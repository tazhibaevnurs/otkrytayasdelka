# Деплой Docker и резервное копирование

Развёртывание описано для Linux-сервера (путь приложения может быть например `/opt/otkrytayasdelka`). Рядом с `docker-compose.yml` должны быть `.env`, каталоги `data`, `media`, `staticfiles` после первого запуска.

## Бэкап перед деплоем

Скрипт `backup-before-deploy.sh` создаёт каталог `./backups/pre-deploy-ГГГГММДД-ЧЧММСС` с:

- **`django.dumpdata.json.gz`** — дамп данных Django (`manage.py dumpdata`), подходит для PostgreSQL и SQLite.
- **`postgres.sql.gz`** — если в `.env` задан **`DATABASE_URL`** вида `postgres://…` или `postgresql://…` (через `pg_dump`).
- **`db.sqlite3`** — копия файла с хоста `./data/db.sqlite3`, если БД без Postgres URL в `.env`.

Опционально:

- **`BACKUP_MEDIA=1`** — добавить архив `./media` в **`media.tgz`** (может занять много места).
- **`BACKUP_KEEP_DAYS=14`** — удалять старые каталоги `pre-deploy-*` (`0` — не удалять автоматически).

Пример перед ручным `docker compose up`:

```bash
chmod +x deploy/backup-before-deploy.sh deploy/deploy-with-backup.sh
./deploy/backup-before-deploy.sh
docker compose build && docker compose up -d
```

Или один шаг (бэкап → build → `up -d`):

```bash
./deploy/deploy-with-backup.sh
```

Каталог `backups/` в git не коммитится (см. `.gitignore`).

### Формат `.env`

Каждая строка должна быть вида **`ИМЯ=значение`**. Не оставляйте «голое» значение на отдельной строке (например только `localhost,127.0.0.1,yourdomain.com`) — это ломало бы выполнение `source .env` в shell. Скрипт бэкапа **не** делает `source` всего файла и только читает строку **`DATABASE_URL=`**, но приведите файл в порядок: например **`DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com`** в одну строку (при необходимости заключите значение в кавычки).

### Важно про SQLite и консистентность

При живом контейнере `web` копирование `./data/db.sqlite3` может теоретически попасть в середину записи; для дополнительной надёжности используйте `django.dumpdata.json.gz`. Перед деплоем можно кратко остановить веб (`docker compose stop web`), сделать бэкап, затем `build`/`up`.

## Nginx и статика

См. конфиг-пример и подсказки в этом каталоге: `nginx-otkrytayasdelka.conf`, `nginx-patch-media.txt`.
