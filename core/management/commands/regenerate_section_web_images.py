"""Пересобрать image_optimized для «Изображения секций» (после миграции или --force)."""
from django.core.management.base import BaseCommand

from core.models import SectionImage


class Command(BaseCommand):
    help = 'Генерирует image_optimized для SectionImage с загруженным image.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Пересоздать веб-копию даже если файл уже есть',
        )

    def handle(self, *args, **options):
        force = options['force']
        qs = SectionImage.objects.filter(image__isnull=False).exclude(image='')
        n = 0
        for obj in qs.iterator():
            if not force and obj.image_optimized:
                continue
            if force and obj.image_optimized:
                obj.image_optimized.delete(save=False)
                SectionImage.objects.filter(pk=obj.pk).update(image_optimized=None)
                obj.image_optimized = None
            obj.save()
            n += 1
        self.stdout.write(self.style.SUCCESS(f'Обработано записей: {n}'))
