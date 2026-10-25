from pathlib import Path
import os

from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

from django.core.exceptions import ImproperlyConfigured

_DEFAULT_DEVELOPMENT_SECRET = "thinklink-local-demo-key-change-before-deployment"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", _DEFAULT_DEVELOPMENT_SECRET)
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
if not DEBUG and (not CSRF_TRUSTED_ORIGINS or any(not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS)):
    raise ImproperlyConfigured("Set exact HTTPS origins in DJANGO_CSRF_TRUSTED_ORIGINS before production.")

# Fail closed when production mode is enabled with development-only secrets/hosts.
if not DEBUG and (
    SECRET_KEY == _DEFAULT_DEVELOPMENT_SECRET
    or SECRET_KEY.lower().startswith(("replace-", "change-", "your-"))
    or len(SECRET_KEY) < 50
):
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY to a unique, high-entropy secret (at least 50 characters) before production.")
if not DEBUG and (
    not os.getenv("DJANGO_ALLOWED_HOSTS", "").strip()
    or not ALLOWED_HOSTS
    or "*" in ALLOWED_HOSTS
    or all(host in {"localhost", "127.0.0.1"} for host in ALLOWED_HOSTS)
):
    raise ImproperlyConfigured("Set explicit production hostnames in DJANGO_ALLOWED_HOSTS before running with DJANGO_DEBUG=False.")
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "core",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "core.middleware.RequestBodyLimitMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    # Avoid stale persistent connections in Vercel's request-scoped Python functions.
    connection_age = int(os.getenv("DB_CONN_MAX_AGE", "0" if os.getenv("VERCEL") else "600"))
    database_config = dj_database_url.parse(DATABASE_URL, conn_max_age=connection_age)
    if not DEBUG and database_config["ENGINE"] == "django.db.backends.postgresql":
        database_config.setdefault("OPTIONS", {})["sslmode"] = "require"
    DATABASES = {"default": database_config}
else:
    if not DEBUG:
        raise ImproperlyConfigured("Set DATABASE_URL to persistent PostgreSQL for production; SQLite is development-only.")
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
if not DEBUG and DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production requires PostgreSQL; SQLite is not supported on serverless hosting.")
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
if not DEBUG:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
# Vercel terminates TLS and forwards the original protocol to the Django runtime.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Security defaults for the Django-rendered web application. Production hosting
# must terminate HTTPS correctly before enabling the default SSL redirect.
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", str(not DEBUG)).lower() in {"1", "true", "yes"}
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG

# Configure real SMTP credentials in Vercel for verification and recovery mail.
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in {"1", "true", "yes"}
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "ThinkLink <no-reply@thinklink.invalid>")
EMAIL_TIMEOUT = 10
if DEBUG and not EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
if not DEBUG and (not EMAIL_HOST or not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD or "@" not in DEFAULT_FROM_EMAIL or ".invalid" in DEFAULT_FROM_EMAIL):
    raise ImproperlyConfigured("Configure EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, and a real DEFAULT_FROM_EMAIL before production.")

# Structured security events; avoid logging emails, passwords, request bodies, or raw IPs.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "thinklink.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "thinklink.email": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}
