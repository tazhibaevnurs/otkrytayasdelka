import mimetypes
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# Чтобы загруженные .avif отдавались с правильным Content-Type
mimetypes.add_type('image/avif', '.avif')

BASE_DIR = Path(__file__).resolve().parent.parent

# Безопасное значение по умолчанию: на сервере DEBUG должен быть выключен.
# Для локальной разработки включайте явно: DJANGO_DEBUG=1
DEBUG = os.environ.get('DJANGO_DEBUG', '0') == '1'

# Секрет подписи — только из окружения в production; в dev допускается слабый fallback.
_secret = (os.environ.get('DJANGO_SECRET_KEY') or '').strip()
if not DEBUG:
    if not _secret:
        raise ImproperlyConfigured(
            'Задайте переменную окружения DJANGO_SECRET_KEY (длинная случайная строка). '
            'Не храните её в репозитории.'
        )
    SECRET_KEY = _secret
else:
    SECRET_KEY = _secret or 'dev-only-change-me-not-for-production'

# Пароли: Argon2 — предпочтительный алгоритм (не MD5/SHA1).
AUTH_PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
]

# Сессии: срок жизни и защита cookie (инвалидация при logout — стандартное flush).
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = False
# 12 часов неактивности; при logout сессия уничтожается полностью.
SESSION_COOKIE_AGE = int(os.environ.get('DJANGO_SESSION_COOKIE_AGE', str(60 * 60 * 12)))
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', '1') == '1'
    # HTTPS: HSTS (заголовок Strict-Transport-Security)
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', str(365 * 24 * 60 * 60)))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('DJANGO_HSTS_INCLUDE_SUBDOMAINS', '1') == '1'
    SECURE_HSTS_PRELOAD = os.environ.get('DJANGO_HSTS_PRELOAD', '0') == '1'
else:
    SECURE_HSTS_SECONDS = 0

# Заголовки безопасности (часть дублируется в SecurityHeadersMiddleware для CSP)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# Сброс пароля: одноразовый токен (недействителен после смены пароля) и срок жизни 1 час.
PASSWORD_RESET_TIMEOUT = 3600

# Кэш для rate limiting неудачных входов (в production лучше Redis).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'auth-rate-limit',
    }
}

LOGIN_URL = '/accounts/login/'
LOGOUT_REDIRECT_URL = '/'

# Публичная регистрация с обязательной верификацией email (новые аккаунты неактивны до перехода по ссылке).
REGISTRATION_OPEN = os.environ.get('DJANGO_REGISTRATION_OPEN', '0') == '1'

# Префиксы URL, для которых требуется аутентифицированная сессия (дополнительно к правам в админке).
AUTH_PROTECTED_PATH_PREFIXES = tuple(
    p.strip()
    for p in os.environ.get('DJANGO_AUTH_PROTECTED_PREFIXES', '/accounts/profile/').split(',')
    if p.strip()
)

# Почта: верификация и сброс пароля. В dev по умолчанию — консоль.
EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('DJANGO_EMAIL_USE_TLS', '1') == '1'
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', 'webmaster@localhost')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'rest_framework',
    'corsheaders',
    'accounts',
    'captcha',
    'core',
    'listings',
]

# WhiteNoise: раздача статики в production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.security_headers.SecurityHeadersMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.LoginFailureRateLimitMiddleware',
    'accounts.middleware.AuthProtectedRoutesMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.security_monitoring.SecurityMonitoringMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.section_images',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# База: PostgreSQL по DATABASE_URL (Docker/production) или SQLite по умолчанию
_db_url = os.environ.get('DATABASE_URL', '').strip()
if _db_url.startswith('postgres://'):
    _db_url = 'postgresql' + _db_url[9:]
if _db_url.startswith('postgresql://'):
    import re
    _m = re.match(
        r'postgresql://(?:([^:]+):([^@]*)@)?([^:/]+)(?::(\d+))?/(.+)',
        _db_url
    )
    if _m:
        _user, _pw, _host, _port, _path = _m.groups()
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': _path.split('?')[0].strip('/') or 'postgres',
                'USER': _user or 'postgres',
                'PASSWORD': _pw or '',
                'HOST': _host or 'db',
                'PORT': _port or '5432',
                'OPTIONS': {},
            }
        }
    else:
        _sqlite_path = os.environ.get('DJANGO_DB_PATH', str(BASE_DIR / 'db.sqlite3'))
        DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': _sqlite_path}}
else:
    _sqlite_path = os.environ.get('DJANGO_DB_PATH', str(BASE_DIR / 'db.sqlite3'))
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': _sqlite_path}}

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Asia/Bishkek'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# WhiteNoise ругается, если каталога нет; в .gitignore — создаём при старте (collectstatic тоже заполнит).
try:
    STATIC_ROOT.mkdir(parents=True, exist_ok=True)
except OSError:
    pass
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

MEDIA_URL = 'media/'
MEDIA_ROOT = os.environ.get('DJANGO_MEDIA_ROOT', str(BASE_DIR / 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Лимит размера тела запроса (не-файловые поля форм / JSON API).
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024  # 1 МБ
# Файлы больше порога пишутся во временный файл; суммарно загрузки — до 10 МБ на файл в памяти до spill.
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 МБ

# AI (заглушка /api/ai/generate/): дневной лимит; pro — группа Django с именем ниже.
AI_RATE_LIMIT_FREE_DAILY = int(os.environ.get('AI_RATE_LIMIT_FREE_DAILY', '5'))
AI_RATE_LIMIT_PRO_DAILY = int(os.environ.get('AI_RATE_LIMIT_PRO_DAILY', '50'))
AI_PRO_GROUP_NAME = os.environ.get('AI_PRO_GROUP_NAME', 'subscription_pro')

# CAPTCHA (django-simple-captcha); в DEBUG можно пропускать проверку в тестах
CAPTCHA_TEST_MODE = DEBUG

# CORS: без wildcard; в production только явный список (через запятую в env).
CORS_ALLOW_ALL_ORIGINS = False
if DEBUG:
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ]
else:
    _cors = os.environ.get('DJANGO_CORS_ALLOWED_ORIGINS', '').strip()
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors.split(',') if o.strip()]

# Content-Security-Policy (переопределение: DJANGO_CSP). Для /admin/ CSP не задаётся (см. middleware).
_default_csp = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: https: http:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)
CONTENT_SECURITY_POLICY = os.environ.get('DJANGO_CSP', _default_csp).strip() or None

# Мониторинг (middleware)
SUSPICIOUS_403_401_PER_MINUTE = int(os.environ.get('DJANGO_SUSPICIOUS_AUTH_PER_MIN', '30'))
ANOMALY_REQUESTS_PER_MINUTE = int(os.environ.get('DJANGO_ANOMALY_RPM', '400'))

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_THROTTLE_CLASSES': [
        'listings.throttles.BurstUserRateThrottle',
        'listings.throttles.BurstAnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'api_burst_user': '100/min',
        'api_burst_anon': '100/min',
    },
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
}

# Вместо стандартной тех-страницы CSRF 403 показываем аккуратную страницу для пользователя.
CSRF_FAILURE_VIEW = 'core.views.csrf_failure'

# Production: за прокси (nginx, load balancer)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    _origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
    if _origins:
        CSRF_TRUSTED_ORIGINS = [o.strip() for o in _origins.split(',') if o.strip()]

# Структурированные security-логи (JSON в stdout — удобно для Docker / journald / ELK)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'security_json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'fmt': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'security_stdout': {
            'class': 'logging.StreamHandler',
            'formatter': 'security_json',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['security_stdout'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
