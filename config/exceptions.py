"""Логирование ответов API с кодами 4xx/5xx."""

from rest_framework.views import exception_handler as drf_exception_handler

from core.security_logging import log_warning_event


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    request = context.get('request')
    path = getattr(request, 'path', '') if request else ''
    method = getattr(request, 'method', '') if request else ''

    if response is not None:
        status = response.status_code
        # 405 — нормальная ситуация (не тот HTTP-метод), не событие для security-логов / шума в тестах.
        if status == 405:
            return response
        if status >= 400:
            detail = getattr(exc, 'detail', None)
            if detail is None:
                detail = str(exc)
            else:
                detail = str(detail)
            log_warning_event(
                'api_error',
                http_status=status,
                path=path,
                method=method,
                detail=detail[:500],
            )
    return response
