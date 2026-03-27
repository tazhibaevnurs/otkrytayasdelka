from django.db import migrations


def create_mock_reviews(apps, schema_editor):
    Review = apps.get_model('core', 'Review')
    if Review.objects.filter(author_name__in=['Иванов Иван Иванович', 'Петрова Алина Кубанычевна']).exists():
        return

    mock_reviews = [
        {
            'author_name': 'Иванов Иван Иванович',
            'text': 'Продали квартиру за 18 дней. Риэлтор сопровождал на всех этапах, документы оформили без задержек.',
            'image_url': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600&q=80',
            'order': 10,
            'is_active': True,
        },
        {
            'author_name': 'Петрова Алина Кубанычевна',
            'text': 'Понравился профессиональный подход и прозрачная коммуникация. Сделка прошла спокойно и быстро.',
            'image_url': 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=600&q=80',
            'video_url': 'https://cdn.coverr.co/videos/coverr-mountain-running-1579/1080p.mp4',
            'order': 11,
            'is_active': True,
        },
        {
            'author_name': 'Садыков Бакыт Эмилович',
            'text': '',
            'video_url': 'https://cdn.coverr.co/videos/coverr-happy-customer-1570/1080p.mp4',
            'order': 12,
            'is_active': True,
        },
    ]

    for review in mock_reviews:
        Review.objects.create(**review)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0007_review_image_url_review_video_review_video_url_and_more'),
    ]

    operations = [
        migrations.RunPython(create_mock_reviews, noop),
    ]
