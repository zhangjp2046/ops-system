from rest_framework import viewsets, permissions
from django_filters import rest_framework as django_filters
from .models import Customer
from .serializers import CustomerSerializer


class CustomerFilter(django_filters.FilterSet):
    """客户过滤器"""
    
    customer_code = django_filters.CharFilter(lookup_expr='icontains')
    customer_name = django_filters.CharFilter(lookup_expr='icontains')
    industry = django_filters.CharFilter(lookup_expr='exact')
    status = django_filters.CharFilter(lookup_expr='exact')
    
    class Meta:
        model = Customer
        fields = ['customer_code', 'customer_name', 'industry', 'status']


class CustomerViewSet(viewsets.ModelViewSet):
    """客户视图集"""
    
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = CustomerFilter
    search_fields = ['customer_code', 'customer_name']
    ordering_fields = ['customer_code', 'customer_name', 'created_at']
    ordering = ['-created_at']