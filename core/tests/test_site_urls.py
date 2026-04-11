"""
Автопроверка маршрутов: reverse() без ошибок и ожидаемые HTTP-коды для публичных страниц.
"""
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from listings.models import Listing

# Тестовый клиент Django по умолчанию шлёт Host: testserver — должен быть в ALLOWED_HOSTS.
ALLOWED_HOSTS_TEST = ['testserver', 'localhost', '127.0.0.1']


@override_settings(ALLOWED_HOSTS=ALLOWED_HOSTS_TEST)
class NamedUrlsResolveTests(TestCase):
    """Все именованные URL из шаблонов и конфига должны собираться через reverse()."""

    def test_core_and_catalog_names_resolve(self):
        for name in (
            'home',
            'about',
            'team',
            'services',
            'purchase',
            'sale',
            'contacts',
            'privacy',
            'listing_list',
            'brand_logo_svg',
        ):
            with self.subTest(name=name):
                reverse(name)

    def test_listing_detail_resolves_with_uuid(self):
        listing = Listing.objects.create(
            title='Тестовый объект',
            address='Бишкек',
            listing_type=Listing.TYPE_SALE,
            is_published=True,
        )
        url = reverse('listing_detail', kwargs={'public_uuid': listing.public_uuid})
        self.assertIn(str(listing.public_uuid), url)

    def test_listing_detail_legacy_resolves(self):
        reverse('listing_detail_legacy', kwargs={'pk': 1})

    def test_accounts_auth_names_resolve(self):
        for name in (
            'login',
            'logout',
            'password_reset',
            'password_reset_done',
            'password_reset_complete',
        ):
            with self.subTest(name=name):
                reverse(name)
        reverse('password_reset_confirm', kwargs={'uidb64': 'MQ', 'token': 'set-password'})
        reverse('verify_email', kwargs={'uidb64': 'MQ', 'token': 'verify-token'})
        reverse('register')

    def test_seo_and_misc_names_resolve(self):
        reverse('django.contrib.sitemaps.views.sitemap')

    def test_api_names_resolve(self):
        reverse('api_ai_generate')


@override_settings(ALLOWED_HOSTS=ALLOWED_HOSTS_TEST)
class PublicPagesSmokeTests(TestCase):
    """GET публичных страниц — 200 (или допустимый редирект)."""

    def setUp(self):
        self.client = Client()

    def test_brand_logo_svg_returns_svg(self):
        r = self.client.get(reverse('brand_logo_svg'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('svg', (r.get('Content-Type') or '').lower())
        self.assertIn(b'<svg', r.content[:500])

    def test_static_pages_return_200(self):
        for path in (
            '/',
            '/about/',
            '/team/',
            '/services/',
            '/services/purchase/',
            '/services/sale/',
            '/contacts/',
            '/privacy/',
            '/catalog/',
            '/robots.txt',
            '/sitemap.xml',
            '/google4de3c8fff92579c4.html',
            '/accounts/login/',
            '/accounts/password-reset/',
            '/accounts/password-reset/done/',
            '/accounts/password-reset/complete/',
        ):
            with self.subTest(path=path):
                r = self.client.get(path)
                self.assertEqual(r.status_code, 200, msg=path)

    def test_registration_closed_returns_404(self):
        r = self.client.get('/accounts/register/')
        self.assertEqual(r.status_code, 404)

    @override_settings(REGISTRATION_OPEN=True)
    def test_registration_open_returns_200(self):
        r = self.client.get('/accounts/register/')
        self.assertEqual(r.status_code, 200)

    def test_profile_requires_login(self):
        r = self.client.get('/accounts/profile/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r.headers.get('Location', ''))

    def test_logout_get_not_allowed(self):
        r = self.client.get('/accounts/logout/')
        self.assertEqual(r.status_code, 405)

    def test_listing_detail_200(self):
        listing = Listing.objects.create(
            title='Квартира',
            address='ул. Тест',
            listing_type=Listing.TYPE_SALE,
            is_published=True,
        )
        r = self.client.get(
            reverse('listing_detail', kwargs={'public_uuid': listing.public_uuid})
        )
        self.assertEqual(r.status_code, 200)

    def test_listing_detail_unpublished_404(self):
        listing = Listing.objects.create(
            title='Скрытый',
            address='—',
            listing_type=Listing.TYPE_SALE,
            is_published=False,
        )
        r = self.client.get(
            reverse('listing_detail', kwargs={'public_uuid': listing.public_uuid})
        )
        self.assertEqual(r.status_code, 404)

    def test_legacy_catalog_redirects(self):
        listing = Listing.objects.create(
            title='Легаси',
            address='—',
            listing_type=Listing.TYPE_SALE,
            is_published=True,
        )
        r = self.client.get(
            reverse('listing_detail_legacy', kwargs={'pk': listing.pk}),
            follow=False,
        )
        self.assertEqual(r.status_code, 301)
        self.assertIn(str(listing.public_uuid), r.headers.get('Location', ''))

    def test_api_listings_list_json(self):
        r = self.client.get('/api/listings/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('application/json', r.headers.get('Content-Type', ''))

    def test_api_ai_generate_requires_post(self):
        r = self.client.get('/api/ai/generate/')
        self.assertEqual(r.status_code, 405)

    def test_contacts_post_redirects_success(self):
        r = self.client.post(
            '/contacts/',
            {
                'name': 'Тест',
                'phone': '+996555123456',
                'message': 'Сообщение из автотеста',
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn('/contacts/', r.headers.get('Location', ''))
