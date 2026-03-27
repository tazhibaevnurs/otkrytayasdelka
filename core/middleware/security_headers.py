"""
Дополнительные security-заголовки (CSP не применяется к /admin/ — совместимость админки Django).
"""

from django.conf import settings


class SecurityHeadersMiddleware:
    """CSP, Referrer-Policy, Permissions-Policy, X-Content-Type-Options (дублирует SECURE_CONTENT_TYPE_NOSNIFF)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(settings, 'SECURITY_HEADERS_DISABLE', False):
            return response

        path = request.path
        # Админка и DRF browsable API используют inline-скрипты/стили — без строгого CSP
        if path.startswith('/admin/'):
            response['X-Content-Type-Options'] = 'nosniff'
            response.setdefault('Referrer-Policy', 'same-origin')
            return response

        csp = getattr(settings, 'CONTENT_SECURITY_POLICY', None)
        if csp:
            response['Content-Security-Policy'] = csp

        response.setdefault('Referrer-Policy', getattr(settings, 'SECURE_REFERRER_POLICY', 'same-origin'))
        response.setdefault(
            'Permissions-Policy',
            'accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()',
        )
        response['X-Content-Type-Options'] = 'nosniff'
        return response
