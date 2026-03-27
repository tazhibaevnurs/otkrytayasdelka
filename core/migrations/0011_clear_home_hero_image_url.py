# Сброс внешней ссылки hero главной — используется static/img/hero-home.png по умолчанию

from django.db import migrations


def clear_home_hero_url(apps, schema_editor):
    SectionImage = apps.get_model('core', 'SectionImage')
    SectionImage.objects.filter(key='home_hero').update(image_url='')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0010_employee_mock_data'),
    ]

    operations = [
        migrations.RunPython(clear_home_hero_url, noop),
    ]
