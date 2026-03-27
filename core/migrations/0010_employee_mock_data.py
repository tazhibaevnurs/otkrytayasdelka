# Мок-сотрудники для страницы «Команда»

from django.db import migrations


def create_mock_employees(apps, schema_editor):
    Employee = apps.get_model('core', 'Employee')
    if Employee.objects.exists():
        return

    mock = [
        {
            'full_name': 'Токтогулов Азамат',
            'position': 'Руководитель отдела продаж',
            'photo_url': 'https://images.unsplash.com/photo-1560250097-0b93528c311a?w=600&q=80',
            'bio': 'Более 10 лет на рынке недвижимости Бишкека. Сопровождает сделки от оценки объекта до регистрации.',
            'order': 0,
            'is_active': True,
        },
        {
            'full_name': 'Садыкова Юлия',
            'position': 'Старший риэлтор',
            'photo_url': 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600&q=80',
            'bio': 'Подбор объектов под запрос клиента, переговоры и организация показов. Специализация — жилая недвижимость.',
            'order': 1,
            'is_active': True,
        },
        {
            'full_name': 'Мамытова Алина',
            'position': 'Риэлтор',
            'photo_url': 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=600&q=80',
            'bio': 'Работа с новостройками и вторичным жильём. Помогает быстро найти вариант в нужном районе и бюджете.',
            'order': 2,
            'is_active': True,
        },
        {
            'full_name': 'Аскаров Эльдар',
            'position': 'Юрист по недвижимости',
            'photo_url': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=600&q=80',
            'bio': 'Проверка документов, сопровождение договоров купли-продажи и консультации по рискам сделки.',
            'order': 3,
            'is_active': True,
        },
        {
            'full_name': 'Касымова Гульнара',
            'position': 'Маркетинг и реклама объектов',
            'photo_url': 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=600&q=80',
            'bio': 'Фото- и видеосъёмка объектов, размещение в каталогах и соцсетях для быстрой продажи.',
            'order': 4,
            'is_active': True,
        },
    ]

    for row in mock:
        Employee.objects.create(**row)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0009_employee'),
    ]

    operations = [
        migrations.RunPython(create_mock_employees, noop),
    ]
