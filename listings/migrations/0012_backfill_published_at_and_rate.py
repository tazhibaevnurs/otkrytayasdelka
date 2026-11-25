# Существующим объектам дата публикации = дата создания (порядок каталога не меняется)
# и начальный курс доллара из ТЗ: 91 000 $ = 7 962 500 сом → 87.5. Курс правится в админке.

from decimal import Decimal

from django.db import migrations
from django.db.models import F

INITIAL_USD_KGS_RATE = Decimal('87.5')


def forwards(apps, schema_editor):
    Listing = apps.get_model('listings', 'Listing')
    Listing.objects.update(published_at=F('created_at'))
    CurrencyRate = apps.get_model('listings', 'CurrencyRate')
    if not CurrencyRate.objects.exists():
        CurrencyRate.objects.create(usd_to_kgs=INITIAL_USD_KGS_RATE)


class Migration(migrations.Migration):
    dependencies = [
        ('listings', '0011_listing_telegram_author'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
