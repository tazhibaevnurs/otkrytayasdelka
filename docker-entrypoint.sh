#!/bin/sh
set -e
# Каталоги для volume и права для appuser (bind mount создаётся от root)
mkdir -p /app/data /app/media /app/staticfiles
chown -R appuser:appuser /app/data /app/media /app/staticfiles
# Подготавливаем статику в bind mount, чтобы nginx отдавал её напрямую.
su appuser -s /bin/sh -c "python manage.py collectstatic --noinput"
# Миграции и gunicorn — от пользователя appuser (-- чтобы su не парсил аргументы gunicorn)
su appuser -s /bin/sh -c "python manage.py migrate --noinput"
exec su appuser -s /bin/sh -c 'exec "$@"' -- _ "$@"
