from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from django.db.models import Q, Count, Case, When, IntegerField
from django.db.models.functions import Coalesce

from .models import Asset, AssetType, AssetField, AssetData
from .serializers import (
    AssetSerializer, AssetCreateSerializer, AssetUpdateSerializer,
    AssetImportSerializer, AssetTypeSerializer, AssetFieldSerializer,
    AssetDataSerializer
)
from apps.customers.models import Customer


class AssetFilter(django_filters.FilterSet):
    """资产过滤器"""
    
    asset_code = django_filters.CharFilter(lookup_expr='icontains')
    asset_name = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.CharFilter(lookup_expr='exact')
    importance_level = django_filters.CharFilter(lookup_expr='exact')
    customer = django_filters.NumberFilter(field_name='customer__id')
    asset_type = django_filters.NumberFilter(field_name='asset_type__id')
    location = django_filters.CharFilter(lookup_expr='icontains')
    owner = django_filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = Asset
        fields = [
            'asset_code', 'asset_name', 'status', 'importance_level',
            'customer', 'asset_type', 'location', 'owner'
        ]


class AssetViewSet(viewsets.ModelViewSet):
    """资产视图集"""
    
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_class = AssetFilter
    search_fields = ['asset_code', 'asset_name', 'description']
    ordering_fields = ['asset_code', 'asset_name', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'create':
            return AssetCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AssetUpdateSerializer
        elif self.action == 'import':
            return AssetImportSerializer
        return super().get_serializer_class()
    
    def get_queryset(self):
        """获取查询集"""
        queryset = super().get_queryset()
        
        # 权限过滤：普通用户只能看到自己负责的资产
        user = self.request.user
        if user.is_authenticated and not user.is_superuser:
            # 这里可以根据实际需求调整权限逻辑
            queryset = queryset.filter(
                Q(owner=user.username) | 
                Q(department=getattr(user, 'full_name', '')) |
                Q(created_by=user)
            ).distinct()
        
        return queryset
    
    def perform_create(self, serializer):
        """创建资产"""
        serializer.save()
    
    def perform_update(self, serializer):
        """更新资产"""
        serializer.save()
    
    @action(detail=False, methods=['post'], url_path='import')
    def import_assets(self, request):
        """批量导入资产"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = serializer.save()
        
        return Response(result, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """资产统计"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # 按状态统计
        status_stats = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # 按重要等级统计
        importance_stats = queryset.values('importance_level').annotate(
            count=Count('id')
        ).order_by('importance_level')
        
        # 按资产类型统计
        type_stats = queryset.values(
            'asset_type__type_name', 'asset_type__type_code'
        ).annotate(
            count=Count('id')
        ).order_by('asset_type__type_name')
        
        # 按客户统计
        customer_stats = queryset.values(
            'customer__customer_name', 'customer__customer_code'
        ).annotate(
            count=Count('id')
        ).order_by('customer__customer_name')
        
        # 最近创建的资产
        recent_assets = queryset.order_by('-created_at')[:10]
        
        return Response({
            'total_count': queryset.count(),
            'status_stats': list(status_stats),
            'importance_stats': list(importance_stats),
            'type_stats': list(type_stats),
            'customer_stats': list(customer_stats),
            'recent_assets': AssetSerializer(recent_assets, many=True).data
        })
    
    @action(detail=True, methods=['get'], url_path='field-data')
    def field_data(self, request, pk=None):
        """获取资产字段数据"""
        asset = self.get_object()
        field_data = AssetData.objects.filter(asset=asset)
        serializer = AssetDataSerializer(field_data, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='update-field')
    def update_field(self, request, pk=None):
        """更新资产字段数据"""
        asset = self.get_object()
        field_code = request.data.get('field_code')
        value = request.data.get('value')
        
        if not field_code or value is None:
            return Response(
                {'error': '必须提供 field_code 和 value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            field = asset.asset_type.fields.get(field_code=field_code)
            asset_data, created = AssetData.objects.get_or_create(
                asset=asset,
                field=field,
                defaults={'string_value': str(value)}
            )
            if not created:
                asset_data.set_value(value)
                asset_data.save()
            
            return Response({'message': '字段更新成功'})
            
        except AssetField.DoesNotExist:
            return Response(
                {'error': f'字段 {field_code} 不存在'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """激活资产"""
        asset = self.get_object()
        asset.status = 'ACTIVE'
        asset.save()
        return Response({'message': '资产已激活'})
    
    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        """停用资产"""
        asset = self.get_object()
        asset.status = 'INACTIVE'
        asset.save()
        return Response({'message': '资产已停用'})
    
    @action(detail=True, methods=['post'], url_path='maintenance')
    def maintenance(self, request, pk=None):
        """设置资产为维护状态"""
        asset = self.get_object()
        asset.status = 'MAINTENANCE'
        asset.save()
        return Response({'message': '资产已设置为维护状态'})
    
    @action(detail=True, methods=['post'], url_path='decommission')
    def decommission(self, request, pk=None):
        """退役资产"""
        asset = self.get_object()
        asset.status = 'DECOMMISSIONED'
        asset.decommission_date = request.data.get('decommission_date')
        asset.save()
        return Response({'message': '资产已退役'})


class AssetTypeViewSet(viewsets.ModelViewSet):
    """资产类型视图集"""
    
    queryset = AssetType.objects.all()
    serializer_class = AssetTypeSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ['customer', 'is_system', 'is_active']
    
    def get_queryset(self):
        """获取查询集"""
        queryset = super().get_queryset()
        
        # 按客户过滤
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        return queryset
    
    @action(detail=True, methods=['get'], url_path='fields')
    def fields(self, request, pk=None):
        """获取资产类型的字段"""
        asset_type = self.get_object()
        fields = asset_type.fields.all()
        serializer = AssetFieldSerializer(fields, many=True)
        return Response(serializer.data)


class AssetFieldViewSet(viewsets.ModelViewSet):
    """资产字段视图集"""
    
    queryset = AssetField.objects.all()
    serializer_class = AssetFieldSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ['asset_type', 'field_type', 'is_required']