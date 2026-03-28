"""Пересобрать превью каталога для всех объявлений с загруженным image (после внедрения image_thumbnail)."""
from django.core.management.base import BaseCommand

from listings.models import Listing


class Command(BaseCommand):
    help = 'Генерирует image_thumbnail для объявлений с файлом image, где превью ещё пустое или принудительно (--force).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Пересоздать превью даже если файл уже есть',
        )

    def handle(self, *args, **options):
        force = options['force']
        qs = Listing.objects.filter(image__isnull=False).exclude(image='')
        updated = 0
        for listing in qs.iterator():
            if not force and listing.image_thumbnail:
                continue
            if force and listing.image_thumbnail:
                listing.image_thumbnail.delete(save=False)
                Listing.objects.filter(pk=listing.pk).update(image_thumbnail=None)
                listing.image_thumbnail = None
            listing.save()
            updated += 1
            if updated % 50 == 0:
                self.stdout.write(f'… {updated}')
        self.stdout.write(self.style.SUCCESS(f'Готово, обработано сохранений: {updated}'))
