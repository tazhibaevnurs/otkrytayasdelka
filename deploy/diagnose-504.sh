#!/usr/bin/env bash
# Диагностика 504 Gateway Time-out для otkrytayasdelka.kg
# Запуск на сервере из каталога с docker-compose.yml:
#   chmod +x deploy/diagnose-504.sh && ./deploy/diagnose-504.sh

set -u

APP_DIR="${APP_DIR:-$(pwd)}"
MEDIA_DIR="${MEDIA_DIR:-$APP_DIR/media}"
STATIC_DIR="${STATIC_DIR:-$APP_DIR/staticfiles}"
DATA_DIR="${DATA_DIR:-$APP_DIR/data}"

hr() { printf '\n%s\n' "======== $* ========"; }
run() { printf '> %s\n' "$*"; eval "$@" 2>&1 || true; }

hr "Окружение"
run "date"
run "hostname"
run "uptime"
run "df -h \"$APP_DIR\" \"$MEDIA_DIR\" 2>/dev/null || df -h ."

hr "Docker"
if command -v docker >/dev/null 2>&1; then
  run "docker compose -f \"$APP_DIR/docker-compose.yml\" ps -a"
  run "docker compose -f \"$APP_DIR/docker-compose.yml\" logs --tail=80 web"
  run "docker inspect --format='{{.State.Health.Status}}' otkrytaya-sdelka-web 2>/dev/null"
else
  echo "docker не найден"
fi

hr "Gunicorn / Django (localhost:8000)"
for path in /healthz / /catalog/; do
  run "curl -sS -o /dev/null -w '${path} -> HTTP %{http_code} за %{time_total}s\n' --connect-timeout 5 --max-time 30 \"http://127.0.0.1:8000${path}\""
done

hr "Nginx: /media/ и /static/ отдаются с диска?"
if command -v nginx >/dev/null 2>&1; then
  run "nginx -T 2>/dev/null | grep -A6 'location /media/' || true"
  run "nginx -T 2>/dev/null | grep -A6 'location /static/' || true"
  run "nginx -T 2>/dev/null | grep -E 'proxy_read_timeout|proxy_pass' | head -20"
else
  echo "nginx не найден (проверьте конфиг вручную: deploy/nginx-otkrytayasdelka.conf)"
fi

hr "Проверка медиа через nginx (не должно идти в Django)"
SAMPLE="$(find "$MEDIA_DIR" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) 2>/dev/null | head -1)"
if [ -n "$SAMPLE" ] && [ -f "$SAMPLE" ]; then
  REL="${SAMPLE#$MEDIA_DIR/}"
  run "curl -sS -o /dev/null -w '/media/${REL} -> HTTP %{http_code} за %{time_total}s (размер заголовка)\n' --connect-timeout 5 --max-time 15 -I \"https://otkrytayasdelka.kg/media/${REL}\""
  run "ls -lh \"$SAMPLE\""
else
  echo "Файлы в $MEDIA_DIR не найдены"
fi

hr "Тяжёлые фото в media/ (топ-15 по размеру)"
if [ -d "$MEDIA_DIR" ]; then
  run "find \"$MEDIA_DIR\" -type f \\( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' -o -iname '*.gif' \\) -printf '%s %p\n' 2>/dev/null | sort -rn | head -15 | awk '{printf \"%.1f MB  %s\\n\", \$1/1024/1024, \$2}'"
  run "find \"$MEDIA_DIR\" -type f | wc -l"
else
  echo "Каталог media отсутствует: $MEDIA_DIR"
fi

hr "Превью каталога (image_thumbnail)"
if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q otkrytaya-sdelka-web; then
  run "docker compose -f \"$APP_DIR/docker-compose.yml\" exec -T web python manage.py shell -c \"
from listings.models import Listing
total = Listing.objects.count()
with_img = Listing.objects.exclude(image='').count()
with_thumb = Listing.objects.exclude(image_thumbnail='').count()
missing = Listing.objects.exclude(image='').filter(image_thumbnail='').count()
print(f'Объявлений: {total}, с фото: {with_img}, с превью: {with_thumb}, без превью (грузят оригинал): {missing}')
\""
else
  echo "Контейнер web не запущен — пропуск проверки БД"
fi

hr "База данных"
if [ -f "$DATA_DIR/db.sqlite3" ]; then
  run "ls -lh \"$DATA_DIR/db.sqlite3\""
  echo "ВНИМАНИЕ: SQLite под нагрузкой может блокироваться → медленные ответы и 504. Рекомендуется PostgreSQL (DATABASE_URL в .env)."
elif [ -f "$APP_DIR/.env" ]; then
  if grep -q '^DATABASE_URL=postgresql' "$APP_DIR/.env" 2>/dev/null; then
    echo "Используется PostgreSQL (DATABASE_URL)"
  else
    echo "db.sqlite3 не найден; проверьте DATABASE_URL в .env"
  fi
fi

hr "Рекомендации (кратко)"
cat <<'EOF'
1. Если curl 127.0.0.1:8000/healthz не 200 за <1с — Gunicorn завис/перегружен:
   docker compose restart web
   docker compose logs -f web
2. Если healthz OK, а снаружи 504 — смотрите nginx (proxy_pass, таймауты, location /media/).
3. location /media/ должен быть alias на диск, НЕ proxy_pass на :8000 (см. deploy/nginx-otkrytayasdelka.conf).
4. Тяжёлые фото (>5 МБ) при загрузке в админке блокируют воркер (Pillow + запись на диск).
   Лимит уже 5 МБ/файл; грузите пачками по 5–10, не 30 сразу.
5. Объявления без image_thumbnail отдают полный оригинал в каталоге — выполните:
   docker compose exec web python manage.py regenerate_listing_thumbnails
6. При постоянной нагрузке увеличьте воркеры Gunicorn (см. Dockerfile, WEB_CONCURRENCY) или RAM на сервере.
EOF
