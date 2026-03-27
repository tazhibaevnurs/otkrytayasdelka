# Безопасный деплой и мониторинг (Django)

Проект разворачивается как **Django + Gunicorn + Nginx** (или Docker). **Vercel** и **Supabase** в типичной схеме не обязательны; ниже — как перенести принципы на ваш стек.

## 1. HTTPS и HSTS

- В production задайте `DJANGO_DEBUG=0`, `DJANGO_SECURE_SSL_REDIRECT=1`.
- Включены: `SECURE_HSTS_SECONDS` (по умолчанию 1 год), опционально `DJANGO_HSTS_PRELOAD=1` после проверки на [hstspreload.org](https://hstspreload.org/).
- За **reverse proxy** обязательно: `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` и реальные `CSRF_TRUSTED_ORIGINS` / `DJANGO_ALLOWED_HOSTS`.

## 2. Секреты

- **Не храните** ключи в репозитории. Используйте переменные окружения на сервере, **Docker secrets**, **Kubernetes Secrets**, **Vault**, или секреты платформы (аналог Vercel Environment Variables для PaaS).
- **Supabase Vault** — если БД на Supabase: храните `DATABASE_URL` и пароли только в панели/секретах, не в коде.

## 3. База данных из интернета

- **PostgreSQL**: не публикуйте порт `5432` в публичный интернет. В Docker — только внутренняя сеть `db:5432`, без `ports: "5432:5432"` на хост.
- Используйте **firewall** (ufw, security groups), **allowlist IP** для админ-доступа к БД при необходимости.
- **SQLite** в Docker: том только на сервере, не в общедоступном volume без нужды.

## 4. CORS

- В production список `DJANGO_CORS_ALLOWED_ORIGINS` — **только явные HTTPS-URL** вашего фронта, без `*`.
- `CORS_ALLOW_ALL_ORIGINS = False` в коде.

## 5. Заголовки

- Настроены: `X-Frame-Options` (DENY), `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, **CSP** для публичных страниц (не для `/admin/`).
- CSP можно переопределить переменной `DJANGO_CSP`.

## 6–7. Логирование и аномалии

- Логгер `security` (JSON в **stdout**): события `auth_login_success`, `auth_login_failed`, `api_error`, `suspicious_auth_responses`, `anomaly_high_request_rate`.
- Собирайте логи контейнера в **journald**, **Loki**, **CloudWatch**, **ELK** и настройте алерты по ключевым словам.
- Пороги: `DJANGO_SUSPICIOUS_AUTH_PER_MIN`, `DJANGO_ANOMALY_RPM`.

## 8. Бэкапы БД

- **Supabase**: включите ежедневные бэкапы в панели проекта.
- **Свой PostgreSQL**: `pg_dump` по cron + off-site хранение; проверяйте восстановление.

## 9. Preview / staging

- **Preview** (аналог Vercel Preview): отдельный `DATABASE_URL` для staging, **никогда** не указывайте продакшн-БД в preview-окружении.
- Отдельные `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` для preview.

## Nginx (пример)

- SSL termination на Nginx, прокси на Gunicorn с заголовками `X-Forwarded-Proto`, `X-Forwarded-For`.
- `client_max_body_size` согласован с лимитами Django (см. `deploy/nginx-otkrytayasdelka.conf`).
