"""Authenticated self-service profile editing for ThinkLink."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import StudentProfile
from .views_skill_catalog import SKILL_CATALOG


class ProfileForm(forms.Form):
    name = forms.CharField(max_length=120)
    college = forms.CharField(max_length=160)
    year = forms.CharField(max_length=80, required=False)
    contribution = forms.CharField(max_length=120, required=False)
    availability = forms.CharField(max_length=160, required=False)
    interests = forms.CharField(max_length=500, required=False, help_text="Separate interests with commas.")
    skills_text = forms.CharField(
        max_length=1200, required=False,
        help_text="One skill per line as skill-id=level (1–5), e.g. python=3 or machine learning=4.",
        widget=forms.Textarea(attrs={"rows": 7}),
    )
    clear_github_evidence = forms.BooleanField(required=False, label="Remove my saved GitHub username and derived evidence.")

    def clean_skills_text(self):
        raw = self.cleaned_data.get("skills_text", "")
        skills = {}
        for line_number, line in enumerate(raw.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            if "=" not in line:
                raise forms.ValidationError(f"Line {line_number}: use skill-id=level, such as python=3.")
            key, value = (part.strip().lower() for part in line.rsplit("=", 1))
            if key not in SKILL_CATALOG:
                raise forms.ValidationError(f"Line {line_number}: '{key}' is not in the supported skill catalog.")
            try:
                level = int(value)
            except ValueError:
                raise forms.ValidationError(f"Line {line_number}: skill level must be a number from 1 to 5.")
            if not 1 <= level <= 5:
                raise forms.ValidationError(f"Line {line_number}: skill level must be between 1 and 5.")
            skills[key] = level
        if len(skills) > 20:
            raise forms.ValidationError("Add no more than 20 skills.")
        self.cleaned_skills = skills
        return raw

    def clean_interests(self):
        items = [item.strip()[:60] for item in self.cleaned_data.get("interests", "").split(",") if item.strip()]
        if len(items) > 20:
            raise forms.ValidationError("Add no more than 20 interests.")
        return ", ".join(items)


@login_required
@require_http_methods(["GET", "POST"])
def edit_profile(request):
    profile = StudentProfile.objects.filter(owner=request.user).first()
    if profile is None:
        messages.error(request, "Your student profile could not be found. Please contact support.")
        return redirect("dashboard")
    initial = {
        "name": profile.name, "college": profile.college, "year": profile.year,
        "contribution": profile.contribution, "availability": profile.availability,
        "interests": ", ".join(profile.interests or []),
        "skills_text": "\n".join(f"{key}={level}" for key, level in (profile.skills or {}).items()),
        "clear_github_evidence": False,
    }
    form = ProfileForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        profile.name = data["name"].strip()
        profile.initials = "".join(part[0] for part in profile.name.split()[:2]).upper()[:8] or "TL"
        profile.college = data["college"].strip()
        profile.year = data["year"].strip()
        profile.contribution = data["contribution"].strip()
        profile.availability = data["availability"].strip()
        profile.interests = [item.strip() for item in data["interests"].split(",") if item.strip()]
        profile.skills = form.cleaned_skills
        if data["clear_github_evidence"]:
            profile.github_username = ""
            profile.github_skill_evidence = {}
        profile.save(update_fields=[
            "name", "initials", "college", "year", "contribution", "availability",
            "interests", "skills", "github_username", "github_skill_evidence", "updated_at",
        ])
        messages.success(request, "Your ThinkLink profile was updated.")
        return redirect("dashboard")
    return render(request, "registration/profile.html", {"form": form, "profile": profile})
