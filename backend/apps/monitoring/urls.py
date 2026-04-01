from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MonitoringTaskViewSet, MonitoringResultViewSet,
    AlertRuleViewSet, AlertViewSet
)
from .test_views import MonitorTestConfigViewSet, MonitorTestResultViewSet, quick_test

router = DefaultRouter()
router.register(r'tasks', MonitoringTaskViewSet, basename='monitoring-task')
router.register(r'results', MonitoringResultViewSet, basename='monitoring-result')
router.register(r'rules', AlertRuleViewSet, basename='alert-rule')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'test-configs', MonitorTestConfigViewSet, basename='test-config')
router.register(r'test-results', MonitorTestResultViewSet, basename='test-result')

urlpatterns = [
    path('quick-test/', quick_test, name='quick-test'),
    path('', include(router.urls)),
]