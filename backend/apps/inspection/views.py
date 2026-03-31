from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
import subprocess

from .models import InspectionPlan, InspectionTask, InspectionResult, InspectionRecord
from .serializers import (
    InspectionPlanSerializer, InspectionTaskSerializer,
    InspectionResultSerializer, InspectionRecordSerializer,
    InspectionRecordDetailSerializer
)


class InspectionPlanViewSet(viewsets.ModelViewSet):
    """巡检计划视图集"""
    
    queryset = InspectionPlan.objects.all()
    serializer_class = InspectionPlanSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """启用巡检计划"""
        plan = self.get_object()
        plan.status = 'active'
        plan.save()
        return Response({'success': True, 'message': '巡检计划已启用'})
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停巡检计划"""
        plan = self.get_object()
        plan.status = 'paused'
        plan.save()
        return Response({'success': True, 'message': '巡检计划已暂停'})


class InspectionTaskViewSet(viewsets.ModelViewSet):
    """巡检任务视图集"""
    
    queryset = InspectionTask.objects.all()
    serializer_class = InspectionTaskSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        plan_id = self.request.query_params.get('plan')
        asset_id = self.request.query_params.get('asset')
        task_status = self.request.query_params.get('status')
        
        if plan_id:
            queryset = queryset.filter(plan_id=plan_id)
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        if task_status:
            queryset = queryset.filter(status=task_status)
        return queryset
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行巡检任务"""
        task = self.get_object()
        
        # 更新任务状态
        task.status = 'in_progress'
        task.executed_time = timezone.now()
        task.save()
        
        # 获取资产的IP地址
        from apps.assets.models import AssetData
        ip_data = AssetData.objects.filter(asset=task.asset, field__field_code='ip_address').first()
        ip = ip_data.string_value if ip_data else None
        
        results = []
        
        # 执行基础巡检
        if ip:
            # Ping检测
            ping_result = self._check_ping(ip)
            results.append(ping_result)
            
            # 端口检测
            port_result = self._check_port(ip)
            if port_result:
                results.append(port_result)
        
        # 创建巡检结果
        for r in results:
            InspectionResult.objects.create(
                task=task,
                asset=task.asset,
                check_item=r['check_item'],
                check_item_code=r['check_item_code'],
                status=r['status'],
                result_value=r['result_value'],
                result_message=r['result_message'],
                suggestion=r.get('suggestion', '')
            )
        
        # 创建巡检记录
        pass_count = sum(1 for r in results if r['status'] == 'pass')
        fail_count = sum(1 for r in results if r['status'] == 'fail')
        
        InspectionRecord.objects.create(
            task=task,
            asset=task.asset,
            total_checks=len(results),
            pass_checks=pass_count,
            fail_checks=fail_count,
            status='completed' if fail_count == 0 else 'partial',
            overall_status='pass' if fail_count == 0 else 'warning',
            executor=request.user if request.user.is_authenticated else None,
            started_at=task.executed_time,
            completed_at=timezone.now()
        )
        
        # 更新任务状态
        task.status = 'completed'
        task.save()
        
        return Response({
            'success': True,
            'message': f'巡检完成，发现{len(results)}个检查项',
            'results': results
        })
    
    def _check_ping(self, ip):
        """Ping检测"""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', ip],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # 解析响应时间
                for line in result.stdout.split('\n'):
                    if 'time=' in line:
                        time_ms = line.split('time=')[1].split()[0]
                        return {
                            'check_item': '网络连通性',
                            'check_item_code': 'NETWORK_PING',
                            'status': 'pass',
                            'result_value': f'{time_ms}ms',
                            'result_message': f'主机 {ip} 连通正常'
                        }
            
            return {
                'check_item': '网络连通性',
                'check_item_code': 'NETWORK_PING',
                'status': 'fail',
                'result_value': '超时',
                'result_message': f'主机 {ip} 连接超时'
            }
        except Exception as e:
            return {
                'check_item': '网络连通性',
                'check_item_code': 'NETWORK_PING',
                'status': 'fail',
                'result_value': '错误',
                'result_message': str(e)
            }
    
    def _check_port(self, ip, port=22):
        """端口检测"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                return {
                    'check_item': f'SSH端口({port})',
                    'check_item_code': 'PORT_SSH',
                    'status': 'pass',
                    'result_value': '开放',
                    'result_message': f'SSH端口 {port} 开放'
                }
            else:
                return {
                    'check_item': f'SSH端口({port})',
                    'check_item_code': 'PORT_SSH',
                    'status': 'fail',
                    'result_value': '关闭',
                    'result_message': f'SSH端口 {port} 关闭'
                }
        except Exception as e:
            return {
                'check_item': f'SSH端口({port})',
                'check_item_code': 'PORT_SSH',
                'status': 'warning',
                'result_value': '错误',
                'result_message': str(e)
            }


class InspectionRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """巡检记录视图集（只读）"""
    
    queryset = InspectionRecord.objects.all()
    serializer_class = InspectionRecordSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        asset_id = self.request.query_params.get('asset')
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        """获取巡检记录详情"""
        instance = self.get_object()
        serializer = InspectionRecordDetailSerializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """巡检统计"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        total_records = self.queryset.count()
        today_records = self.queryset.filter(created_at__date=today).count()
        week_records = self.queryset.filter(created_at__date__gte=week_ago).count()
        
        pass_count = self.queryset.filter(overall_status='pass').count()
        warning_count = self.queryset.filter(overall_status='warning').count()
        fail_count = self.queryset.filter(overall_status='fail').count()
        
        return Response({
            'total_records': total_records,
            'today_records': today_records,
            'week_records': week_records,
            'pass_count': pass_count,
            'warning_count': warning_count,
            'fail_count': fail_count,
            'pass_rate': round(pass_count / total_records * 100, 2) if total_records > 0 else 0
        })
