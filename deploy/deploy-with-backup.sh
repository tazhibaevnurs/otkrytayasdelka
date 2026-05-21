#!/usr/bin/env bash
# Сбор образа и деплой с предварительным бэкапом (Linux / сервер VPS).
#
# Использование на сервере из каталога с репозиторием (рядом с docker-compose.yml):
#   chmod +x deploy/deploy-with-backup.sh
#   ./deploy/deploy-with-backup.sh
#
# Доп. аргументы передаются в docker compose после build (напр. профиль или override):
#   ./deploy/deploy-with-backup.sh --progress plain
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/backup-before-deploy.sh"
docker compose build "$@"
docker compose up -d "$@"
