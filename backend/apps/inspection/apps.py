#!/usr/bin/env python3
"""
巡检记录应用配置
"""

from django.apps import AppConfig


class InspectionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inspection'
    verbose_name = '巡检管理'
