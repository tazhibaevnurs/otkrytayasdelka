"""Общие константы и IP для ограничения попыток входа (админка + /accounts/login/)."""

from django.conf import settings

LOGIN_PATHS = frozenset(('/admin/login/', '/accounts/login/'))
_FAILURE_WINDOW_SEC = 60.0


def get_client_ip(request):
    if not settings.DEBUG:
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or ''


def failure_cache_key(ip: str) -> str:
    return f'login_fail_window:{ip}'


def failure_window_seconds() -> float:
    return _FAILURE_WINDOW_SEC
