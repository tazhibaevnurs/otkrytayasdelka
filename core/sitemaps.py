from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from listings.models import Listing


class StaticPagesSitemap(Sitemap):
    """Карта статических страниц сайта."""
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return [
            'home',
            'about',
            'purchase',
            'sale',
            'contacts',
            'listing_list',
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        priorities = {
            'home': 1.0,
            'listing_list': 0.9,
            'purchase': 0.8,
            'sale': 0.8,
            'about': 0.7,
            'contacts': 0.6,
        }
        return priorities.get(item, 0.5)

    def changefreq(self, item):
        freqs = {
            'home': 'daily',
            'listing_list': 'daily',
            'purchase': 'weekly',
            'sale': 'weekly',
            'about': 'monthly',
            'contacts': 'monthly',
        }
        return freqs.get(item, 'weekly')


class ListingSitemap(Sitemap):
    """Карта страниц объектов недвижимости."""
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Listing.objects.filter(is_published=True).order_by('-updated_at')

    def location(self, obj):
        return reverse('listing_detail', args=[obj.pk])

    def lastmod(self, obj):
        return obj.updated_at
