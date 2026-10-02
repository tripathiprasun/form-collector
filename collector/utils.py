from django.conf import settings
from django.core.cache import cache


def is_rate_limited():
    """
    Flood guard: allow RATE_LIMIT_POSTS form posts per RATE_LIMIT_WINDOW seconds
    across the whole site. Nothing about the visitor is read or stored.
    """
    key = "form-posts"
    window = settings.RATE_LIMIT_WINDOW
    cache.add(key, 0, window)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        count = 1
    return count > settings.RATE_LIMIT_POSTS
