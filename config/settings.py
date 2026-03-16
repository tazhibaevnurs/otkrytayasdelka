import mimetypes
import os
from pathlib import Path

# Чтобы загруженные .avif отдавались с правильным Content-Type
mimetypes.add_type('image/avif', '.avif')

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-change-in-production')

DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'core',
    'listings',
]

# WhiteNoise: раздача статики в production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

MEDIA_URL = 'media/'
MEDIA_ROOT = os.environ.get('DJANGO_MEDIA_ROOT', str(BASE_DIR / 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS: разрешаем запросы с фронта (Vite dev на порту 5173)
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
if not DEBUG:
    CORS_ALLOWED_ORIGINS.extend([
        'http://localhost:3000',
        'https://your-production-domain.com',
    ])

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
}

# Production: за прокси (nginx, load balancer)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    _origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
    if _origins:
        CSRF_TRUSTED_ORIGINS = [o.strip() for o in _origins.split(',') if o.strip()]
