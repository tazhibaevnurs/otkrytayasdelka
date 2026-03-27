from django.db import migrations


def create_pro_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='subscription_pro')


def remove_pro_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='subscription_pro').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_clear_home_hero_image_url'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_pro_group, remove_pro_group),
    ]
