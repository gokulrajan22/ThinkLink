"""Account creation, verification, and sign-in views for ThinkLink."""
import re

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core import signing
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from .models import StudentProfile
from .privacy_views import PRIVACY_POLICY_VERSION
from .security import rate_limit


class SignUpForm(forms.Form):
    username = forms.CharField(max_length=150)
    full_name = forms.CharField(max_length=120)
    email = forms.EmailField()
    college = forms.CharField(max_length=160)
    year = forms.CharField(max_length=80, required=False)
    password1 = forms.CharField(min_length=10, widget=forms.PasswordInput)
    password2 = forms.CharField(min_length=10, widget=forms.PasswordInput)
    privacy_consent = forms.BooleanField(required=True, label="I have read the Privacy Notice and consent to ThinkLink processing my profile and submitted project brief to provide team-analysis features.")

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
                from django.contrib.auth.password_validation import validate_password
                validate_password(cleaned["password1"])
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned


def _verification_token(user):
    return signing.dumps({"user_id": user.pk, "email": user.email}, salt="thinklink.email-verification")


def _send_verification_email(request, user):
    token = _verification_token(user)
    url = request.build_absolute_uri(reverse("verify-email", kwargs={"token": token}))
    send_mail(
        "Verify your ThinkLink email address",
        f"Verify your email within 24 hours by opening this link:\n\n{url}\n\nIf you did not create this account, ignore this message.",
        getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@thinklink.invalid"),
        [user.email],
        fail_silently=False,
    )


@require_http_methods(["GET", "POST"])
@rate_limit("signup", 5, 3600)
def sign_up(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            user = User.objects.create_user(
                username=data["username"], email=data["email"], password=data["password1"],
                first_name=data["full_name"].strip()[:30], is_active=False,
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
                is_demo=False, color="violet", privacy_consent_at=__import__("django.utils.timezone", fromlist=["now"]).now(),
                privacy_policy_version=PRIVACY_POLICY_VERSION,
            )
        try:
            _send_verification_email(request, user)
        except Exception:
            # Do not expose SMTP/provider details. Staff can inspect server logs.
            import logging
            logging.getLogger("thinklink.email").exception("Verification email delivery failed")
            user.delete()
            messages.error(request, "Verification email could not be sent, so no account was retained. Please try again later or contact support.")
            return render(request, "registration/signup.html", {"form": form}, status=503)
        messages.success(request, "Check your email for a verification link before signing in.")
        return redirect("login")
    return render(request, "registration/signup.html", {"form": form})


@require_http_methods(["GET"])
@rate_limit("email-verification", 20, 3600)
def verify_email(request, token):
    try:
        data = signing.loads(token, salt="thinklink.email-verification", max_age=86400)
        user = User.objects.get(pk=data["user_id"], email=data["email"])
    except (signing.BadSignature, signing.SignatureExpired, User.DoesNotExist, KeyError, TypeError):
        messages.error(request, "That verification link is invalid or has expired. Please register again or contact support.")
        return redirect("login")
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
        messages.success(request, "Email verified. You can now sign in.")
    else:
        messages.info(request, "This email address is already verified.")
    return redirect("login")


class ResendVerificationForm(forms.Form):
    email = forms.EmailField()


@require_http_methods(["GET", "POST"])
@rate_limit("resend-verification", 5, 3600)
def resend_verification(request):
    form = ResendVerificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=False).first()
        if user:
            try:
                _send_verification_email(request, user)
            except Exception:
                import logging
                logging.getLogger("thinklink.email").exception("Verification resend failed")
        # Same response for known and unknown addresses to reduce account enumeration.
        messages.success(request, "If that address has an unverified ThinkLink account, a verification email has been sent.")
        return redirect("login")
    return render(request, "registration/resend_verification.html", {"form": form})


@require_http_methods(["GET", "POST"])
@rate_limit("login", 10, 900, identity_getter=lambda request: request.POST.get("username", ""))
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
