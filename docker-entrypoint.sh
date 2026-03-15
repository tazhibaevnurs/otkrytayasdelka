#!/bin/sh
set -e
# Каталоги для volume (SQLite, медиа) и права для appuser (volume при монтировании создаётся от root)
mkdir -p /app/data /app/media
chown -R appuser:appuser /app/data /app/media
# Миграции и gunicorn — от пользователя appuser (-- чтобы su не парсил аргументы gunicorn)
su appuser -s /bin/sh -c "python manage.py migrate --noinput"
exec su appuser -s /bin/sh -c 'exec "$@"' -- _ "$@"
