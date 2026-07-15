from django.urls import path
from .views import (
    analyze_repo,
    deployment_plan,
    login,
    logout,
    me,
    recommend_deployment_ml,
    register,
)

urlpatterns = [
    path("auth/register/", register),
    path("auth/login/", login),
    path("auth/logout/", logout),
    path("auth/me/", me),
    path("analyze/", analyze_repo),
    path("recommend-ml/", recommend_deployment_ml),
    path("deployment-plan/", deployment_plan),
]
