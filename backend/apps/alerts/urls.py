from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AlertViewSet, AlertRuleViewSet, AlertSubscriptionViewSet,
    receive_alert, get_customer_api_info
)
from .threshold_views import (
    AlertThresholdViewSet, AlertThresholdRuleViewSet, AlertThresholdTemplateViewSet,
    get_default_thresholds
)

router = DefaultRouter()
router.register(r'alerts', AlertViewSet)
router.register(r'rules', AlertRuleViewSet)
router.register(r'subscriptions', AlertSubscriptionViewSet)
router.register(r'thresholds', AlertThresholdViewSet)
router.register(r'threshold-rules', AlertThresholdRuleViewSet)
router.register(r'threshold-templates', AlertThresholdTemplateViewSet)

urlpatterns = [
    path('receive/', receive_alert, name='receive-alert'),
    path('api-info/', get_customer_api_info, name='get-api-info'),
    path('default-thresholds/', get_default_thresholds, name='default-thresholds'),
    path('', include(router.urls)),
]
