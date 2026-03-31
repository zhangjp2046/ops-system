from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InspectionPlanViewSet, InspectionTaskViewSet, InspectionRecordViewSet

router = DefaultRouter()
router.register(r'plans', InspectionPlanViewSet)
router.register(r'tasks', InspectionTaskViewSet)
router.register(r'records', InspectionRecordViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
