"""Privacy notice, account export, and account deletion."""
import json

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from django.db.models import Q

from .models import Message, Notification, ProjectMembership, StudentProfile, TeamAnalysis, TeamInvite


PRIVACY_POLICY_VERSION = "2026-10-26.2"


def privacy_notice(request):
    return render(request, "registration/privacy.html", {"policy_version": PRIVACY_POLICY_VERSION})


@login_required
@require_http_methods(["GET"])
def export_my_data(request):
    profile = StudentProfile.objects.filter(owner=request.user).first()
    analyses = TeamAnalysis.objects.filter(owner=request.user).order_by("-created_at")
    payload = {
        "exported_at": __import__("django.utils.timezone", fromlist=["now"]).now().isoformat(),
        "account": {"username": request.user.username, "email": request.user.email,
                    "full_name": request.user.get_full_name(), "date_joined": request.user.date_joined.isoformat(),
                    "email_verified": request.user.is_active},
        "profile": None if profile is None else {
            "name": profile.name, "college": profile.college, "semester": profile.semester,
            "skills": profile.skills, "interests": profile.interests,
            "availability": profile.availability, "contribution": profile.contribution,
            "github_username": profile.github_username,
            "github_skill_evidence": profile.github_skill_evidence,
            "github_projects": profile.github_projects,
            "share_github_projects": profile.share_github_projects,
            "is_discoverable": profile.is_discoverable,
            "email_notifications": profile.email_notifications,
            "privacy_consent_at": profile.privacy_consent_at.isoformat() if profile.privacy_consent_at else None,
            "privacy_policy_version": profile.privacy_policy_version,
            "created_at": profile.created_at.isoformat(), "updated_at": profile.updated_at.isoformat(),
        },
        "team_analyses": [{
            "title": item.title, "problem_statement": item.problem_statement,
            "selected_students": item.selected_students, "required_skills": item.required_skills,
            "covered_skills": item.covered_skills, "missing_skills": item.missing_skills,
            "coverage_score": item.coverage_score, "analysis_source": item.analysis_source,
            "created_at": item.created_at.isoformat(),
        } for item in analyses],
        "project_memberships": [{
            "project": m.project.title, "role": m.role, "joined_at": m.joined_at.isoformat(),
        } for m in ProjectMembership.objects.filter(user=request.user).select_related("project")],
        "invites": [{
            "project": i.project.title, "kind": i.kind, "status": i.status, "message": i.message,
            "direction": "sent" if i.sender_id == request.user.pk else "received",
            "created_at": i.created_at.isoformat(),
        } for i in TeamInvite.objects.filter(Q(sender=request.user) | Q(recipient=request.user)).select_related("project")],
        "messages_sent": [{
            "conversation_id": m.conversation_id, "body": m.body, "created_at": m.created_at.isoformat(),
        } for m in Message.objects.filter(sender=request.user)],
        "notifications": [{
            "kind": n.kind, "text": n.text, "is_read": n.is_read, "created_at": n.created_at.isoformat(),
        } for n in Notification.objects.filter(user=request.user)],
    }
    response = HttpResponse(json.dumps(payload, ensure_ascii=False, indent=2), content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="thinklink-personal-data.json"'
    response["Cache-Control"] = "no-store"
    return response


@login_required
@require_http_methods(["GET", "POST"])
def delete_my_account(request):
    if request.method == "POST":
        password = request.POST.get("password", "")
        confirmation = request.POST.get("confirm_delete", "")
        if confirmation != "DELETE" or not request.user.check_password(password):
            messages.error(request, "Enter your current password and type DELETE exactly to confirm.")
            return render(request, "registration/delete_account.html", status=400)
        user = request.user
        username = user.username
        # User-owned profile and analyses cascade via on_delete=CASCADE.
        logout(request)
        user.delete()
        messages.success(request, f"Account {username} and its linked profile and saved analyses were deleted.")
        return redirect("login")
    return render(request, "registration/delete_account.html")
