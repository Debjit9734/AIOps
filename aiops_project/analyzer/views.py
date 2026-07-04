from uuid import uuid4

from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response

from analyzer.utils.analyzer_utils import download_repo_as_zip, analyze_files

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

    repo_url = request.data.get("repo_url")

    if not repo_url:
        return Response(
            {"error": "repo_url is required"},
            status=400,
        )

    repo_path, error = download_repo_as_zip(repo_url)

    if error:
        return Response(
            {"error": error},
            status=400,
        )

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
        },
        ANALYSIS_CACHE_TTL,
    )

    return Response(
        {
            "analysis_id": analysis_id,
            "repo_url": repo_url,
            "insights": insights,
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

    repo_url = analysis_data["repo_url"]
    repo_path = analysis_data["repo_path"]
    insights = analysis_data["insights"]
    features = analysis_data["features"]

    # Gemini Recommendation
    llm_recommendation = generate_gemini_recommendation(
        insights,
        features,
        cloud
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