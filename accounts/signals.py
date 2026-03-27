import time

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core.cache import cache
from django.dispatch import receiver

from core.security_logging import log_event

from accounts.ratelimit import (
    LOGIN_PATHS,
    failure_cache_key,
    failure_window_seconds,
    get_client_ip,
)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request, **kwargs):
    if not request or request.method != 'POST' or request.path not in LOGIN_PATHS:
        return
    ip = get_client_ip(request)
    log_event(
        'auth_login_failed',
        ip=ip,
        path=request.path,
        username=(credentials.get('username') or '')[:200],
    )
    key = failure_cache_key(ip)
    now = time.time()
    window = failure_window_seconds()
    times = cache.get(key, [])
    times = [t for t in times if now - t < window]
    times.append(now)
    cache.set(key, times, int(window) + 5)


@receiver(user_logged_in)
def on_login_success(sender, request, user, **kwargs):
    if request:
        ip = get_client_ip(request)
        cache.delete(failure_cache_key(ip))
        log_event(
            'auth_login_success',
            ip=ip,
            path=request.path,
            user_id=user.pk,
            username=(user.get_username() or '')[:200],
        )
