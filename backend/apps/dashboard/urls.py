#!/usr/bin/env python3
"""
驾驶舱URL配置
"""

from django.urls import path
from .views import (
    DashboardStatsView,
    MonitoringStatsView,
    AlertStatsView,
    InspectionStatsView,
    TaskStatsView,
    AssetHealthView,
)

urlpatterns = [
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('monitoring/', MonitoringStatsView.as_view(), name='monitoring-stats'),
    path('alerts/', AlertStatsView.as_view(), name='alert-stats'),
    path('inspection/', InspectionStatsView.as_view(), name='inspection-stats'),
    path('tasks/', TaskStatsView.as_view(), name='task-stats'),
    path('health/', AssetHealthView.as_view(), name='asset-health'),
]
