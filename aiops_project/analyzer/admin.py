from django.contrib import admin
from .models import AuthToken, DailyAnalyzeUsage

# Register your models here.

admin.site.register(AuthToken)
admin.site.register(DailyAnalyzeUsage)
