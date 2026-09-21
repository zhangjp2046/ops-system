from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DiscoveryTaskViewSet, DiscoveredDeviceViewSet, TopologyViewSet

router = DefaultRouter()
router.register(r'tasks', DiscoveryTaskViewSet, basename='discovery-task')
router.register(r'devices', DiscoveredDeviceViewSet, basename='discovery-device')
router.register(r'topology', TopologyViewSet, basename='topology')

urlpatterns = [
    path('', include(router.urls)),
]
