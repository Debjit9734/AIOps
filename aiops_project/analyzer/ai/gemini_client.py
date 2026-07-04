import google.generativeai as genai
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


def get_ai_recommendation(project):

    prompt = f"""
You are a senior DevOps Engineer.

Analyze this project.

Framework:
{project['framework']}

Dependencies:
{project['dependencies']}

Security Score:
{project['security_score']}

Project Size:
{project['project_size']}

Predicted Resources:
CPU: {project['cpu']}
RAM: {project['ram']}
Storage: {project['storage']}

Cloud:
{project['cloud']}

Generate:

1. Deployment recommendation

2. Security improvements

3. Performance optimization

4. Cost optimization

5. Scaling strategy

Return in proper markdown.
"""

    response = model.generate_content(prompt)

    return response.text