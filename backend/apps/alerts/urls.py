from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AlertViewSet, AlertRuleViewSet, AlertSubscriptionViewSet,
    receive_alert, get_customer_api_info
)

router = DefaultRouter()
router.register(r'alerts', AlertViewSet)
router.register(r'rules', AlertRuleViewSet)
router.register(r'subscriptions', AlertSubscriptionViewSet)

urlpatterns = [
    path('receive/', receive_alert, name='receive-alert'),
    path('api-info/', get_customer_api_info, name='get-api-info'),
    path('', include(router.urls)),
]
