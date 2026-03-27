"""Лимиты DRF: API (100/мин) и AI (5/день free, 50/день pro по группе)."""

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.throttling import AnonRateThrottle, BaseThrottle, UserRateThrottle

from accounts.ratelimit import get_client_ip


class BurstUserRateThrottle(UserRateThrottle):
    scope = 'api_burst_user'


class BurstAnonRateThrottle(AnonRateThrottle):
    scope = 'api_burst_anon'


class AIDailyThrottle(BaseThrottle):
    """
    POST к AI-эндпоинту: free — AI_RATE_LIMIT_FREE_DAILY, pro — группа AI_PRO_GROUP_NAME.
    """

    def allow_request(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        ident = self._ident(request)
        key = f'ai_daily:{timezone.now().date()}:{ident}'
        limit = self._limit(request.user)
        n = cache.get(key, 0)
        if n >= limit:
            return False
        cache.set(key, n + 1, timeout=86400)
        return True

    def _ident(self, request):
        if request.user.is_authenticated:
            return f'u{request.user.pk}'
        return f'ip{get_client_ip(request)}'

    def _limit(self, user):
        pro_name = getattr(settings, 'AI_PRO_GROUP_NAME', 'subscription_pro')
        pro_limit = int(getattr(settings, 'AI_RATE_LIMIT_PRO_DAILY', 50))
        free_limit = int(getattr(settings, 'AI_RATE_LIMIT_FREE_DAILY', 5))
        if user.is_authenticated and user.groups.filter(name=pro_name).exists():
            return pro_limit
        return free_limit
