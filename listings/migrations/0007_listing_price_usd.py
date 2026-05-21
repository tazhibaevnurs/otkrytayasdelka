# Цена USD для фильтра каталога

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0006_listing_image_thumbnail'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='price_usd',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Число в долларах для фильтра в каталоге. Строковое поле «Цена» — подпись на сайте.',
                null=True,
                verbose_name='Цена, USD',
            ),
        ),
    ]
