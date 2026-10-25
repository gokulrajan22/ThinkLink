"""Private FastAPI service for ThinkLink; protect it with INTERNAL_API_TOKEN."""
import hmac
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from core.ai_service import analyze_problem
from core.models import StudentProfile, TeamAnalysis
from core.views_skill_catalog import SKILL_CATALOG

app = FastAPI(title="ThinkLink API", version="1.0.0", description="Private problem-aware student team composition API.")
bearer_scheme = HTTPBearer(auto_error=False)


def require_internal_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    expected = os.getenv("INTERNAL_API_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Private API token is not configured.")
    supplied = credentials.credentials if credentials else ""
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Authentication required.")
    return True


class AnalyzeRequest(BaseModel):
    title: str = Field(default="Untitled project", max_length=200)
    problem_statement: str = Field(min_length=12, max_length=8000)
    student_slugs: list[str] = Field(min_length=1, max_length=20)


@app.get("/")
def root():
    return {"status": "ok", "service": "think-link", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "thinklink-api", "version": "v1"}


@app.get("/v1/students", dependencies=[Depends(require_internal_token)])
def list_students():
    return {"results": [
        {"id": s.slug, "name": s.name, "college": s.college, "year": s.year,
         "skills": s.skills, "interests": s.interests, "availability": s.availability,
         "contribution": s.contribution,
         "github_profile_url": f"https://github.com/{s.github_username}" if s.github_username else None,
         "is_demo": s.is_demo}
        for s in StudentProfile.objects.filter(is_demo=True)
    ]}


@app.post("/v1/team-analysis", dependencies=[Depends(require_internal_token)])
def team_analysis(payload: AnalyzeRequest):
    students = list(StudentProfile.objects.filter(is_demo=True, slug__in=payload.student_slugs))
    if not students:
        raise HTTPException(status_code=404, detail="No matching demo profiles were found.")
    requirements, notice = analyze_problem(payload.problem_statement)
    skills = requirements["required_skills"]
    covered, gaps, details = [], [], []
    for skill in skills:
        matched = [s.name for s in students if skill in (s.skills or {})]
        row = {"skill": SKILL_CATALOG.get(skill, skill.title()), "status": "covered" if matched else "gap", "people": matched}
        details.append(row)
        (covered if matched else gaps).append(row["skill"])
    score = round(100 * len(covered) / max(len(skills), 1))
    return {
        "title": payload.title, "analysis_source": requirements.get("analysis_source", "rules"),
        "problem_summary": requirements.get("problem_summary", ""), "reasoning": requirements.get("reasoning", ""),
        "notice": notice, "roles": requirements.get("roles", []), "team_size": len(students),
        "coverage_score": score, "required_skills": [SKILL_CATALOG.get(s, s.title()) for s in skills],
        "covered_skills": covered, "missing_skills": gaps, "details": details,
        "limitations": "Coverage is not a prediction of project success. Demo profile skills are illustrative and unverified.",
    }


@app.get("/v1/analyses", dependencies=[Depends(require_internal_token)])
def list_analyses():
    # The internal service has no user identity; don't expose private user analyses.
    return {"results": []}
