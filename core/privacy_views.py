"""Privacy notice, account export, and account deletion."""
import json

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import StudentProfile, TeamAnalysis


PRIVACY_POLICY_VERSION = "2026-10-26"


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
            "name": profile.name, "college": profile.college, "year": profile.year,
            "skills": profile.skills, "interests": profile.interests,
            "availability": profile.availability, "contribution": profile.contribution,
            "github_username": profile.github_username,
            "github_skill_evidence": profile.github_skill_evidence,
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
