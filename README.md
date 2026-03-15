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
