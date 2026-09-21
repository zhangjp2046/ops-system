from rest_framework import viewsets, status, permissions, filters, pagination
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from django.db.models import Q, Count, Case, When, IntegerField
from django.db.models.functions import Coalesce


class AssetPageNumberPagination(pagination.PageNumberPagination):
    """支持 page_size 查询参数的分页类"""
    page_size_query_param = 'page_size'
    max_page_size = 1000

from .models import (
    Asset, AssetType, AssetField, AssetData, AssetStatusHistory,
    AssetTransfer, AssetRepair, AssetScrap, AssetLend
)
from .serializers import (
    AssetSerializer, AssetCreateSerializer, AssetUpdateSerializer,
    AssetImportSerializer, AssetTypeSerializer, AssetFieldSerializer,
    AssetDataSerializer,
    AssetTransferSerializer, AssetTransferCreateSerializer,
    AssetRepairSerializer, AssetRepairCreateSerializer,
    AssetScrapSerializer, AssetScrapCreateSerializer,
    AssetLendSerializer, AssetLendCreateSerializer
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
    protocol = django_filters.CharFilter(lookup_expr='exact')
    
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
    pagination_class = AssetPageNumberPagination

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
        
        # 预加载关联数据，避免 N+1 查询
        queryset = queryset.select_related('customer', 'asset_type').prefetch_related(
            'field_values__field'
        )
        
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
import uuid
from datetime import datetime
from django.utils import timezone


def generate_transfer_no():
    """生成调拨单号"""
    date_str = datetime.now().strftime('%Y%m%d')
    unique = str(uuid.uuid4())[:6].upper()
    return f'TR{date_str}{unique}'


def generate_repair_no():
    """生成维修单号"""
    date_str = datetime.now().strftime('%Y%m%d')
    unique = str(uuid.uuid4())[:6].upper()
    return f'RP{date_str}{unique}'


def generate_scrap_no():
    """生成报废单号"""
    date_str = datetime.now().strftime('%Y%m%d')
    unique = str(uuid.uuid4())[:6].upper()
    return f'SC{date_str}{unique}'


def generate_lend_no():
    """生成出借单号"""
    date_str = datetime.now().strftime('%Y%m%d')
    unique = str(uuid.uuid4())[:6].upper()
    return f'LD{date_str}{unique}'


class AssetTransferFilter(django_filters.FilterSet):
    """资产调拨过滤器"""
    transfer_no = django_filters.CharFilter(lookup_expr='icontains')
    asset_name = django_filters.CharFilter(lookup_expr='asset__asset_name__icontains')
    
    class Meta:
        model = AssetTransfer
        fields = ['customer', 'asset', 'status', 'from_department', 'to_department']


class AssetTransferViewSet(viewsets.ModelViewSet):
    """资产调拨视图集"""
    
    queryset = AssetTransfer.objects.all()
    serializer_class = AssetTransferSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AssetTransferFilter
    search_fields = ['transfer_no', 'asset__asset_name', 'applicant']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AssetTransferCreateSerializer
        return AssetTransferSerializer
    
    def perform_create(self, serializer):
        serializer.save(transfer_no=generate_transfer_no())
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """审批通过"""
        transfer = self.get_object()
        if transfer.status != 'PENDING':
            return Response({'error': '当前状态不允许审批'}, status=status.HTTP_400_BAD_REQUEST)
        transfer.status = 'APPROVED'
        transfer.approver = request.user.username
        transfer.approve_time = timezone.now()
        transfer.approve_comment = request.data.get('comment', '')
        transfer.save()
        return Response({'message': '审批通过'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """审批拒绝"""
        transfer = self.get_object()
        if transfer.status != 'PENDING':
            return Response({'error': '当前状态不允许审批'}, status=status.HTTP_400_BAD_REQUEST)
        transfer.status = 'REJECTED'
        transfer.approver = request.user.username
        transfer.approve_time = timezone.now()
        transfer.approve_comment = request.data.get('comment', '')
        transfer.save()
        return Response({'message': '已拒绝'})
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行调拨"""
        transfer = self.get_object()
        if transfer.status != 'APPROVED':
            return Response({'error': '只有已审批的调拨才能执行'}, status=status.HTTP_400_BAD_REQUEST)
        transfer.status = 'COMPLETED'
        transfer.executor = request.user.username
        transfer.execute_time = timezone.now()
        # 更新资产位置
        transfer.asset.department = transfer.to_department
        transfer.asset.location = transfer.to_location
        transfer.asset.save()
        transfer.save()
        return Response({'message': '调拨完成'})


class AssetRepairFilter(django_filters.FilterSet):
    """资产维修过滤器"""
    repair_no = django_filters.CharFilter(lookup_expr='icontains')
    asset_name = django_filters.CharFilter(lookup_expr='asset__asset_name__icontains')
    
    class Meta:
        model = AssetRepair
        fields = ['customer', 'asset', 'status', 'priority']


class AssetRepairViewSet(viewsets.ModelViewSet):
    """资产维修视图集"""
    
    queryset = AssetRepair.objects.all()
    serializer_class = AssetRepairSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AssetRepairFilter
    search_fields = ['repair_no', 'asset__asset_name', 'assignee']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AssetRepairCreateSerializer
        return AssetRepairSerializer
    
    def perform_create(self, serializer):
        serializer.save(repair_no=generate_repair_no())
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """派工"""
        repair = self.get_object()
        if repair.status != 'APPLIED':
            return Response({'error': '当前状态不允许派工'}, status=status.HTTP_400_BAD_REQUEST)
        repair.status = 'ASSIGNED'
        repair.assignee = request.data.get('assignee', '')
        repair.assignee_phone = request.data.get('assignee_phone', '')
        repair.save()
        return Response({'message': '已派工'})
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """接单"""
        repair = self.get_object()
        if repair.status != 'ASSIGNED':
            return Response({'error': '当前状态不允许接单'}, status=status.HTTP_400_BAD_REQUEST)
        repair.status = 'ACCEPTED'
        repair.save()
        return Response({'message': '已接单'})
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """开始维修"""
        repair = self.get_object()
        if repair.status not in ['ACCEPTED', 'ASSIGNED']:
            return Response({'error': '当前状态不允许开始维修'}, status=status.HTTP_400_BAD_REQUEST)
        repair.status = 'PROCESSING'
        repair.save()
        return Response({'message': '维修开始'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """完成维修"""
        repair = self.get_object()
        if repair.status != 'PROCESSING':
            return Response({'error': '当前状态不允许完成维修'}, status=status.HTTP_400_BAD_REQUEST)
        repair.status = 'COMPLETED'
        repair.repair_result = request.data.get('repair_result', '')
        repair.repair_time = timezone.now()
        repair.repair_cost = request.data.get('repair_cost', 0)
        repair.parts_cost = request.data.get('parts_cost', 0)
        repair.total_cost = repair.repair_cost + repair.parts_cost
        repair.save()
        return Response({'message': '维修完成'})
    
    @action(detail=True, methods=['post'], url_path='accept-inspect')
    def accept_inspect(self, request, pk=None):
        """验收"""
        repair = self.get_object()
        if repair.status != 'COMPLETED':
            return Response({'error': '当前状态不允许验收'}, status=status.HTTP_400_BAD_REQUEST)
        repair.status = 'QUALIFIED'
        repair.accept_result = request.data.get('accept_result', '合格')
        repair.accept_comment = request.data.get('accept_comment', '')
        repair.accept_time = timezone.now()
        repair.accept_by = request.user.username
        repair.save()
        return Response({'message': '验收通过'})


class AssetScrapFilter(django_filters.FilterSet):
    """资产报废过滤器"""
    scrap_no = django_filters.CharFilter(lookup_expr='icontains')
    asset_name = django_filters.CharFilter(lookup_expr='asset__asset_name__icontains')
    
    class Meta:
        model = AssetScrap
        fields = ['customer', 'asset', 'status']


class AssetScrapViewSet(viewsets.ModelViewSet):
    """资产报废视图集"""
    
    queryset = AssetScrap.objects.all()
    serializer_class = AssetScrapSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AssetScrapFilter
    search_fields = ['scrap_no', 'asset__asset_name', 'handler']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AssetScrapCreateSerializer
        return AssetScrapSerializer
    
    def perform_create(self, serializer):
        serializer.save(scrap_no=generate_scrap_no())
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """审批"""
        scrap = self.get_object()
        if scrap.status != 'APPLIED':
            return Response({'error': '当前状态不允许审批'}, status=status.HTTP_400_BAD_REQUEST)
        action_type = request.data.get('action', 'approve')
        if action_type == 'approve':
            scrap.status = 'APPROVED'
        else:
            scrap.status = 'REJECTED'
        scrap.approver = request.user.username
        scrap.approve_time = timezone.now()
        scrap.approve_comment = request.data.get('comment', '')
        scrap.save()
        return Response({'message': '审批完成'})
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行报废"""
        scrap = self.get_object()
        if scrap.status != 'APPROVED':
            return Response({'error': '只有已审批的报废才能执行'}, status=status.HTTP_400_BAD_REQUEST)
        scrap.status = 'SCRAPPED'
        scrap.scrap_time = timezone.now()
        scrap.scrap_by = request.user.username
        scrap.disposal_result = request.data.get('disposal_result', '')
        # 更新资产状态
        scrap.asset.status = 'DECOMMISSIONED'
        scrap.asset.decommission_date = timezone.now().date()
        scrap.asset.save()
        scrap.save()
        return Response({'message': '报废完成'})


class AssetLendFilter(django_filters.FilterSet):
    """资产出借过滤器"""
    lend_no = django_filters.CharFilter(lookup_expr='icontains')
    asset_name = django_filters.CharFilter(lookup_expr='asset__asset_name__icontains')
    
    class Meta:
        model = AssetLend
        fields = ['customer', 'asset', 'status', 'from_department', 'to_department']


class AssetLendViewSet(viewsets.ModelViewSet):
    """资产出借视图集"""
    
    queryset = AssetLend.objects.all()
    serializer_class = AssetLendSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AssetLendFilter
    search_fields = ['lend_no', 'asset__asset_name', 'lendee']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AssetLendCreateSerializer
        return AssetLendSerializer
    
    def perform_create(self, serializer):
        serializer.save(lend_no=generate_lend_no())
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """审批"""
        lend = self.get_object()
        if lend.status != 'PENDING':
            return Response({'error': '当前状态不允许审批'}, status=status.HTTP_400_BAD_REQUEST)
        action_type = request.data.get('action', 'approve')
        if action_type == 'approve':
            lend.status = 'APPROVED'
        else:
            lend.status = 'REJECTED'
        lend.approver = request.user.username
        lend.approve_time = timezone.now()
        lend.approve_comment = request.data.get('comment', '')
        lend.save()
        return Response({'message': '审批完成'})
    
    @action(detail=True, methods=['post'])
    def lend_out(self, request, pk=None):
        """借出"""
        lend = self.get_object()
        if lend.status != 'APPROVED':
            return Response({'error': '只有已审批的出借才能执行借出'}, status=status.HTTP_400_BAD_REQUEST)
        lend.status = 'OUT'
        lend.lend_date = timezone.now().date()
        lend.lend_executor = request.user.username
        # 更新资产临时位置
        lend.asset.department = lend.to_department
        lend.asset.location = lend.to_location
        lend.asset.save()
        lend.save()
        return Response({'message': '已借出'})
    
    @action(detail=True, methods=['post'])
    def return_asset(self, request, pk=None):
        """归还"""
        lend = self.get_object()
        if lend.status not in ['OUT', 'OVERDUE']:
            return Response({'error': '当前状态不允许归还'}, status=status.HTTP_400_BAD_REQUEST)
        lend.status = 'RETURNED'
        lend.actual_return_date = timezone.now().date()
        lend.return_executor = request.user.username
        lend.return_acceptance = request.data.get('return_acceptance', '')
        lend.return_acceptor = request.user.username
        # 恢复资产原位置（可以从调拨记录获取，这里简化为借出时的原部门）
        lend.asset.department = lend.from_department
        lend.asset.location = lend.from_location
        lend.asset.save()
        lend.save()
        return Response({'message': '已归还'})
    
    @action(detail=True, methods=['post'])
    def check_overdue(self, request, pk=None):
        """检查逾期并更新状态"""
        lend = self.get_object()
        if lend.status == 'OUT' and lend.expected_return_date:
            if lend.expected_return_date < timezone.now().date():
                lend.status = 'OVERDUE'
                lend.save()
        return Response({'message': '检查完成', 'status': lend.status})
