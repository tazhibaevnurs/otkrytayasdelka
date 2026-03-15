# Generated manually

from django.db import migrations


def create_default(apps, schema_editor):
    FeaturedMedia = apps.get_model('core', 'FeaturedMedia')
    if not FeaturedMedia.objects.exists():
        FeaturedMedia.objects.create(
            title='Знаем все нюансы продажи и покупки недвижимости и готовы делиться знаниями с вами',
            description='Мы ведём YouTube-канал, на котором даём полезные советы и делаем обзоры недвижимости, чтобы вы могли сделать правильный выбор.',
            media_type='youtube',
            link_label='Подписаться на канал',
            link_url='https://www.youtube.com',
            is_active=True,
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_featured_media'),
    ]

    operations = [
        migrations.RunPython(create_default, noop),
    ]
