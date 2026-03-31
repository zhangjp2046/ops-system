#!/usr/bin/env python3
"""
巡检执行API
提供手工和定时巡检的接口
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.inspection.models import Inspection, InspectionTemplate
from apps.assets.models import Asset
from apps.scheduler.models import ScheduledTask


class InspectionRunView(APIView):
    """手工执行巡检视图"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        手工执行巡检
        
        参数:
        - asset_id: 资产ID
        - inspection_type: 巡检类型 (SNMP, DATABASE, SECURITY, etc.)
        """
        asset_id = request.data.get('asset_id')
        inspection_type = request.data.get('inspection_type', 'SNMP')
        
        if not asset_id:
            return Response({
                'success': False,
                'message': '缺少资产ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            asset = Asset.objects.get(id=asset_id)
        except Asset.DoesNotExist:
            return Response({
                'success': False,
                'message': f'资产 {asset_id} 不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 创建巡检记录
        from django.utils import timezone
        inspection = Inspection.objects.create(
            name=f'手工巡检-{asset.asset_name}',
            description=f'手工触发巡检 - {request.user.username}',
            inspection_type=inspection_type,
            customer=asset.customer,
            asset=asset,
            asset_type=asset.asset_type,
            status='RUNNING',
            started_at=timezone.now()
        )
        
        # 根据巡检类型执行
        try:
            if inspection_type == 'DATABASE':
                from apps.inspection.db_inspector import run_database_inspection
                result = run_database_inspection(inspection.id)
            else:
                # 默认使用SNMP巡检
                from apps.inspection.executors import run_inspection
                result = run_inspection(inspection.id)
            
            return Response({
                'success': True,
                'message': '巡检执行成功',
                'data': {
                    'inspection_id': inspection.id,
                    'status': result.status,
                    'passed_items': result.passed_items,
                    'warning_items': result.warning_items,
                    'failed_items': result.failed_items,
                    'summary': result.summary
                }
            })
            
        except Exception as e:
            inspection.status = 'FAILED'
            inspection.save()
            
            return Response({
                'success': False,
                'message': f'巡检执行失败: {str(e)}',
                'inspection_id': inspection.id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InspectionBatchRunView(APIView):
    """批量执行巡检视图"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        批量执行巡检
        
        参数:
        - customer_id: 客户ID (可选，0表示全部客户)
        - asset_ids: 资产ID列表 (可选)
        - inspection_type: 巡检类型
        """
        customer_id = request.data.get('customer_id', 0)
        asset_ids = request.data.get('asset_ids', [])
        inspection_type = request.data.get('inspection_type', 'SNMP')
        
        # 获取资产列表
        if asset_ids:
            assets = Asset.objects.filter(id__in=asset_ids, status='ACTIVE')
        elif customer_id > 0:
            assets = Asset.objects.filter(customer_id=customer_id, status='ACTIVE')
        else:
            assets = Asset.objects.filter(status='ACTIVE')
        
        if not assets.exists():
            return Response({
                'success': False,
                'message': '没有找到可巡检的资产'
            }, status=status.HTTP_404_NOT_FOUND)
        
        from django.utils import timezone
        results = []
        
        for asset in assets:
            inspection = Inspection.objects.create(
                name=f'批量巡检-{asset.asset_name}',
                description=f'批量巡检 - {request.user.username}',
                inspection_type=inspection_type,
                customer=asset.customer,
                asset=asset,
                asset_type=asset.asset_type,
                status='RUNNING',
                started_at=timezone.now()
            )
            
            try:
                if inspection_type == 'DATABASE':
                    from apps.inspection.db_inspector import run_database_inspection
                    result = run_database_inspection(inspection.id)
                else:
                    from apps.inspection.executors import run_inspection
                    result = run_inspection(inspection.id)
                
                results.append({
                    'asset_id': asset.id,
                    'asset_name': asset.asset_name,
                    'inspection_id': inspection.id,
                    'status': result.status,
                    'passed_items': result.passed_items,
                    'warning_items': result.warning_items,
                    'failed_items': result.failed_items
                })
            except Exception as e:
                results.append({
                    'asset_id': asset.id,
                    'asset_name': asset.asset_name,
                    'inspection_id': inspection.id,
                    'status': 'failed',
                    'error': str(e)
                })
        
        passed = sum(1 for r in results if r.get('status') == 'COMPLETED')
        failed = sum(1 for r in results if r.get('status') == 'failed')
        
        return Response({
            'success': True,
            'message': f'批量巡检完成',
            'data': {
                'total': len(results),
                'passed': passed,
                'failed': failed,
                'results': results
            }
        })


class InspectionStatusView(APIView):
    """巡检状态视图"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, inspection_id):
        """获取巡检详情"""
        try:
            inspection = Inspection.objects.get(id=inspection_id)
        except Inspection.DoesNotExist:
            return Response({
                'success': False,
                'message': f'巡检 {inspection_id} 不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 获取巡检项目
        items = []
        for item in inspection.items.all():
            items.append({
                'item_code': item.item_code,
                'item_name': item.item_name,
                'category': item.category,
                'result': item.result,
                'severity': item.severity,
                'actual_value': item.actual_value,
                'expected_value': item.expected_value,
                'message': item.message
            })
        
        return Response({
            'success': True,
            'data': {
                'id': inspection.id,
                'name': inspection.name,
                'status': inspection.status,
                'inspection_type': inspection.inspection_type,
                'asset_name': inspection.asset.asset_name if inspection.asset else None,
                'passed_items': inspection.passed_items,
                'warning_items': inspection.warning_items,
                'failed_items': inspection.failed_items,
                'total_items': inspection.total_items,
                'summary': inspection.summary,
                'started_at': inspection.started_at,
                'completed_at': inspection.completed_at,
                'duration_ms': inspection.duration_ms,
                'items': items
            }
        })


class InspectionListView(APIView):
    """巡检记录列表视图"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """获取巡检记录列表"""
        # 过滤参数
        customer_id = request.query_params.get('customer_id')
        asset_id = request.query_params.get('asset_id')
        inspection_type = request.query_params.get('type')
        status_filter = request.query_params.get('status')
        
        # 构建查询
        inspections = Inspection.objects.all()
        
        if customer_id:
            inspections = inspections.filter(customer_id=customer_id)
        if asset_id:
            inspections = inspections.filter(asset_id=asset_id)
        if inspection_type:
            inspections = inspections.filter(inspection_type=inspection_type)
        if status_filter:
            inspections = inspections.filter(status=status_filter)
        
        # 分页
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = inspections.count()
        results = []
        
        for inspection in inspections[start:end]:
            results.append({
                'id': inspection.id,
                'name': inspection.name,
                'status': inspection.status,
                'inspection_type': inspection.inspection_type,
                'asset_name': inspection.asset.asset_name if inspection.asset else None,
                'customer_name': inspection.customer.customer_name,
                'passed_items': inspection.passed_items,
                'warning_items': inspection.warning_items,
                'failed_items': inspection.failed_items,
                'summary': inspection.summary,
                'started_at': inspection.started_at,
                'completed_at': inspection.completed_at
            })
        
        return Response({
            'success': True,
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'results': results
            }
        })
