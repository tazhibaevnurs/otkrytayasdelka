"""
Подозрительная активность: частые 401/403 с одного IP; резкий рост числа запросов/мин (эвристика).
"""

import time

from django.conf import settings
from django.core.cache import cache

from accounts.ratelimit import get_client_ip
from core.security_logging import log_warning_event

# Пороги (можно переопределить env)
SUSPICIOUS_AUTH_FAILURE_THRESHOLD = int(
    getattr(settings, 'SUSPICIOUS_403_401_PER_MINUTE', 30)
)
ANOMALY_REQUESTS_PER_MINUTE = int(
    getattr(settings, 'ANOMALY_REQUESTS_PER_MINUTE', 400)
)


class SecurityMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = get_client_ip(request)
        now = time.time()
        minute_bucket = int(now // 60)

        # RPM: запросов с IP за текущую минуту
        rpm_key = f'sec:rpm:{ip}:{minute_bucket}'
        try:
            rpm = cache.incr(rpm_key)
        except ValueError:
            cache.add(rpm_key, 1, timeout=120)
            rpm = 1
        if rpm == ANOMALY_REQUESTS_PER_MINUTE + 1:
            log_warning_event(
                'anomaly_high_request_rate',
                ip=ip,
                rpm=rpm,
                path=request.path,
                threshold=ANOMALY_REQUESTS_PER_MINUTE,
            )

        response = self.get_response(request)

        status = getattr(response, 'status_code', 0)
        if status in (401, 403):
            fk = f'sec:authfail:{ip}:{minute_bucket}'
            try:
                cnt = cache.incr(fk)
            except ValueError:
                cache.add(fk, 1, timeout=120)
                cnt = 1
            if cnt == SUSPICIOUS_AUTH_FAILURE_THRESHOLD:
                log_warning_event(
                    'suspicious_auth_responses',
                    ip=ip,
                    last_status=status,
                    total_in_window=cnt,
                    path=request.path,
                    threshold=SUSPICIOUS_AUTH_FAILURE_THRESHOLD,
                )

        return response
