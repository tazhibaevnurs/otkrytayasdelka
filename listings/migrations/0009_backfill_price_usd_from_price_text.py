# Заполняем price_usd из текстового поля price (иначе фильтр по цене на продакшене возвращает 0 объектов).

from django.db import migrations


def forwards(apps, schema_editor):
    from listings.price_infer import infer_price_usd_from_charfield

    Listing = apps.get_model('listings', 'Listing')
    batch = []
    for row in Listing.objects.filter(price_usd__isnull=True).iterator():
        inferred = infer_price_usd_from_charfield(row.price)
        if inferred is None:
            continue
        row.price_usd = inferred
        batch.append(row)
        if len(batch) >= 400:
            Listing.objects.bulk_update(batch, ['price_usd'])
            batch.clear()
    if batch:
        Listing.objects.bulk_update(batch, ['price_usd'])


def noop_backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('listings', '0008_catalog_demo_listings'),
    ]

    operations = [
        migrations.RunPython(forwards, noop_backwards),
    ]
