"""Persistent database-backed abuse controls suitable for multi-instance hosting."""
import hashlib
import logging
import time
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone

from .models import RateLimitBucket

logger = logging.getLogger("thinklink.security")


def client_ip(request):
    # REMOTE_ADDR avoids trusting client-controlled forwarding headers. Confirm
    # proxy behavior on the deployed platform before enabling public traffic.
    return request.META.get("REMOTE_ADDR", "unknown")[:64]


def rate_limit(scope, limit, window_seconds=900, identity_getter=None):
    """Enforce shared IP and optional account-identity limits in the database."""
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method == "GET":
                return view(request, *args, **kwargs)
            ip = client_ip(request)
            keys = [hashlib.sha256(f"{scope}|ip|{ip}".encode()).hexdigest()]
            if identity_getter:
                try:
                    identity = str(identity_getter(request) or "").strip().lower()[:160]
                except Exception:
                    identity = ""
                if identity:
                    keys.append(hashlib.sha256(f"{scope}|identity|{identity}".encode()).hexdigest())
            now = int(time.time())
            window = now // window_seconds * window_seconds
            blocked = False
            try:
                with transaction.atomic():
                    for key in keys:
                        bucket, _ = RateLimitBucket.objects.select_for_update().get_or_create(
                            key=key, defaults={"scope": scope, "window_start": window, "count": 0}
                        )
                        if bucket.window_start != window:
                            bucket.window_start = window
                            bucket.count = 0
                        bucket.count += 1
                        bucket.last_seen_at = timezone.now()
                        bucket.save(update_fields=["window_start", "count", "last_seen_at"])
                        blocked = blocked or bucket.count > limit
            except Exception:
                logger.exception("Rate limiter storage unavailable for scope=%s", scope)
                if not settings.DEBUG:
                    return HttpResponse("Temporarily unavailable. Please try again shortly.", status=503)
                # In development, do not block local development if DB is unavailable.
                return view(request, *args, **kwargs)
            if blocked:
                logger.warning("Rate limit exceeded scope=%s ip_hash=%s", scope, hashlib.sha256(ip.encode()).hexdigest()[:12])
                response = HttpResponse("Too many requests. Please wait and try again.", status=429)
                response["Retry-After"] = str(window_seconds - (now % window_seconds))
                return response
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
