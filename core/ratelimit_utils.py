"""Лимиты на основе Django cache (MVP; для продакшена лучше Redis / Upstash)."""

import time

from django.core.cache import cache
from django.http import HttpResponse

from accounts.ratelimit import get_client_ip

# Регистрация: не более N успешных попыток создания аккаунта за окно (секунд) с одного IP.
REGISTRATION_WINDOW_SEC = 3600
REGISTRATION_MAX_PER_WINDOW = 3


def check_registration_rate_limit(request):
    """
    Вызывать до обработки POST /accounts/register/.
    Возвращает HttpResponse 429 или None.
    """
    if request.method != 'POST':
        return None
    ip = get_client_ip(request)
    key = f'reg:window:{ip}'
    now = time.time()
    times = cache.get(key, [])
    times = [t for t in times if now - t < REGISTRATION_WINDOW_SEC]
    cache.set(key, times, REGISTRATION_WINDOW_SEC + 10)
    if len(times) >= REGISTRATION_MAX_PER_WINDOW:
        return HttpResponse(
            'Слишком много регистраций с этого адреса. Попробуйте позже.',
            status=429,
            content_type='text/plain; charset=utf-8',
        )
    return None


def record_successful_registration(request):
    """Вызывать только после успешного User.objects.create_user для регистрации."""
    ip = get_client_ip(request)
    key = f'reg:window:{ip}'
    now = time.time()
    times = cache.get(key, [])
    times = [t for t in times if now - t < REGISTRATION_WINDOW_SEC]
    times.append(now)
    cache.set(key, times, REGISTRATION_WINDOW_SEC + 10)
