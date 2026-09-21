from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MaterialCategoryViewSet, MaterialViewSet,
    DeptStockViewSet, DeptStockRecordViewSet,
    MaterialOrderViewSet, ConsumptionRecordViewSet,
    StockAlertViewSet,
)

router = DefaultRouter()
router.register(r'categories', MaterialCategoryViewSet)
router.register(r'materials', MaterialViewSet)
router.register(r'dept-stocks', DeptStockViewSet)
router.register(r'stock-records', DeptStockRecordViewSet)
router.register(r'orders', MaterialOrderViewSet)
router.register(r'consumptions', ConsumptionRecordViewSet)
router.register(r'alerts', StockAlertViewSet)

urlpatterns = [
    path('', include(router.urls)),
]