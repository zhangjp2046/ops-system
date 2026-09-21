from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InspectionPlanViewSet, InspectionTaskViewSet, InspectionViewSet

router = DefaultRouter()
router.register(r'plans', InspectionPlanViewSet)
router.register(r'tasks', InspectionTaskViewSet)
router.register(r'inspections', InspectionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
