"""
Scheduler V2 URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PlanViewSet, PlanTaskViewSet, PlanExecutionViewSet,
    TaskTemplateViewSet, AdhocTaskViewSet
)

router = DefaultRouter()
router.register(r'plans', PlanViewSet, basename='plan')
router.register(r'plan-tasks', PlanTaskViewSet, basename='plan-task')
router.register(r'executions', PlanExecutionViewSet, basename='execution')
router.register(r'templates', TaskTemplateViewSet, basename='template')
router.register(r'adhoc', AdhocTaskViewSet, basename='adhoc')

urlpatterns = [
    path('', include(router.urls)),
]
