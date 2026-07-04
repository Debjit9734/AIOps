import os
import json
import re

import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

print("=" * 50)
print("Current Directory:", os.getcwd())
print(".env Exists:", os.path.exists(".env"))
print("Gemini Key:", os.getenv("GEMINI_API_KEY"))
print("=" * 50)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")


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
    except:
        return None


def generate_gemini_recommendation(insights, features, cloud):

    framework = insights.get("framework", "Unknown")

    prompt = f"""
You are an experienced DevOps Architect.

Analyze the following repository information.

Framework:
{framework}

Dependencies:
{insights.get("dependencies", [])}

Features:
{json.dumps(features, indent=2)}

Cloud:
{cloud}

Return ONLY valid JSON.

Format:

{{
    "predicted_resources": {{
        "cpu": 2,
        "ram": 4,
        "storage": 30
    }},
    "os_recommendation":"Ubuntu 22.04 LTS",

    "deployment_steps":[
        "...",
        "...",
        "..."
    ],

    "configuration_files_needed":[
        "...",
        "...",
        "..."
    ]
}}

Do not explain anything.
Do not use markdown.
Only output JSON.
"""

    try:

        response = model.generate_content(prompt)

        data = _extract_json(response.text)

        if data is None:
            return _default_recommendation(framework, cloud)

        return data

    except Exception as e:

        print(e)

        return _default_recommendation(framework, cloud)