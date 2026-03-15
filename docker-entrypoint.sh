#!/bin/sh
set -e

# Каталоги для volume (SQLite, медиа)
mkdir -p /app/data /app/media 2>/dev/null || true

# Миграции (для SQLite выполнятся сразу; для PostgreSQL — после старта БД)
python manage.py migrate --noinput

# Передаём управление команде из CMD (gunicorn)
exec "$@"
