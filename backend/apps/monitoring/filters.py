from django_filters import rest_framework as filters
from .models import MonitoringDataPoint


class MonitoringDataPointFilter(filters.FilterSet):
    """监控数据点过滤器"""

    class Meta:
        model = MonitoringDataPoint
        fields = {
            'asset': ['exact'],
            'protocol': ['exact', 'icontains'],
            'check_item_code': ['exact', 'icontains'],
            'severity': ['exact', 'gte', 'lte'],
            'customer': ['exact'],
            'recorded_at': ['gte', 'lte', 'date__gte', 'date__lte'],
        }
