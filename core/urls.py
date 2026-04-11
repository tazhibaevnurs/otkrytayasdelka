from django.urls import path
from . import views

urlpatterns = [
    path('brand/logo', views.brand_logo, name='brand_logo'),
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('team/', views.team, name='team'),
    path('services/', views.services, name='services'),
    path('services/purchase/', views.purchase, name='purchase'),
    path('services/sale/', views.sale, name='sale'),
    path('contacts/', views.contacts, name='contacts'),
    path('privacy/', views.privacy, name='privacy'),
]
