# Generated manually: создаём по одной записи SectionImage для каждого ключа

from django.db import migrations


def create_placeholders(apps, schema_editor):
    SectionImage = apps.get_model('core', 'SectionImage')
    keys = [
        'home_hero', 'advantage_1', 'advantage_2', 'advantage_3', 'advantage_4', 'advantage_5', 'advantage_6',
        'help_block', 'cta_bg', 'about_image', 'purchase_hero', 'sale_hero',
    ]
    for key in keys:
        SectionImage.objects.get_or_create(key=key)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_section_image_and_review'),
    ]

    operations = [
        migrations.RunPython(create_placeholders, noop),
    ]
