from django.contrib import admin
from django.contrib.auth import views as django_auth_views
from django.urls import path

from core.auth_views import sign_in, sign_up
from core.profile_views import edit_profile
from core.views import dashboard, github_analyze
from core.api import api_health, api_students, api_analyses

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/signup/", sign_up, name="signup"),
    path("accounts/login/", sign_in, name="login"),
    path("accounts/logout/", django_auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", edit_profile, name="profile"),
    path("api/v1/health/", api_health, name="api-health"),
    path("api/v1/students/", api_students, name="api-students"),
    path("api/v1/analyses/", api_analyses, name="api-analyses"),
    path("github/analyze/", github_analyze, name="github-analyze"),
    path("", dashboard, name="dashboard"),
]
