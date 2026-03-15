from django.core.management.base import BaseCommand
from listings.models import Listing


DEMO_LISTINGS = [
    {
        'title': 'Квартира в центре, 2 комнаты',
        'address': 'г. Бишкек, ул. Примерная, 1',
        'price': 'По запросу',
        'rooms': 2,
        'area': 65,
        'description': 'Уютная двухкомнатная квартира в центре города. Хороший ремонт, мебель и техника. Рядом парк и инфраструктура.',
        'image_url': 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&q=80',
    },
    {
        'title': 'Квартира с ремонтом, 3 комнаты',
        'address': 'г. Бишкек, мкр. Юг-2',
        'price': 'По запросу',
        'rooms': 3,
        'area': 85,
        'description': 'Просторная трёхкомнатная квартира с современным ремонтом. Панорамные окна, балкон.',
        'image_url': 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&q=80',
    },
    {
        'title': 'Квартира в новостройке',
        'address': 'г. Бишкек, ул. Примерная, 5',
        'price': 'По запросу',
        'rooms': 2,
        'area': 58,
        'description': 'Новостройка, сдача под ключ. Чистовая отделка на ваш выбор. Подземный паркинг.',
        'image_url': 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800&q=80',
    },
    {
        'title': 'Пентхаус с панорамным видом',
        'address': 'г. Бишкек',
        'price': 'По запросу',
        'rooms': 4,
        'area': 120,
        'description': 'Элитный пентхаус с панорамным остеклением. Два уровня, терраса, вид на город.',
        'image_url': 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&q=80',
    },
    {
        'title': 'Квартира студия',
        'address': 'г. Бишкек, центр',
        'price': 'По запросу',
        'rooms': 1,
        'area': 38,
        'description': 'Студия в центре, идеально для одного человека или пары. Вся необходимая мебель.',
        'image_url': 'https://images.unsplash.com/photo-1493809842364-78817add7ffb?w=800&q=80',
    },
    {
        'title': 'Семейная квартира, 3 комнаты',
        'address': 'г. Бишкек, мкр. Восток',
        'price': 'По запросу',
        'rooms': 3,
        'area': 92,
        'description': 'Семейная квартира в спокойном районе. Детская и гостиная раздельные. Рядом школа и садик.',
        'image_url': 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80',
    },
]


class Command(BaseCommand):
    help = 'Создаёт демо-объекты в каталоге, если он пуст'

    def handle(self, *args, **options):
        if Listing.objects.exists():
            self.stdout.write('Каталог уже содержит объекты. Пропуск.')
            return
        for data in DEMO_LISTINGS:
            Listing.objects.create(**data)
        self.stdout.write(self.style.SUCCESS(f'Создано {len(DEMO_LISTINGS)} демо-объектов.'))
