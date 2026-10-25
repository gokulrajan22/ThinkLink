"""Account creation and sign-in views for ThinkLink."""
import re

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from .models import StudentProfile


class SignUpForm(forms.Form):
    username = forms.CharField(max_length=150)
    full_name = forms.CharField(max_length=120)
    email = forms.EmailField()
    college = forms.CharField(max_length=160)
    year = forms.CharField(max_length=80, required=False)
    password1 = forms.CharField(min_length=10, widget=forms.PasswordInput)
    password2 = forms.CharField(min_length=10, widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not re.fullmatch(r"[\w.@+-]+", username, flags=re.UNICODE):
            raise forms.ValidationError("Use letters, numbers, and @ . + - _ only.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("That email is already registered.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2") and cleaned["password1"] != cleaned["password2"]:
            self.add_error("password2", "Passwords do not match.")
        if cleaned.get("password1"):
            try:
                validate_password(cleaned["password1"])
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned


@require_http_methods(["GET", "POST"])
def sign_up(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            user = User.objects.create_user(
                username=data["username"], email=data["email"], password=data["password1"],
                first_name=data["full_name"].strip()[:30],
            )
            base_slug = slugify(data["username"])[:45] or "student"
            slug, suffix = base_slug, 1
            while StudentProfile.objects.filter(slug=slug).exists():
                suffix += 1
                slug = f"{base_slug[:45]}-{suffix}"
            name = data["full_name"].strip()
            initials = "".join(part[0] for part in name.split()[:2]).upper()[:8] or "TL"
            StudentProfile.objects.create(
                owner=user, slug=slug, name=name, initials=initials,
                college=data["college"].strip(), year=data["year"].strip(),
                is_demo=False, color="violet",
            )
        login(request, user)
        messages.success(request, "Your ThinkLink account is ready.")
        return redirect("dashboard")
    return render(request, "registration/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def sign_in(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect("dashboard")
    return render(request, "registration/login.html", {"form": form, "next": request.GET.get("next", "")})
