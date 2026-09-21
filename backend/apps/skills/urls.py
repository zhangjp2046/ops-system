from django.urls import path
from .views import SkillListView, SkillExecuteView, SkillDetailView

urlpatterns = [
    path('', SkillListView.as_view(), name='skill-list'),
    path('execute/', SkillExecuteView.as_view(), name='skill-execute'),
    path('<str:skill_code>/', SkillDetailView.as_view(), name='skill-detail'),
]
