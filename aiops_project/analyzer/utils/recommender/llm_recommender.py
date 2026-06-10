import json
import os
import re
from urllib import error, request


HF_API_URL = "https://api-inference.huggingface.co/models"
HF_MODEL = os.environ.get("HF_MODEL", "HuggingFaceH4/zephyr-7b-beta")


def _default_recommendation(framework, cloud):
    framework_name = (framework or "unknown").lower()
    os_name = "ubuntu:22.04"

    steps = [
        "Clone repository and set required environment variables.",
        "Install runtime dependencies.",
        "Build application image and run container health checks.",
        f"Deploy to {cloud.upper()} with autoscaling and monitoring enabled.",
    ]

    config_files = [
        "Dockerfile",
        "docker-compose.yml",
        ".env.example",
        "README-deploy.md",
    ]

    if "django" in framework_name:
        steps.insert(2, "Run migrations and collect static files.")
        config_files.append("nginx.conf")

    return {
        "predicted_resources": None,
        "os_recommendation": os_name,
        "deployment_steps": steps,
        "configuration_files_needed": config_files,
    }


def _extract_json_object(text):
    if not text:
        return None

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _coerce_resources(resources):
    if not isinstance(resources, dict):
        return None

    try:
        return {
            "cpu": round(float(resources["cpu"]), 2),
            "ram": round(float(resources["ram"]), 2),
            "storage": round(float(resources["storage"]), 2),
        }
    except (KeyError, TypeError, ValueError):
        return None


def generate_hf_recommendation(insights, features, cloud):
    token = os.environ.get("HF_API_TOKEN")
    framework = insights.get("framework", "unknown")

    if not token:
        return _default_recommendation(framework, cloud)

    prompt = f"""
You are an SRE and cloud architect.
Return ONLY valid JSON with keys:
- predicted_resources: object with numeric cpu, ram, storage
- os_recommendation: string
- deployment_steps: array of short strings
- configuration_files_needed: array of strings

Inputs:
cloud={cloud}
framework={framework}
dependencies={insights.get("dependencies", [])}
features={features}
"""

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 280,
            "temperature": 0.2,
            "return_full_text": False,
        },
    }

    req = request.Request(
        f"{HF_API_URL}/{HF_MODEL}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=25) as resp:
            response_body = json.loads(resp.read().decode("utf-8"))
    except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
        return _default_recommendation(framework, cloud)

    generated_text = ""
    if isinstance(response_body, list) and response_body:
        generated_text = response_body[0].get("generated_text", "")
    elif isinstance(response_body, dict):
        generated_text = response_body.get("generated_text", "")

    parsed = _extract_json_object(generated_text)
    if not isinstance(parsed, dict):
        return _default_recommendation(framework, cloud)

    recommendation = _default_recommendation(framework, cloud)
    recommendation.update(
        {
            "predicted_resources": _coerce_resources(parsed.get("predicted_resources")),
            "os_recommendation": parsed.get("os_recommendation")
            or recommendation["os_recommendation"],
            "deployment_steps": parsed.get("deployment_steps")
            or recommendation["deployment_steps"],
            "configuration_files_needed": parsed.get("configuration_files_needed")
            or recommendation["configuration_files_needed"],
        }
    )
    return recommendation
