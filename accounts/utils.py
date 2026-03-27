"""
Безопасные редиректы после логина/OAuth.

django.contrib.auth.views.LoginView уже проверяет `next` через url_has_allowed_host_and_scheme.
Используйте эту функцию в кастомных обработчиках (OAuth callback, ?next= из внешних форм).
"""

from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


def safe_next_url(request, candidate: str | None, *, default: str = '/') -> str:
    if not candidate:
        return default
    if url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts=settings.ALLOWED_HOSTS,
        require_https=request.is_secure(),
    ):
        return candidate
    return default
