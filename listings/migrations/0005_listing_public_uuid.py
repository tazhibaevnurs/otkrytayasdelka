import uuid

from django.db import migrations, models


def fill_uuids(apps, schema_editor):
    Listing = apps.get_model('listings', 'Listing')
    for row in Listing.objects.all():
        row.public_uuid = uuid.uuid4()
        row.save(update_fields=['public_uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0004_listing_is_land_plot_listing_property_category_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='public_uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(fill_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='listing',
            name='public_uuid',
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name='Публичный идентификатор',
            ),
        ),
    ]
