from uuid import uuid4
import secrets

from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from analyzer.utils.analyzer_utils import download_repo_as_zip, analyze_files
from analyzer.models import AuthToken, DailyAnalyzeUsage

from .utils.recommender.feature_extractor import extract_features
from .utils.recommender.security_analyzer import analyze_security
from .utils.recommender.model import predict_resources
from .utils.recommender.data_generator import save_training_row
from .utils.recommender.llm_recommender import generate_gemini_recommendation
from .utils.deployment_plans import (
    generate_deployment_plan_payload,
    validate_target,
)
from .utils.deployment_generator import (
    generate_django_dockerfile,
    generate_nginx_conf,
    generate_django_compose,
)

ANALYSIS_CACHE_PREFIX = "analysis:"
ANALYSIS_CACHE_TTL = 1800
DAILY_ANALYZE_LIMIT = 3


def _serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_staff or user.is_superuser,
    }


def _get_bearer_token(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    prefix = "Bearer "
    if not auth_header.startswith(prefix):
        return ""
    return auth_header[len(prefix):].strip()


def _authenticate_request(request):
    token_key = _get_bearer_token(request)
    if not token_key:
        return None

    token = (
        AuthToken.objects.select_related("user")
        .filter(key=token_key)
        .first()
    )
    if not token:
        return None
    return token.user


def _require_user(request):
    user = _authenticate_request(request)
    if not user:
        return None, Response(
            {"error": "Please login before using this feature."},
            status=401,
        )
    return user, None


def _get_or_create_token(user):
    AuthToken.objects.filter(user=user).delete()
    return AuthToken.objects.create(user=user, key=secrets.token_hex(32))


def _usage_payload(user):
    if user.is_staff or user.is_superuser:
        return {
            "limit": None,
            "used": 0,
            "remaining": None,
            "is_admin": True,
        }

    today = timezone.localdate()
    usage = DailyAnalyzeUsage.objects.filter(user=user, date=today).first()
    used = usage.count if usage else 0
    return {
        "limit": DAILY_ANALYZE_LIMIT,
        "used": used,
        "remaining": max(DAILY_ANALYZE_LIMIT - used, 0),
        "is_admin": False,
    }


def _consume_analyze_quota(user):
    if user.is_staff or user.is_superuser:
        return _usage_payload(user), None

    today = timezone.localdate()

    with transaction.atomic():
        usage, _ = (
            DailyAnalyzeUsage.objects.select_for_update()
            .get_or_create(user=user, date=today, defaults={"count": 0})
        )

        if usage.count >= DAILY_ANALYZE_LIMIT:
            return _usage_payload(user), Response(
                {
                    "error": "Daily analyze limit reached. You can run up to 3 analyses per day.",
                    "rate_limit": _usage_payload(user),
                },
                status=429,
            )

        usage.count += 1
        usage.save(update_fields=["count", "updated_at"])

    return _usage_payload(user), None


def _reject_if_quota_exhausted(user):
    rate_limit = _usage_payload(user)
    if rate_limit["is_admin"] or rate_limit["remaining"] > 0:
        return None

    return Response(
        {
            "error": "Daily analyze limit reached. You can run up to 3 analyses per day.",
            "rate_limit": rate_limit,
        },
        status=429,
    )


@api_view(["POST"])
def register(request):
    username = (request.data.get("username") or "").strip()
    email = (request.data.get("email") or "").strip()
    password = request.data.get("password") or ""

    if not username or not password:
        return Response(
            {"error": "username and password are required"},
            status=400,
        )

    if len(password) < 8:
        return Response(
            {"error": "Password must be at least 8 characters long."},
            status=400,
        )

    User = get_user_model()
    if User.objects.filter(username__iexact=username).exists():
        return Response(
            {"error": "This username is already registered."},
            status=400,
        )

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )
    token = _get_or_create_token(user)

    return Response(
        {
            "token": token.key,
            "user": _serialize_user(user),
            "rate_limit": _usage_payload(user),
        },
        status=201,
    )


@api_view(["POST"])
def login(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""

    if not username or not password:
        return Response(
            {"error": "username and password are required"},
            status=400,
        )

    user = authenticate(username=username, password=password)
    if not user:
        return Response(
            {"error": "Invalid username or password."},
            status=400,
        )

    token = _get_or_create_token(user)

    return Response(
        {
            "token": token.key,
            "user": _serialize_user(user),
            "rate_limit": _usage_payload(user),
        }
    )


@api_view(["POST"])
def logout(request):
    token_key = _get_bearer_token(request)
    if token_key:
        AuthToken.objects.filter(key=token_key).delete()
    return Response({"ok": True})


@api_view(["GET"])
def me(request):
    user, error_response = _require_user(request)
    if error_response:
        return error_response

    return Response(
        {
            "user": _serialize_user(user),
            "rate_limit": _usage_payload(user),
        }
    )


def _get_analysis(analysis_id):
    if not analysis_id:
        return None, Response(
            {"error": "analysis_id is required"},
            status=400,
        )

    cache_key = f"{ANALYSIS_CACHE_PREFIX}{analysis_id}"
    analysis_data = cache.get(cache_key)

    if analysis_data is None:
        return (
            None,
            Response(
                {
                    "error": "Analysis not found or expired for the provided analysis_id"
                },
                status=404,
            ),
        )

    analysis_data = {**analysis_data, "analysis_id": analysis_id}
    return analysis_data, None


@api_view(["POST"])
def analyze_repo(request):
    """
    Request:
    {
        "repo_url": "https://github.com/user/repo"
    }
    """

    user, error_response = _require_user(request)

    if error_response:
        return error_response

    repo_url = request.data.get("repo_url")

    if not repo_url:
        return Response(
            {"error": "repo_url is required"},
            status=400,
        )

    quota_response = _reject_if_quota_exhausted(user)

    if quota_response:
        return quota_response

    repo_path, error = download_repo_as_zip(repo_url)

    if error:
        return Response(
            {"error": error},
            status=400,
        )

    rate_limit, quota_response = _consume_analyze_quota(user)

    if quota_response:
        return quota_response

    insights = analyze_files(repo_path)

    features = extract_features(repo_path, insights)
    features["security_score"] = analyze_security(
        insights.get("dependencies", [])
    )

    save_training_row(features)

    analysis_id = str(uuid4())

    cache.set(
        f"{ANALYSIS_CACHE_PREFIX}{analysis_id}",
        {
            "repo_url": repo_url,
            "repo_path": repo_path,
            "insights": insights,
            "features": features,
            "user_id": user.id,
        },
        ANALYSIS_CACHE_TTL,
    )

    return Response(
        {
            "analysis_id": analysis_id,
            "repo_url": repo_url,
            "insights": insights,
            "rate_limit": rate_limit,
        }
    )


@api_view(["POST"])
def recommend_deployment_ml(request):
    """
    Request:
    {
        "analysis_id": "...",
        "cloud": "aws"
    }
    """

    user, error_response = _require_user(request)

    if error_response:
        return error_response

    analysis_id = request.data.get("analysis_id")
    cloud = request.data.get("cloud")

    if not analysis_id or not cloud:
        return Response(
            {"error": "analysis_id and cloud are required"},
            status=400,
        )

    analysis_data, error_response = _get_analysis(analysis_id)

    if error_response:
        return error_response

    if analysis_data.get("user_id") != user.id and not (user.is_staff or user.is_superuser):
        return Response(
            {"error": "You do not have access to this analysis."},
            status=403,
        )

    repo_url = analysis_data["repo_url"]
    repo_path = analysis_data["repo_path"]
    insights = analysis_data["insights"]
    features = analysis_data["features"]

    # Gemini Recommendation
    llm_recommendation = generate_gemini_recommendation(
        insights,
        features,
        cloud,
        repo_url=repo_url,
    )

    resources = (
        llm_recommendation.get("predicted_resources")
        or predict_resources(features)
    )

    deployment_files = {}

    framework = insights.get("framework", "").lower()

    if "django" in framework:
        deployment_files = {
            "Dockerfile": generate_django_dockerfile(),
            "nginx.conf": generate_nginx_conf(),
            "docker-compose.yml": generate_django_compose(),
        }

    return Response(
        {
            "analysis_id": analysis_id,
            "repo_url": repo_url,
            "cloud": cloud,
            "framework": framework,
            "features": features,
            "predicted_resources": resources,
            "deployment_files": deployment_files,
            "os_recommendation": llm_recommendation.get(
                "os_recommendation"
            ),
            "deployment_steps": llm_recommendation.get(
                "deployment_steps"
            ),
            "deployment_runbook": llm_recommendation.get(
                "deployment_runbook"
            ),
            "configuration_files_needed": llm_recommendation.get(
                "configuration_files_needed"
            ),
            "summary": llm_recommendation.get("summary"),
            "architecture": llm_recommendation.get("architecture"),
            "security_risks": llm_recommendation.get(
                "security_risks"
            ),
            "confidence": llm_recommendation.get("confidence"),
        }
    )


@api_view(["POST"])
def deployment_plan(request):
    """
    Request:
    {
        "analysis_id": "...",
        "cloud": "aws",
        "target": {...}
    }
    """

    user, error_response = _require_user(request)

    if error_response:
        return error_response

    analysis_id = request.data.get("analysis_id")
    cloud = request.data.get("cloud")
    target = request.data.get("target")

    if not analysis_id or not cloud or not target:
        return Response(
            {
                "error": "analysis_id, cloud and target are required"
            },
            status=400,
        )

    analysis_data, error_response = _get_analysis(analysis_id)

    if error_response:
        return error_response

    if analysis_data.get("user_id") != user.id and not (user.is_staff or user.is_superuser):
        return Response(
            {"error": "You do not have access to this analysis."},
            status=403,
        )

    _, validation_error = validate_target(cloud, target)

    if validation_error:
        return Response(
            {"error": validation_error},
            status=400,
        )

    repo_url = analysis_data["repo_url"]
    insights = analysis_data["insights"]
    features = analysis_data["features"]

    ml_resources = predict_resources(features)

    llm_recommendation = generate_gemini_recommendation(
        insights=insights,
        features=features,
        cloud=cloud,
        repo_url=repo_url,
    )

    plan_payload, plan_error = generate_deployment_plan_payload(
        cloud=cloud,
        target=target,
        insights=insights,
        features=features,
        ml_resources=ml_resources,
        llm_recommendation=llm_recommendation,
    )

    if plan_error:
        return Response(
            {"error": plan_error},
            status=400,
        )

    return Response(
        {
            "analysis_id": analysis_id,
            "repo_url": repo_url,
            "cloud": cloud,
            **plan_payload,
        }
    )
