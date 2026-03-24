from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from listings.views import listing_list, listing_detail
from core.sitemaps import StaticPagesSitemap, ListingSitemap

sitemaps = {
    'static': StaticPagesSitemap,
    'listings': ListingSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('catalog/<int:pk>/', listing_detail, name='listing_detail'),
    path('catalog/', listing_list, name='listing_list'),
    path('api/', include('listings.urls')),

    # SEO
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('google4de3c8fff92579c4.html', TemplateView.as_view(template_name='google4de3c8fff92579c4.html', content_type='text/html')),

    path('', include('core.urls')),
]

# Раздача медиа (загрузки из админки).
# НЕ используем django.conf.urls.static.static() — в Django 5 при DEBUG=False
# он НЕ регистрирует URL-паттерн и Django возвращает 404 на /media/...
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
