from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AssetViewSet, AssetTypeViewSet, AssetFieldViewSet,
    AssetTransferViewSet, AssetRepairViewSet, AssetScrapViewSet, AssetLendViewSet
)

router = DefaultRouter()
router.register(r'assets', AssetViewSet, basename='asset')
router.register(r'types', AssetTypeViewSet, basename='asset-type')
router.register(r'fields', AssetFieldViewSet, basename='asset-field')
router.register(r'transfers', AssetTransferViewSet, basename='asset-transfer')
router.register(r'repairs', AssetRepairViewSet, basename='asset-repair')
router.register(r'scraps', AssetScrapViewSet, basename='asset-scrap')
router.register(r'lends', AssetLendViewSet, basename='asset-lend')

urlpatterns = [
    path('', include(router.urls)),
]
