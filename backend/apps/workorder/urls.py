from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkOrderViewSet, WorkOrderStepViewSet

router = DefaultRouter()
router.register(r'', WorkOrderViewSet, basename='workorder')
router.register(r'steps', WorkOrderStepViewSet, basename='workorder-step')

urlpatterns = [
    path('', include(router.urls)),
]
