from django.contrib import admin
from .models import MonitoringDataPoint, MonitoringTask, MonitoringResult, AlertRule, Alert

admin.site.register(MonitoringDataPoint)
admin.site.register(MonitoringTask)
admin.site.register(MonitoringResult)
admin.site.register(AlertRule)
admin.site.register(Alert)
