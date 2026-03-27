from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.http import HttpResponseForbidden
import time

from accounts.ratelimit import (
    LOGIN_PATHS,
    failure_cache_key,
    failure_window_seconds,
    get_client_ip,
)


class LoginFailureRateLimitMiddleware:
    """
    Login: не более 5 неудачных попыток / минуту на IP (админка и /accounts/login/).
    Счётчик — сигнал user_login_failed; при успешном входе сбрасывается (accounts.signals).
    Кэш Django (MVP); в production лучше Redis / Upstash.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and request.path in LOGIN_PATHS:
            ip = get_client_ip(request)
            key = failure_cache_key(ip)
            now = time.time()
            window = failure_window_seconds()
            times = cache.get(key, [])
            times = [t for t in times if now - t < window]
            if len(times) >= 5:
                return HttpResponseForbidden(
                    'Слишком много неудачных попыток входа. Подождите минуту.'
                )
        return self.get_response(request)


class AuthProtectedRoutesMiddleware:
    """Требует валидную сессию для префиксов из AUTH_PROTECTED_PATH_PREFIXES."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        for prefix in settings.AUTH_PROTECTED_PATH_PREFIXES:
            if path.startswith(prefix):
                if not request.user.is_authenticated:
                    return redirect_to_login(path, login_url=settings.LOGIN_URL)
                break
        return self.get_response(request)
