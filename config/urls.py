from django.contrib import admin
from django.contrib.auth import views as django_auth_views
from django.urls import path, reverse_lazy

from core import collab_views
from core.auth_views import sign_in, sign_up, verify_email, resend_verification
from core.privacy_views import privacy_notice, export_my_data, delete_my_account
from core.security import rate_limit
from core.profile_views import edit_profile
from core.views import dashboard, github_analyze
from core.api import api_health, api_students, api_analyses

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/signup/", sign_up, name="signup"),
    path("accounts/login/", sign_in, name="login"),
    path("accounts/verify/resend/", resend_verification, name="resend-verification"),
    path("accounts/verify/<str:token>/", verify_email, name="verify-email"),
    path("accounts/password-reset/", rate_limit("password-reset", 5, 3600)(django_auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html",
        email_template_name="registration/password_reset_email.html",
        subject_template_name="registration/password_reset_subject.txt",
        success_url=reverse_lazy("password_reset_done"),
    )), name="password_reset"),
    path("accounts/password-reset/done/", django_auth_views.PasswordResetDoneView.as_view(
        template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("accounts/reset/<uidb64>/<token>/", django_auth_views.PasswordResetConfirmView.as_view(
        template_name="registration/password_reset_confirm.html",
        success_url=reverse_lazy("password_reset_complete")), name="password_reset_confirm"),
    path("accounts/reset/complete/", django_auth_views.PasswordResetCompleteView.as_view(
        template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
    path("privacy/", privacy_notice, name="privacy"),
    path("account/export/", export_my_data, name="data-export"),
    path("account/delete/", delete_my_account, name="account-delete"),
    path("accounts/logout/", django_auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", edit_profile, name="profile"),
    path("api/v1/health/", api_health, name="api-health"),
    path("api/v1/students/", api_students, name="api-students"),
    path("api/v1/analyses/", api_analyses, name="api-analyses"),
    path("github/analyze/", github_analyze, name="github-analyze"),
    path("invites/", collab_views.invites, name="invites"),
    path("invites/send/", collab_views.invite_send, name="invite-send"),
    path("invites/<int:pk>/<str:action>/", collab_views.invite_respond, name="invite-respond"),
    path("projects/<int:pk>/", collab_views.project_detail, name="project-detail"),
    path("projects/<int:pk>/open/", collab_views.project_toggle_open, name="project-toggle-open"),
    path("projects/<int:pk>/request/", collab_views.project_request, name="project-request"),
    path("projects/<int:pk>/chat/", collab_views.project_chat, name="project-chat"),
    path("messages/", collab_views.messages_inbox, name="messages-inbox"),
    path("messages/new/<slug:slug>/", collab_views.message_new, name="message-new"),
    path("messages/<int:pk>/", collab_views.message_thread, name="message-thread"),
    path("messages/<int:pk>/send/", collab_views.message_send, name="message-send"),
    path("messages/<int:pk>/poll/", collab_views.message_poll, name="message-poll"),
    path("notifications/", collab_views.notifications, name="notifications"),
    path("notifications/read-all/", collab_views.notifications_read_all, name="notifications-read-all"),
    path("notifications/<int:pk>/open/", collab_views.notification_open, name="notification-open"),
    path("api/v1/notifications/summary/", collab_views.api_notifications_summary, name="api-notifications-summary"),
    path("", dashboard, name="dashboard"),
]
