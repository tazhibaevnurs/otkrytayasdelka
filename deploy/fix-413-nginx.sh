#!/usr/bin/env bash
# Исправление HTTP 413 при загрузке фото (nginx client_max_body_size).
# Запуск на сервере: sudo ./deploy/fix-413-nginx.sh
#
# По умолчанию ищет конфиг с otkrytayasdelka в /etc/nginx/sites-enabled/
# или передайте путь: sudo NGINX_CONF=/etc/nginx/sites-enabled/site ./deploy/fix-413-nginx.sh

set -euo pipefail

SIZE="${CLIENT_MAX_BODY_SIZE:-320M}"
CONF="${NGINX_CONF:-}"

if [[ -z "$CONF" ]]; then
  for c in /etc/nginx/sites-enabled/*; do
    [[ -f "$c" ]] || continue
    if grep -q 'otkrytayasdelka' "$c" 2>/dev/null; then
      CONF="$c"
      break
    fi
  done
fi

if [[ -z "$CONF" || ! -f "$CONF" ]]; then
  echo "Не найден nginx-конфиг. Укажите: sudo NGINX_CONF=/path/to/site $0" >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Запустите с sudo: sudo $0" >&2
  exit 1
fi

echo "=== Было (client_max_body_size) ==="
nginx -T 2>/dev/null | grep client_max_body_size || echo "(не задано — nginx по умолчанию 1M → 413 на фото >1 МБ)"

echo "=== Правим $CONF → $SIZE ==="
if grep -q 'client_max_body_size' "$CONF"; then
  sed -i "s/client_max_body_size[^;]*;/client_max_body_size ${SIZE};/g" "$CONF"
else
  sed -i "/server_name.*otkrytayasdelka/s/;/;\n    client_max_body_size ${SIZE};/g" "$CONF"
fi

nginx -t
systemctl reload nginx

echo "=== Стало ==="
nginx -T 2>/dev/null | grep client_max_body_size
echo "Готово. Проверьте загрузку фото в админке."
