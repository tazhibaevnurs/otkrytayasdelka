from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'listings', views.ListingViewSet, basename='listing')

urlpatterns = [
    path('ai/generate/', views.ai_generate_stub, name='api_ai_generate'),
    path('', include(router.urls)),
]
