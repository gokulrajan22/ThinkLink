"""Authenticated, versioned Django JSON endpoints for ThinkLink."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import StudentProfile, TeamAnalysis


@require_GET
def api_health(request):
    return JsonResponse({"status": "ok", "service": "thinklink-api", "version": "v1"})


@login_required
@require_GET
def api_students(request):
    students = StudentProfile.objects.filter(is_demo=True) | StudentProfile.objects.filter(owner=request.user)
    return JsonResponse({"results": [
        {"id": s.slug, "name": s.name, "email": s.display_email, "college": s.college, "semester": s.semester, "skills": s.skills,
         "interests": s.interests, "availability": s.availability, "contribution": s.contribution,
         "github_profile_url": f"https://github.com/{s.github_username}" if s.github_username else None,
         "is_demo": s.is_demo}
        for s in students.order_by("name").distinct()
    ]})


@login_required
@require_GET
def api_analyses(request):
    return JsonResponse({"results": [
        {"id": a.id, "title": a.title, "coverage_score": a.coverage_score,
         "analysis_source": a.analysis_source, "created_at": a.created_at.isoformat()}
        for a in TeamAnalysis.objects.filter(owner=request.user)[:50]
    ]})
