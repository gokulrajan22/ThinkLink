import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.views.decorators.http import require_POST

from . import collaboration as collab
from .ai_service import analyze_problem
from .github_service import analyze_github_user, GitHubServiceError
from .models import StudentProfile, TeamAnalysis
from .views_skill_catalog import SKILL_CATALOG
from .security import rate_limit


def _label(skill):
    return SKILL_CATALOG.get(skill, skill.replace("_", " ").title())


def _visible_students(user):
    """Demo profiles, the user's own profile, and verified students who haven't hidden themselves."""
    discoverable = Q(owner__isnull=False, owner__is_active=True, is_demo=False, is_discoverable=True)
    return StudentProfile.objects.filter(Q(is_demo=True) | Q(owner=user) | discoverable).distinct()


def _safe_projects(repositories):
    """Keep only display fields and GitHub URLs before persisting repository rows."""
    projects = []
    for repo in repositories[:10]:
        url = str(repo.get("url", ""))
        if not url.startswith("https://github.com/"):
            continue
        projects.append({"name": str(repo.get("name", ""))[:100], "description": str(repo.get("description", ""))[:160],
                         "url": url[:300], "language": str(repo.get("language", ""))[:40]})
    return projects


def _community_projects(user):
    """Projects from other students who opted in to sharing their public GitHub repositories."""
    profiles = StudentProfile.objects.filter(share_github_projects=True).exclude(owner=user).exclude(github_username="")
    return [p for p in profiles[:30] if p.github_projects]


def _dashboard_context(request, analysis=None, idea=None, title=None, selected_ids=None, github_result=None, github_error=None, github_username=""):
    students = list(_visible_students(request.user))
    own_profile = StudentProfile.objects.filter(owner=request.user).first()
    if selected_ids is None:
        selected_ids = ["maya", "arjun", "isha"]
    selected_ids = [sid for sid in selected_ids if any(s.slug == sid for s in students)]
    team = [s for s in students if s.slug in selected_ids]
    if idea is None:
        idea = ("Build an AI-powered campus opportunity platform with personalized recommendations, "
                "a searchable web dashboard, and secure student project data.")
    if title is None:
        title = "Campus Opportunity AI"
    return {
        "students": students, "team": team, "selected_ids": selected_ids,
        "my_projects": list(TeamAnalysis.objects.filter(memberships__user=request.user).distinct()
                            .prefetch_related("memberships__user__student_profile")[:8]),
        "open_projects": collab.open_projects_for(request.user),
        "is_dashboard": True,
        "community_projects": _community_projects(request.user),
        "idea": idea, "title": title, "analysis": analysis,
        "ai_configured": bool(os.getenv("GROQ_API_KEY", "").strip()),
        "github_result": github_result, "github_error": github_error,
        "github_username": github_username, "own_profile": own_profile,
    }


@login_required
@rate_limit("team-analysis", 20, 3600)
def dashboard(request):
    analysis = None
    if request.method == "POST" and request.POST.get("action") == "analyze":
        selected_ids = request.POST.getlist("team")
        idea = request.POST.get("idea", "").strip()[:8000]
        title = request.POST.get("title", "").strip()[:200] or "Untitled project"
        if not idea:
            messages.error(request, "Add a problem statement before analyzing your team.")
        elif not selected_ids:
            messages.error(request, "Select at least one student to analyze a hypothetical team.")
        else:
            requirements, ai_notice = analyze_problem(idea)
            students = list(_visible_students(request.user).filter(slug__in=selected_ids))
            if not students:
                messages.error(request, "Select at least one available student profile.")
            else:
                required = requirements["required_skills"]
                covered, gaps, details = [], [], []
                for skill in required:
                    matches = [s for s in students if skill in (s.skills or {}) or skill in (s.github_skill_evidence or {})]
                    if matches:
                        covered.append(skill)
                        details.append({"skill": _label(skill), "status": "covered",
                                        "people": ", ".join(s.name.split()[0] for s in matches)})
                    else:
                        gaps.append(skill)
                        details.append({"skill": _label(skill), "status": "gap", "people": ""})
                score = round(100 * len(covered) / max(len(required), 1))
                recommendations = []
                for student in _visible_students(request.user).exclude(slug__in=selected_ids):
                    overlap = [skill for skill in gaps if skill in (student.skills or {}) or skill in (student.github_skill_evidence or {})]
                    if overlap:
                        recommendations.append({"student": student, "skills": [_label(x) for x in overlap]})
                recommendations.sort(key=lambda x: len(x["skills"]), reverse=True)
                strengths = []
                for student in students:
                    aligned = [_label(skill) for skill in required if skill in (student.skills or {}) or skill in (student.github_skill_evidence or {})]
                    if aligned:
                        note = f"Self-reported skills and/or public GitHub evidence align with {', '.join(aligned[:4])}."
                    else:
                        note = "No direct self-reported skill match detected; this is not evidence that the student lacks the ability."
                    strengths.append({"student": student, "aligned": aligned, "note": note})
                analysis = {
                    "score": score, "required": [_label(s) for s in required],
                    "covered": [_label(s) for s in covered], "gaps": [_label(s) for s in gaps],
                    "details": details, "recommendations": recommendations[:3],
                    "strengths": strengths, "team_size": len(students),
                    "roles": requirements.get("roles", []),
                    "problem_summary": requirements.get("problem_summary", ""),
                    "reasoning": requirements.get("reasoning", ""),
                    "source": requirements.get("analysis_source", "rules"),
                    "ai_notice": ai_notice,
                }
                project = TeamAnalysis.objects.create(
                    owner=request.user, title=title, problem_statement=idea,
                    selected_students=[s.slug for s in students],
                    required_skills=analysis["required"], covered_skills=analysis["covered"],
                    missing_skills=analysis["gaps"], coverage_score=score,
                    analysis_source=analysis["source"],
                )
                collab.ensure_owner_membership(project)
                analysis["project_id"] = project.pk
    elif request.method == "POST":
        selected_ids = request.POST.getlist("team") or ["maya", "arjun", "isha"]
        idea = request.POST.get("idea", "").strip()[:8000] or None
        title = request.POST.get("title", "").strip()[:200] or None
    else:
        selected_ids = ["maya", "arjun", "isha"]
        idea = None
        title = None
    context = _dashboard_context(request, analysis, idea, title, selected_ids)
    return render(request, "core/dashboard.html", context)


@login_required
@require_POST
@rate_limit("github-analysis", 10, 3600)
def github_analyze(request):
    username = request.POST.get("github_username", "").strip()
    if request.POST.get("github_consent") != "yes":
        return render(request, "core/dashboard.html", _dashboard_context(
            request, github_error="Please confirm that you consent to inspection of public GitHub repository metadata and a bounded source-file sample.",
            github_username=username))
    try:
        result = analyze_github_user(username)
        # Never let a user attach GitHub evidence to another person's profile.
        selected_slug = request.POST.get("student_slug", "").strip()
        profile = StudentProfile.objects.filter(owner=request.user).first() if selected_slug else None
        if profile and selected_slug == profile.slug:
            profile.github_username = result["username"]
            profile.github_skill_evidence = {item["skill_id"]: item["evidence"] for item in result["inferred_skills"]}
            profile.github_projects = _safe_projects(result.get("repositories", []))
            profile.share_github_projects = request.POST.get("share_github_projects") == "yes"
            profile.save(update_fields=["github_username", "github_skill_evidence", "github_projects",
                                        "share_github_projects", "updated_at"])
        elif selected_slug:
            messages.error(request, "You can associate GitHub evidence only with your own profile.")
        context = _dashboard_context(request, github_result=result, github_username=username)
    except GitHubServiceError as exc:
        context = _dashboard_context(request, github_error=str(exc), github_username=username)
    return render(request, "core/dashboard.html", context)
