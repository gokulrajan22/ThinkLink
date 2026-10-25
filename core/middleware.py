"""Request-size guard for expensive or user-controlled payloads."""
from django.http import HttpResponse


class RequestBodyLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raw_length = request.META.get("CONTENT_LENGTH")
        try:
            length = int(raw_length) if raw_length else 0
        except (TypeError, ValueError):
            return HttpResponse("Invalid Content-Length.", status=400)
        # Project briefs and profile forms need far less than 64 KiB.
        if length > 65536:
            return HttpResponse("Request body is too large.", status=413)
        return self.get_response(request)
