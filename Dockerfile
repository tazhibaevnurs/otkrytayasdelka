# Образ для деплоя Django (Открытая Сделка)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Зависимости системы (для Pillow и т.п.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python-зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код приложения
COPY . .

# Собираем статику (нужен SECRET_KEY на этапе import settings; runtime-ключ задаётся в .env)
RUN DJANGO_SECRET_KEY=collectstatic-build-only-not-for-runtime python manage.py collectstatic --noinput --clear

# Права на entrypoint
RUN chmod +x docker-entrypoint.sh

# Пользователь appuser (переключение в entrypoint после chown volume)
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app

EXPOSE 8000

# Запуск через entrypoint (migrate + gunicorn)
ENTRYPOINT ["./docker-entrypoint.sh"]
# --timeout: согласован с proxy_read_timeout в nginx (см. deploy/nginx-otkrytayasdelka.conf)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
