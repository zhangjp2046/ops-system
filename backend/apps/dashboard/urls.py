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
    PushRetryView,
    PushReportView,
)
from .knowledge_views import receive_knowledge_pack, trigger_knowledge_sync, check_knowledge_status

urlpatterns = [
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('monitoring/', MonitoringStatsView.as_view(), name='monitoring-stats'),
    path('alerts/', AlertStatsView.as_view(), name='alert-stats'),
    path('inspection/', InspectionStatsView.as_view(), name='inspection-stats'),
    path('tasks/', TaskStatsView.as_view(), name='task-stats'),
    path('health/', AssetHealthView.as_view(), name='asset-health'),
    path('push-retry/', PushRetryView.as_view(), name='push-retry'),
    # 知识包接收（来自 ops-center）
    path('receive-pack/', receive_knowledge_pack, name='receive-knowledge-pack'),
    path('trigger-sync/', trigger_knowledge_sync, name='trigger-knowledge-sync'),
    # 知识包状态查询（供前端仪表盘）
    path('knowledge-status/', check_knowledge_status, name='knowledge-status'),
    # 资产报表推送
    path('push-report/', PushReportView.as_view(), name='push-report'),
]
