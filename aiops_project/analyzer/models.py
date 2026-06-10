from django.db import models

# Create your models here.


class ProjectRepo(models.Model):
    repo_url = models.CharField(max_length=512, unique=True)
    cloud_provider = models.CharField(max_length=32)
    status = models.CharField(max_length=32, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AnalysisResult(models.Model):
    project_repo = models.ForeignKey(ProjectRepo, on_delete=models.CASCADE, related_name='analyses')
    framework = models.CharField(max_length=128)
    dependencies = models.JSONField(null=True, blank=True)
    file_stats = models.JSONField(null=True, blank=True)
    project_size = models.BigIntegerField(null=True, blank=True)
    analysis_timestamp = models.DateTimeField(auto_now_add=True)

class SecurityReport(models.Model):
    analysis_result = models.OneToOneField(AnalysisResult, on_delete=models.CASCADE, related_name='security_report')
    security_score = models.IntegerField(default=0)
    vulnerabilities = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class MLPrediction(models.Model):
    analysis_result = models.OneToOneField(AnalysisResult, on_delete=models.CASCADE, related_name='ml_prediction')
    cpu = models.FloatField()
    ram = models.FloatField()
    storage = models.FloatField()
    model_version = models.CharField(max_length=64, default='v0')
    created_at = models.DateTimeField(auto_now_add=True)

class DeploymentFiles(models.Model):
    analysis_result = models.OneToOneField(AnalysisResult, on_delete=models.CASCADE, related_name='deployment_files')
    dockerfile = models.TextField(null=True, blank=True)
    nginx_conf = models.TextField(null=True, blank=True)
    docker_compose = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
