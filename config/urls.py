from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from listings.views import listing_list, listing_detail

urlpatterns = [
    path('admin/', admin.site.urls),
    path('catalog/<int:pk>/', listing_detail, name='listing_detail'),
    path('catalog/', listing_list, name='listing_list'),
    path('api/', include('listings.urls')),
    path('', include('core.urls')),
]

# Раздача медиа (загрузки из админки).
# НЕ используем django.conf.urls.static.static() — в Django 5 при DEBUG=False
# он НЕ регистрирует URL-паттерн и Django возвращает 404 на /media/...
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
