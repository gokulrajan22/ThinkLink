from django.conf import settings
from django.db import models


class StudentProfile(models.Model):
    """Student profile. Skill levels are self-reported, not verified."""
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="student_profile", null=True, blank=True,
    )
    slug = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    initials = models.CharField(max_length=8)
    college = models.CharField(max_length=160, default="ThinkLink Campus")
    year = models.CharField(max_length=80, blank=True)
    skills = models.JSONField(default=dict, blank=True)
    interests = models.JSONField(default=list, blank=True)
    availability = models.CharField(max_length=160, blank=True)
    contribution = models.CharField(max_length=120, blank=True)
    github_username = models.CharField(max_length=39, blank=True)
    github_skill_evidence = models.JSONField(default=dict, blank=True)
    privacy_consent_at = models.DateTimeField(null=True, blank=True)
    privacy_policy_version = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=20, default="violet")
    is_demo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TeamAnalysis(models.Model):
    """A private team-analysis snapshot owned by the user who created it."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="team_analyses", null=True, blank=True,
    )
    title = models.CharField(max_length=200)
    problem_statement = models.TextField()
    selected_students = models.JSONField(default=list, blank=True)
    required_skills = models.JSONField(default=list, blank=True)
    covered_skills = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    coverage_score = models.PositiveSmallIntegerField(default=0)
    analysis_source = models.CharField(max_length=40, default="rules")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.created_at:%Y-%m-%d %H:%M}"


class RateLimitBucket(models.Model):
    """Shared request counters; database-backed for multi-instance deployments."""
    key = models.CharField(max_length=64, unique=True)
    scope = models.CharField(max_length=40, db_index=True)
    window_start = models.BigIntegerField(db_index=True)
    count = models.PositiveIntegerField(default=0)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["scope", "window_start"])]
