#!/usr/bin/env bash
# Сторож: при 504/таймауте перезапускает контейнер web.
#
# Ручной запуск:
#   chmod +x deploy/restart-on-504.sh
#   ./deploy/restart-on-504.sh
#
# Автозапуск (каждую минуту, на сервере):
#   crontab -e
#   * * * * * cd /opt/otkrytayasdelka && ./deploy/restart-on-504.sh >> /var/log/otkrytayasdelka-watchdog.log 2>&1

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f docker-compose.yml ]]; then
  echo "[watchdog] docker-compose.yml not found in $ROOT" >&2
  exit 1
fi

SITE_URL="${SITE_URL:-https://otkrytayasdelka.kg/healthz}"
CONNECT_TIMEOUT="${CONNECT_TIMEOUT:-5}"
MAX_TIME="${MAX_TIME:-15}"
# Не чаще одного рестарта за N секунд (чтобы cron не крутил restart каждую минуту)
COOLDOWN_SEC="${COOLDOWN_SEC:-300}"
COOLDOWN_FILE="${COOLDOWN_FILE:-/tmp/otkrytayasdelka-watchdog-restart.ts}"

log() { echo "[watchdog] $(date -Is) $*"; }

RESPONSE="$(curl -sS -L -o /dev/null -w '%{http_code} %{time_total}' \
  --connect-timeout "$CONNECT_TIMEOUT" --max-time "$MAX_TIME" "$SITE_URL" 2>/dev/null || true)"
HTTP_CODE="${RESPONSE%% *}"
ELAPSED="${RESPONSE#* }"

is_bad=0
if [[ -z "$HTTP_CODE" || "$HTTP_CODE" == "000" || "$HTTP_CODE" == "502" || "$HTTP_CODE" == "503" || "$HTTP_CODE" == "504" ]]; then
  is_bad=1
fi

if [[ "$is_bad" -eq 0 ]]; then
  log "OK code=$HTTP_CODE t=${ELAPSED}s url=$SITE_URL"
  exit 0
fi

log "BAD code=${HTTP_CODE:-n/a} t=${ELAPSED:-n/a}s url=$SITE_URL"

now_ts="$(date +%s)"
if [[ -f "$COOLDOWN_FILE" ]]; then
  last_ts="$(cat "$COOLDOWN_FILE" 2>/dev/null || echo 0)"
  if [[ "$((now_ts - last_ts))" -lt "$COOLDOWN_SEC" ]]; then
    log "skip restart (cooldown ${COOLDOWN_SEC}s, last restart $(date -d "@$last_ts" -Is 2>/dev/null || echo "$last_ts"))"
    exit 0
  fi
fi

log "restarting web..."
docker compose restart web
echo "$now_ts" >"$COOLDOWN_FILE"
sleep 4
docker compose ps web
