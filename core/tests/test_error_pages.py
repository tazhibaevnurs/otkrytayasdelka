from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from listings.models import CurrencyRate, Listing

ALLOWED_HOSTS_TEST = ['testserver', 'localhost', '127.0.0.1']


@override_settings(ALLOWED_HOSTS=ALLOWED_HOSTS_TEST)
class NotFoundPageTests(TestCase):
    def test_unknown_url_renders_branded_404(self):
        r = self.client.get('/no-such-page/')
        self.assertEqual(r.status_code, 404)
        self.assertTemplateUsed(r, '404.html')
        self.assertContains(r, 'Страница не найдена', status_code=404)
        self.assertContains(r, 'name="q"', status_code=404)
        self.assertContains(r, 'noindex', status_code=404)


@override_settings(ALLOWED_HOSTS=ALLOWED_HOSTS_TEST)
class PriceInSomTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_detail_shows_som_by_admin_rate(self):
        CurrencyRate.objects.all().delete()
        CurrencyRate.objects.create(usd_to_kgs='87.5')
        listing = Listing.objects.create(title='Квартира', address='мкр. Асанбай', price='91 000 $', price_usd=91000)
        r = self.client.get(reverse('listing_detail', kwargs={'public_uuid': listing.public_uuid}))
        self.assertContains(r, '91 000 $')
        self.assertContains(r, '7 962 500 сом')

    def test_no_som_without_rate(self):
        CurrencyRate.objects.all().delete()
        listing = Listing.objects.create(title='Квартира', address='—', price='91 000 $', price_usd=91000)
        r = self.client.get(reverse('listing_detail', kwargs={'public_uuid': listing.public_uuid}))
        self.assertNotContains(r, 'сом</p>')

    def test_rate_change_invalidates_cache(self):
        rate = CurrencyRate.objects.first() or CurrencyRate.objects.create(usd_to_kgs='87.5')
        listing = Listing.objects.create(title='Квартира', address='—', price='1 000 $', price_usd=1000)
        url = reverse('listing_detail', kwargs={'public_uuid': listing.public_uuid})
        self.client.get(url)
        rate.usd_to_kgs = '90'
        rate.save()
        self.assertContains(self.client.get(url), '90 000 сом')


@override_settings(ALLOWED_HOSTS=ALLOWED_HOSTS_TEST)
class CatalogOrderingTests(TestCase):
    def test_recently_published_listing_goes_first(self):
        now = timezone.now()
        old = Listing.objects.create(title='Старый, но обновлён', address='—', published_at=now)
        Listing.objects.create(title='Новый', address='—', published_at=now - timedelta(days=1))
        r = self.client.get('/catalog/')
        self.assertEqual(r.context['listings'][0].pk, old.pk)
