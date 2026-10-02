import ipaddress

from django.conf import settings
from django.core.cache import cache


def _clean_ip(value):
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def get_client_ip(request):
    """
    Return the client IP as seen by the server.

    X-Forwarded-For is only used when TRUSTED_PROXY_COUNT > 0, and then only the
    entry added by your own proxies is read (counting from the right). Anything the
    client puts at the left of the header is ignored.
    """
    remote = request.META.get("REMOTE_ADDR", "")
    proxies = settings.TRUSTED_PROXY_COUNT

    if proxies > 0:
        header = request.META.get("HTTP_X_FORWARDED_FOR", "")
        parts = [p.strip() for p in header.split(",") if p.strip()]
        if len(parts) >= proxies:
            ip = _clean_ip(parts[-proxies])
            if ip:
                return ip

    return _clean_ip(remote) or "0.0.0.0"


def is_rate_limited(ip):
    """Allow RATE_LIMIT_POSTS form posts per RATE_LIMIT_WINDOW seconds per IP."""
    key = f"rl:{ip}"
    window = settings.RATE_LIMIT_WINDOW
    cache.add(key, 0, window)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        count = 1
    return count > settings.RATE_LIMIT_POSTS
