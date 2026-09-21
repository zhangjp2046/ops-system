from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from decimal import Decimal
from .models import (
    MaterialCategory, Material,
    DeptStock, DeptStockRecord,
    MaterialOrder, MaterialOrderItem,
    ConsumptionRecord, StockAlert,
)
from .serializers import (
    MaterialCategorySerializer, MaterialSerializer,
    DeptStockSerializer, DeptStockRecordSerializer,
    MaterialOrderSerializer, MaterialOrderItemSerializer,
    ConsumptionRecordSerializer, StockAlertSerializer,
)


class MaterialCategoryViewSet(viewsets.ModelViewSet):
    """物资分类管理"""
    queryset = MaterialCategory.objects.filter(is_active=True)
    serializer_class = MaterialCategorySerializer


class MaterialViewSet(viewsets.ModelViewSet):
    """物资台账管理"""
    queryset = Material.objects.filter(is_active=True)
    serializer_class = MaterialSerializer
    filterset_fields = ['category', 'code', 'name']
    search_fields = ['code', 'name', 'spec']


class DeptStockViewSet(viewsets.ModelViewSet):
    """科室库存管理"""
    queryset = DeptStock.objects.all()
    serializer_class = DeptStockSerializer
    filterset_fields = ['department', 'material']
    search_fields = ['department', 'material__name']
    
    @action(detail=False, methods=['get'])
    def by_department(self, request):
        """按科室查询库存"""
        department = request.query_params.get('department', '')
        stocks = DeptStock.objects.filter(department__icontains=department)
        serializer = self.get_serializer(stocks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def in_stock(self, request, pk=None):
        """入库操作"""
        stock = self.get_object()
        quantity = request.data.get('quantity', 0)
        order_no = request.data.get('order_no', '')
        remark = request.data.get('remark', '')
        
        try:
            stock.quantity += Decimal(str(quantity))
            stock.save()
            
            DeptStockRecord.objects.create(
                stock=stock,
                direction='IN',
                quantity=quantity,
                order_no=order_no,
                remark=remark,
                operator=request.data.get('operator', ''),
            )
            return Response({'status': 'success', 'quantity': stock.quantity})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=400)
    
    @action(detail=True, methods=['post'])
    def consume(self, request, pk=None):
        """消耗操作"""
        stock = self.get_object()
        quantity = request.data.get('quantity', 0)
        consume_type = request.data.get('consume_type', 'OTHER')
        remark = request.data.get('remark', '')
        
        try:
            if stock.quantity < Decimal(str(quantity)):
                return Response({
                    'status': 'error',
                    'message': f'库存不足：当前 {stock.quantity}，需要 {quantity}'
                }, status=400)
            
            stock.quantity -= Decimal(str(quantity))
            stock.save()
            
            DeptStockRecord.objects.create(
                stock=stock,
                direction='OUT',
                quantity=quantity,
                consume_type=consume_type,
                remark=remark,
                operator=request.data.get('operator', ''),
            )
            
            # 检查是否需要预警
            if stock.material.min_stock and stock.quantity < stock.material.min_stock:
                stock.min_stock_alert = True
                stock.save()
                
                StockAlert.objects.create(
                    material=stock.material,
                    department=stock.department,
                    alert_type='LOW_STOCK',
                    current_quantity=stock.quantity,
                    threshold_value=stock.material.min_stock,
                )
            
            return Response({'status': 'success', 'quantity': stock.quantity})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=400)


class DeptStockRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """库存明细查询"""
    queryset = DeptStockRecord.objects.all()
    serializer_class = DeptStockRecordSerializer
    filterset_fields = ['stock', 'direction', 'order_no']
    search_fields = ['order_no', 'stock__department']


class MaterialOrderViewSet(viewsets.ModelViewSet):
    """物资单据管理"""
    queryset = MaterialOrder.objects.all()
    serializer_class = MaterialOrderSerializer
    filterset_fields = ['order_type', 'status']
    search_fields = ['order_no', 'supplier']
    
    def create(self, request, *args, **kwargs):
        data = request.data
        items_data = data.pop('items', [])
        
        order = MaterialOrder.objects.create(**data)
        
        total = Decimal('0')
        for item_data in items_data:
            item_data['order'] = order.id
            item_data['subtotal'] = Decimal(str(item_data['quantity'])) * Decimal(str(item_data['unit_price']))
            item = MaterialOrderItem.objects.create(**item_data)
            total += item.subtotal
        
        order.total_amount = total
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConsumptionRecordViewSet(viewsets.ModelViewSet):
    """消耗记录管理"""
    queryset = ConsumptionRecord.objects.all()
    serializer_class = ConsumptionRecordSerializer
    filterset_fields = ['department', 'material', 'consume_type']
    search_fields = ['department', 'material__name']
    
    def get_queryset(self):
        qs = super().get_queryset()
        # 支持日期范围筛选
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(created_at__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__lte=end_date)
        return qs


class StockAlertViewSet(viewsets.ModelViewSet):
    """库存预警管理"""
    queryset = StockAlert.objects.all()
    serializer_class = StockAlertSerializer
    filterset_fields = ['department', 'alert_type', 'is_resolved']
    search_fields = ['department', 'material__name']
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """处理预警"""
        alert = self.get_object()
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.data.get('operator', '')
        alert.resolution = request.data.get('resolution', '')
        alert.save()
        return Response({'status': 'resolved'})