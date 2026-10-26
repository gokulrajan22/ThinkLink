from django.contrib import admin
from .models import Message, Notification, ProjectMembership, StudentProfile, TeamAnalysis, TeamInvite


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "college", "semester", "contribution", "github_username", "is_demo", "updated_at")
    list_filter = ("college", "is_demo")
    search_fields = ("name", "college", "github_username", "contribution")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TeamAnalysis)
class TeamAnalysisAdmin(admin.ModelAdmin):
    list_display = ("title", "coverage_score", "analysis_source", "created_at")
    list_filter = ("analysis_source", "created_at")
    search_fields = ("title", "problem_statement")
    readonly_fields = ("created_at",)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Visible for moderation; changes happen only through the app's authorization rules."""
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(ReadOnlyAdmin):
    list_display = ("project", "user", "role", "joined_at")


@admin.register(TeamInvite)
class TeamInviteAdmin(ReadOnlyAdmin):
    list_display = ("project", "kind", "sender", "recipient", "status", "created_at")
    list_filter = ("kind", "status")


@admin.register(Message)
class MessageAdmin(ReadOnlyAdmin):
    list_display = ("conversation", "sender", "created_at")


@admin.register(Notification)
class NotificationAdmin(ReadOnlyAdmin):
    list_display = ("user", "kind", "is_read", "created_at")
