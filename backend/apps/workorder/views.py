from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta

from .models import WorkOrder, WorkOrderStep, WorkOrderComment
from .serializers import (
    WorkOrderListSerializer, WorkOrderDetailSerializer,
    WorkOrderCreateSerializer, WorkOrderStepSerializer,
    WorkOrderCommentSerializer
)


class WorkOrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class WorkOrderViewSet(viewsets.ModelViewSet):
    """工单视图集"""
    
    queryset = WorkOrder.objects.all()
    serializer_class = WorkOrderListSerializer
    pagination_class = WorkOrderPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 状态筛选
        status_filter = self.request.query_params.get('status')
        if status_filter and status_filter.isdigit():
            queryset = queryset.filter(status=int(status_filter))
        
        # 类型筛选
        order_type = self.request.query_params.get('type')
        if order_type and order_type.isdigit():
            queryset = queryset.filter(order_type=int(order_type))
        
        # 优先级筛选
        priority = self.request.query_params.get('priority')
        if priority and priority.isdigit():
            queryset = queryset.filter(priority=int(priority))
        
        # 客户筛选
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # 处理人筛选
        handler_id = self.request.query_params.get('handler')
        if handler_id:
            queryset = queryset.filter(handler_id=handler_id)
        
        # 关键词搜索
        keyword = self.request.query_params.get('keyword')
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) |
                Q(resume__icontains=keyword) |
                Q(description__icontains=keyword)
            )
        
        return queryset.select_related('customer', 'creator', 'handler')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkOrderDetailSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return WorkOrderCreateSerializer
        return WorkOrderListSerializer
    
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user if self.request.user.is_authenticated else None)
    
    @action(detail=True, methods=['post'])
    def add_step(self, request, pk=None):
        """添加工单步骤"""
        work_order = self.get_object()
        
        serializer = WorkOrderStepSerializer(data={
            'order': work_order.id,
            'description': request.data.get('description', ''),
            'status': request.data.get('status', work_order.status),
            'handler': request.data.get('handler') or (request.user.id if request.user.is_authenticated else None),
        })
        
        if serializer.is_valid():
            serializer.save()
            # 如果步骤状态改变，同步更新工单状态
            new_status = request.data.get('status')
            if new_status is not None:
                work_order.status = int(new_status)
                work_order.save()
            return Response({'success': True, 'message': '步骤添加成功'})
        return Response({'success': False, 'errors': serializer.errors}, status=400)
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """添加评论"""
        work_order = self.get_object()
        
        serializer = WorkOrderCommentSerializer(data={
            'order': work_order.id,
            'user': request.user.id if request.user.is_authenticated else None,
            'content': request.data.get('content', ''),
        })
        
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'message': '评论添加成功'})
        return Response({'success': False, 'errors': serializer.errors}, status=400)
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """修改工单状态"""
        work_order = self.get_object()
        new_status = request.data.get('status')
        
        if new_status is not None:
            work_order.status = int(new_status)
            work_order.save()
            return Response({'success': True, 'message': f'状态已更新为{work_order.get_status_display()}'})
        
        return Response({'success': False, 'message': '请提供状态值'}, status=400)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """分配处理人"""
        work_order = self.get_object()
        handler_id = request.data.get('handler_id')
        
        if handler_id:
            from apps.users.models import User
            try:
                handler = User.objects.get(id=handler_id)
                work_order.handler = handler
                work_order.save()
                return Response({'success': True, 'message': f'已分配给{handler.username}'})
            except User.DoesNotExist:
                return Response({'success': False, 'message': '处理人不存在'}, status=400)
        
        return Response({'success': False, 'message': '请提供处理人ID'}, status=400)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """工单统计"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        total = self.queryset.count()
        today_count = self.queryset.filter(cttime__date=today).count()
        week_count = self.queryset.filter(cttime__date__gte=week_ago).count()
        
        # 按状态统计
        by_status = {}
        for status_value, status_name in WorkOrder.STATUS_CHOICES:
            count = self.queryset.filter(status=status_value).count()
            by_status[status_value] = {'name': status_name, 'count': count}
        
        # 按类型统计
        by_type = {}
        for type_value, type_name in WorkOrder.TYPE_CHOICES:
            count = self.queryset.filter(order_type=type_value).count()
            by_type[type_value] = {'name': type_name, 'count': count}
        
        # 待处理工单
        pending = self.queryset.filter(status__in=[0, 1]).count()
        
        return Response({
            'total': total,
            'today': today_count,
            'week': week_count,
            'pending': pending,
            'by_status': by_status,
            'by_type': by_type,
        })
    
    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        """我的工单（我创建的+我处理的）"""
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response({'results': [], 'count': 0})
        
        queryset = self.queryset.filter(
            Q(creator=user) | Q(handler=user)
        ).distinct().order_by('-cttime')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = WorkOrderListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = WorkOrderListSerializer(queryset, many=True)
        return Response({'results': serializer.data, 'count': queryset.count()})


class WorkOrderStepViewSet(viewsets.ModelViewSet):
    """工单步骤视图集"""
    
    queryset = WorkOrderStep.objects.all()
    serializer_class = WorkOrderStepSerializer
    pagination_class = WorkOrderPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        order_id = self.request.query_params.get('order')
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        
        return queryset.select_related('handler', 'order')
