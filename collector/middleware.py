import hashlib

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

FAIL_LIMIT = 5
LOCK_SECONDS = 15 * 60


class SecurityHeadersMiddleware:
    """Extra response headers. The strict CSP is for public pages only (not the admin)."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_prefix = "/" + settings.ADMIN_URL.strip("/") + "/"

    def __call__(self, request):
        response = self.get_response(request)
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response["Cross-Origin-Opener-Policy"] = "same-origin"
        response["X-Robots-Tag"] = "noindex, nofollow"
        if not request.path.startswith(self.admin_prefix):
            response["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; "
                "base-uri 'self'; form-action 'self'"
            )
        return response


class AdminLoginThrottleMiddleware:
    """Lock a username for 15 minutes after 5 failed admin logins (no IP involved)."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.login_path = "/" + settings.ADMIN_URL.strip("/") + "/login/"

    def __call__(self, request):
        key = None
        if request.method == "POST" and request.path == self.login_path:
            username = request.POST.get("username", "").strip().lower()[:150]
            key = "loginfail:" + hashlib.sha256(username.encode()).hexdigest()
            if cache.get(key, 0) >= FAIL_LIMIT:
                return HttpResponse(
                    "Too many failed login attempts. Try again in 15 minutes.",
                    status=429,
                    content_type="text/plain",
                )

        response = self.get_response(request)

        if key:
            if response.status_code == 200:  # login form shown again = failure
                cache.add(key, 0, LOCK_SECONDS)
                try:
                    cache.incr(key)
                except ValueError:
                    cache.set(key, 1, LOCK_SECONDS)
            elif response.status_code in (301, 302):  # redirected = success
                cache.delete(key)
        return response
