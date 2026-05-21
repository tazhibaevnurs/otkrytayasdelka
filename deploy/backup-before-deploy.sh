#!/usr/bin/env bash
# Резервная копия перед деплоем (на сервере, из корня проекта рядом с docker-compose.yml).
# Использует одноразовый контейнер web: dumpdata (+ pg_dump для PostgreSQL) без bind-mount прав.
#
# Переменные окружения (опционально):
#   BACKUP_MEDIA=1          — упаковать ./media в media.tgz (может быть тяжёлым).
#   BACKUP_KEEP_DAYS=14     — удалять каталоги backups/pre-deploy-* старше N дней (0 = не чистить).
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f docker-compose.yml ]]; then
  echo "Ожидался файл docker-compose.yml в $ROOT" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Предупреждение: нет файла .env рядом с docker-compose.yml (compose и бэкап могут не видеть секреты БД)." >&2
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${ROOT}/backups/pre-deploy-${STAMP}"
mkdir -p "$DEST"

echo "[backup] Каталог: $DEST"

# Одноразовый запуск без entrypoint (без migrate/collectstatic в docker-entrypoint.sh).
DOCKER_RUN=(
  docker compose run --rm --no-deps -T --entrypoint ""
)

# Django JSON dump (Postgres и SQLite — корректно для типичного восстановления через loaddata).
echo "[backup] dumpdata.json.gz ..."
"${DOCKER_RUN[@]}" web \
  su appuser -s /bin/sh -c \
  'cd /app && python manage.py dumpdata \
    --natural-foreign --natural-primary \
    --exclude=contenttypes \
    --exclude=auth.permission \
    --exclude=sessions \
    --indent 1' |
  gzip -c >"${DEST}/django.dumpdata.json.gz"

# Не делаем source .env: в production-файлах часто строки в стиле docker/dotenv,
# которые bash не может выполнить (например значение без KEY= на отдельной строке).
# Берём только DATABASE_URL построчным разбором.
_DB_URL="${DATABASE_URL:-}"
if [[ -f .env ]]; then
  _line="$(grep -E '^[[:space:]]*DATABASE_URL=' .env 2>/dev/null | tail -n1 || true)"
  if [[ -n "${_line}" ]]; then
    _from_file="${_line#*=}"
    _from_file="${_from_file%$'\r'}"
    _from_file="$(printf '%s' "${_from_file}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    if [[ "${_from_file}" == \"*\" ]]; then
      _from_file="${_from_file#\"}"
      _from_file="${_from_file%\"}"
    elif [[ "${_from_file}" == \'*\' ]]; then
      _from_file="${_from_file#\'}"
      _from_file="${_from_file%\'}"
    fi
    _DB_URL="${_from_file}"
  fi
fi

# Postgres: логический дамп через pg_dump (client внутри образа).
if [[ -n "${_DB_URL}" ]] && [[ "${_DB_URL}" == postgres* ]]; then
  echo "[backup] postgres.sql.gz (pg_dump) ..."
  "${DOCKER_RUN[@]}" web \
    su appuser -s /bin/sh -c \
    'cd /app && exec pg_dump "$DATABASE_URL" --no-owner --no-acl --encoding=UTF8' |
    gzip -c >"${DEST}/postgres.sql.gz"
fi

# SQLite на хосте (параллельно с записью возможна неконсистентность при работающем web).
# Без скобок в [[ ... ]] — на старых bash иначе syntax error около ']]'.
if [[ -f ./data/db.sqlite3 ]]; then
  if [[ -z "${_DB_URL}" ]] || [[ "${_DB_URL}" != postgres* ]]; then
    echo "[backup] db.sqlite3 (копия файла на хосте) ..."
    cp -a ./data/db.sqlite3 "${DEST}/db.sqlite3"
  fi
fi

if [[ "${BACKUP_MEDIA:-0}" == "1" ]] && [[ -d ./media ]] && [[ -n "$(find ./media -mindepth 1 -print -quit 2>/dev/null)" ]]; then
  echo "[backup] media.tgz ..."
  tar -czf "${DEST}/media.tgz" --exclude='.gitkeep' -C "$ROOT" media
fi

# Ротация (BACKUP_KEEP_DAYS=0 — не удалять старые бэкапы)
KEEP="${BACKUP_KEEP_DAYS:-14}"
if [[ "${KEEP}" =~ ^[0-9]+$ ]] && [[ "${KEEP}" -gt 0 ]] && [[ -d "${ROOT}/backups" ]]; then
  echo "[backup] Ротация: удаляю каталоги pre-deploy-* старше ${KEEP} дней в ${ROOT}/backups ..."
  find "${ROOT}/backups" -maxdepth 1 -type d -name 'pre-deploy-*' -mtime "+${KEEP}" -exec rm -rf {} +
fi

echo "[backup] Готово."
