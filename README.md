# Открытая Сделка

Сайт агентства недвижимости на **Django** (Python). Шаблоны, статика и приложения в одном проекте.

## Структура проекта

```
Otkrytaya-sdelka/
├── .venv/           # виртуальное окружение (создать: python -m venv .venv)
├── config/          # настройки Django
├── core/            # приложение: главная, контакты, услуги, о нас
├── listings/        # приложение: каталог объявлений
├── templates/       # общие шаблоны (base.html, includes)
├── static/          # CSS, изображения
├── media/           # загружаемые файлы (создаётся при запуске)
├── manage.py
├── requirements.txt
└── db.sqlite3       # БД (создаётся после migrate)
```

## Запуск

```bash
# из корня проекта
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Откройте в браузере: **http://127.0.0.1:8000/**

Админка: **http://127.0.0.1:8000/admin/** (создайте суперпользователя: `python manage.py createsuperuser`).

## Telegram-бот загрузки объектов

Сотрудники добавляют, редактируют и удаляют объекты каталога через Telegram (приложение `tgbot`).

1. Создайте бота у [@BotFather](https://t.me/BotFather) и пропишите `TELEGRAM_BOT_TOKEN` и `SITE_URL` в `.env`.
2. Запуск: `python manage.py run_telegram_bot` (в Docker — сервис `bot`, поднимается вместе с `docker compose up -d`).
3. Доступ: сотрудник пишет боту `/start` и получает свой Telegram ID → администратор добавляет его в
   админке «Telegram-бот → Сотрудники». Флаг «Может управлять всеми объектами» — для руководителя.
4. Курс доллара для показа цены в сомах: админка «Каталог → Курс доллара».
5. Кто и когда менял объекты: админка «Telegram-бот → Журнал изменений объектов».

Деплой в Docker и бэкапы перед выкладкой: **[deploy/README.md](deploy/README.md)**.
