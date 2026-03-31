from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScheduledTaskViewSet, ScheduledTaskExecutionViewSet

router = DefaultRouter()
router.register(r'tasks', ScheduledTaskViewSet, basename='scheduled-task')
router.register(r'executions', ScheduledTaskExecutionViewSet, basename='task-execution')

urlpatterns = [
    path('', include(router.urls)),
]