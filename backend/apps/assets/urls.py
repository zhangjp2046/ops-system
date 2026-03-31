from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssetViewSet, AssetTypeViewSet, AssetFieldViewSet

router = DefaultRouter()
router.register(r'assets', AssetViewSet, basename='asset')
router.register(r'types', AssetTypeViewSet, basename='asset-type')
router.register(r'fields', AssetFieldViewSet, basename='asset-field')

urlpatterns = [
    path('', include(router.urls)),
]