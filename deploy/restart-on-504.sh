#!/usr/bin/env bash
# Auto-restart web container when upstream returns 504/timeout.
#
# Usage:
#   chmod +x deploy/restart-on-504.sh
#   ./deploy/restart-on-504.sh
#
# Recommended cron (every minute):
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
RESPONSE="$(curl -sS -L -o /dev/null -w '%{http_code} %{time_total}' --connect-timeout "$CONNECT_TIMEOUT" --max-time "$MAX_TIME" "$SITE_URL" || true)"
HTTP_CODE="${RESPONSE%% *}"
ELAPSED="${RESPONSE#* }"

is_bad=0
if [[ -z "$HTTP_CODE" ]]; then
  is_bad=1
fi
if [[ "$HTTP_CODE" == "000" || "$HTTP_CODE" == "502" || "$HTTP_CODE" == "503" || "$HTTP_CODE" == "504" ]]; then
  is_bad=1
fi

if [[ "$is_bad" -eq 1 ]]; then
  echo "[watchdog] $(date -Is) bad response from $SITE_URL: code=${HTTP_CODE:-n/a}, t=${ELAPSED:-n/a}s; restarting web..."
  docker compose restart web
  sleep 4
  docker compose ps web
  exit 0
fi

echo "[watchdog] $(date -Is) OK code=$HTTP_CODE t=${ELAPSED}s url=$SITE_URL"
