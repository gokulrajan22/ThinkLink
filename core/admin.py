from django.contrib import admin
from .models import StudentProfile, TeamAnalysis


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "college", "year", "contribution", "github_username", "is_demo", "updated_at")
    list_filter = ("college", "is_demo")
    search_fields = ("name", "college", "github_username", "contribution")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TeamAnalysis)
class TeamAnalysisAdmin(admin.ModelAdmin):
    list_display = ("title", "coverage_score", "analysis_source", "created_at")
    list_filter = ("analysis_source", "created_at")
    search_fields = ("title", "problem_statement")
    readonly_fields = ("created_at",)
