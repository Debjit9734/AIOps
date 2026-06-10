from django.urls import path
from .views import analyze_repo, recommend_deployment_ml, deployment_plan

urlpatterns = [
    path("analyze/", analyze_repo),
    path("recommend-ml/", recommend_deployment_ml),
    path("deployment-plan/", deployment_plan),
]
