import os
import json
import re

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")


def _rule_based_resource_estimate(features):
    """
    Deterministic sizing baseline, independent of the LLM. Mirrors the
    labeling logic used for training data generation (see
    data_generator.generate_labels), so LLM output can be sanity-checked
    against a known-reasonable estimate instead of trusted blindly.
    """
    total_lines = features.get("total_lines") or 0
    dependency_count = features.get("dependency_count") or 0
    security_score = features.get("security_score") or 0

    if total_lines < 3000 and dependency_count < 15:
        cpu, ram, storage = 1, 1, 10
    elif total_lines < 20000:
        cpu, ram, storage = 2, 4, 20
    else:
        cpu, ram, storage = 4, 8, 50

    if security_score and security_score > 6:
        cpu += 0.5
        ram += 1

    return {"cpu": cpu, "ram": ram, "storage": storage}


def _sanity_check_resources(predicted, features, max_multiplier=3):
    """
    Clamp LLM-predicted resources against the rule-based baseline so a
    hallucinated or copy-pasted-example value can't slip through
    unquestioned. Values are allowed to differ from the baseline by up to
    `max_multiplier`x in either direction, which still gives the LLM room
    to account for things the rule-based estimate can't see (e.g. it read
    the code and noticed heavy background jobs) without letting it return
    wildly disproportionate numbers for a small project.
    """
    if not isinstance(predicted, dict):
        return None

    baseline = _rule_based_resource_estimate(features)
    clamped = {}

    for key in ("cpu", "ram", "storage"):
        predicted_value = predicted.get(key)
        baseline_value = baseline[key]

        if not isinstance(predicted_value, (int, float)):
            clamped[key] = baseline_value
            continue

        upper_bound = baseline_value * max_multiplier
        lower_bound = baseline_value / max_multiplier
        clamped[key] = round(min(max(predicted_value, lower_bound), upper_bound), 2)

    return clamped


def _default_recommendation(framework, cloud):
    framework_name = (framework or "unknown").lower()

    steps = [
        "Clone repository.",
        "Install dependencies.",
        "Build Docker image.",
        f"Deploy on {cloud.upper()}.",
    ]

    files = [
        "Dockerfile",
        "docker-compose.yml",
        ".env",
    ]

    if framework_name == "django":
        steps.insert(2, "Run migrations and collectstatic.")
        files.append("nginx.conf")

    return {
        "predicted_resources": None,
        "os_recommendation": "Ubuntu 22.04 LTS",
        "deployment_steps": steps,
        "configuration_files_needed": files,
    }


def _extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except Exception:
        return None


def generate_gemini_recommendation(insights, features, cloud):
    framework = insights.get("framework", "Unknown")

    # NOTE: the previous prompt put literal example numbers (cpu: 2, ram: 4,
    # storage: 30) directly in the expected-output schema. LLMs frequently
    # echo concrete example values back verbatim instead of reasoning about
    # the actual input, especially when the example "looks like a real
    # answer" rather than an obvious placeholder. The schema below uses
    # clearly-marked placeholder text instead, and explicitly restates the
    # real project metrics right above it so there's no ambiguity about
    # what to size for.
    prompt = f"""
You are an experienced DevOps Architect.

Analyze the following repository information and size infrastructure
resources specifically for THIS project. Do not use generic or example
values -- base cpu/ram/storage on the actual metrics given below.

Framework:
{framework}

Dependencies:
{insights.get("dependencies", [])}

Project metrics (use these to size resources):
{json.dumps(features, indent=2)}

Target cloud:
{cloud}

Return ONLY valid JSON, matching this exact shape. The bracketed text is
a description of what to put there, NOT a value to copy -- replace each
one with a real number you calculated from the project metrics above.

{{
    "predicted_resources": {{
        "cpu": "[number of vCPUs appropriate for total_lines={features.get('total_lines')} and dependency_count={features.get('dependency_count')}, e.g. 0.5 to 8]",
        "ram": "[RAM in GB appropriate for this project's size, e.g. 0.5 to 16]",
        "storage": "[storage in GB appropriate for this project's size, e.g. 5 to 100]"
    }},
    "os_recommendation": "Ubuntu 22.04 LTS",
    "deployment_steps": [
        "...",
        "...",
        "..."
    ],
    "configuration_files_needed": [
        "...",
        "...",
        "..."
    ]
}}

Do not explain anything.
Do not use markdown.
Only output JSON. All numeric fields must be actual numbers, not strings
or bracketed placeholders.
"""

    try:
        response = model.generate_content(prompt)
        data = _extract_json(response.text)

        if data is None:
            return _default_recommendation(framework, cloud)

        # Sanity-check whatever the LLM returned against a deterministic
        # baseline before trusting it, regardless of whether it looks
        # plausible on its face.
        predicted = data.get("predicted_resources")
        data["predicted_resources"] = _sanity_check_resources(predicted, features)

        return data

    except Exception as e:
        print(e)
        return _default_recommendation(framework, cloud)