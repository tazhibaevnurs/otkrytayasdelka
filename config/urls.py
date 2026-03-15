from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from listings.views import listing_list, listing_detail

urlpatterns = [
    path('admin/', admin.site.urls),
    path('catalog/<int:pk>/', listing_detail, name='listing_detail'),
    path('catalog/', listing_list, name='listing_list'),
    path('api/', include('listings.urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
