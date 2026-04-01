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
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
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
        asset_type_code = None
        
        # 获取资产类型
        try:
            if task.asset and task.asset.asset_type:
                asset_type_code = task.asset.asset_type.type_code
        except Exception:
            pass
        
        # 执行基础巡检 (Ping + 端口) - 所有资产类型都做
        if ip:
            ping_result = self._check_ping(ip)
            results.append(ping_result)
            
            port_result = self._check_port(ip)
            if port_result:
                results.append(port_result)
        
        # 执行数据库巡检 (仅数据库类型资产)
        # run_inspection 会创建自己的 InspectionRecord 和 InspectionResult
        if asset_type_code == 'DATABASE':
            db_results = self._run_db_inspection(task)
            results.extend(db_results)
            # 创建巡检记录
            pass_count = sum(1 for r in results if r['status'] == 'pass')
            fail_count = sum(1 for r in results if r['status'] == 'fail')
            warning_count = sum(1 for r in results if r['status'] == 'warning')
            overall = 'fail' if fail_count > 0 else ('warning' if warning_count > 0 else 'pass')
            InspectionRecord.objects.create(
                task=task, asset=task.asset,
                total_checks=len(results),
                pass_checks=pass_count, warning_checks=warning_count, fail_checks=fail_count,
                status='completed', overall_status=overall,
                executor=request.user if request.user.is_authenticated else None,
                started_at=task.executed_time, completed_at=timezone.now()
            )
        else:
            # 非数据库类型：只创建基础检查结果
            for r in results:
                InspectionResult.objects.create(
                    task=task, asset=task.asset,
                    check_item=r['check_item'], check_item_code=r['check_item_code'],
                    status=r['status'], result_value=r.get('result_value', ''),
                    result_message=r['result_message'], suggestion=r.get('suggestion', '')
                )
            pass_count = sum(1 for r in results if r['status'] == 'pass')
            fail_count = sum(1 for r in results if r['status'] == 'fail')
            overall = 'pass' if fail_count == 0 else 'fail'
            InspectionRecord.objects.create(
                task=task, asset=task.asset,
                total_checks=len(results),
                pass_checks=pass_count, warning_checks=0, fail_checks=fail_count,
                status='completed', overall_status=overall,
                executor=request.user if request.user.is_authenticated else None,
                started_at=task.executed_time, completed_at=timezone.now()
            )
        
        # 更新任务状态
        task.status = 'completed'
        task.save()
        
        return Response({
            'success': True,
            'message': f'巡检完成，发现{len(results)}个检查项（通过{pass_count}，警告{warning_count if asset_type_code == "DATABASE" else 0}，失败{fail_count}）',
            'results': results
        })
    
    def _run_db_inspection(self, task):
        """执行数据库巡检（复用 execute_db_inspection 的逻辑）"""
        from apps.inspection.db_inspector_v2 import run_inspection
        try:
            record = run_inspection(task.id, custom_sql=None)
            # 从巡检记录中提取结果
            results = []
            for ir in record.results.all():
                status_map = {'pass': 'pass', 'warning': 'warning', 'fail': 'fail', 'error': 'fail', 'skip': 'skip'}
                results.append({
                    'check_item': ir.check_item,
                    'check_item_code': ir.check_item_code,
                    'status': status_map.get(ir.status, 'fail'),
                    'result_value': ir.result_value or '',
                    'result_message': ir.result_message or ''
                })
            return results
        except Exception as e:
            return [{
                'check_item': '数据库巡检',
                'check_item_code': 'DB_INSPECTION',
                'status': 'fail',
                'result_value': '错误',
                'result_message': f'数据库巡检执行失败: {str(e)}'
            }]
    
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

    @action(detail=True, methods=['post'])
    def execute_db_inspection(self, request, pk=None):
        """执行数据库巡检（支持自定义SQL）"""
        task = self.get_object()
        custom_sql = request.data.get('custom_sql', None)

        # 更新状态
        task.status = 'in_progress'
        task.executed_time = timezone.now()
        task.save()

        try:
            from apps.inspection.db_inspector_v2 import run_inspection
            record = run_inspection(task.id, custom_sql=custom_sql)

            return Response({
                'success': True,
                'message': record.summary,
                'record_id': record.id,
                'total_checks': record.total_checks,
                'pass_checks': record.pass_checks,
                'warning_checks': record.warning_checks,
                'fail_checks': record.fail_checks,
                'overall_status': record.overall_status,
            })
        except Exception as e:
            task.status = 'failed'
            task.save()
            return Response({
                'success': False,
                'message': f'巡检执行失败: {str(e)}'
            }, status=500)

    @action(detail=False, methods=['post'])
    def execute_custom_sql(self, request):
        """执行自定义SQL查询"""
        asset_id = request.data.get('asset_id')
        sql = request.data.get('sql')

        if not asset_id or not sql:
            return Response({'error': 'asset_id 和 sql 为必填项'}, status=400)

        try:
            from apps.assets.models import Asset
            from apps.inspection.db_connectors import get_connector_from_asset

            asset = Asset.objects.get(id=asset_id)
            connector = get_connector_from_asset(asset)
            result = connector.execute_custom_sql(sql)

            return Response(result)
        except Asset.DoesNotExist:
            return Response({'error': '资产不存在'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class InspectionRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """巡检记录视图集（只读）"""
    
    queryset = InspectionRecord.objects.all()
    serializer_class = InspectionRecordSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        asset_id = self.request.query_params.get('asset')
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        overall_status = self.request.query_params.get('overall_status')
        if overall_status:
            queryset = queryset.filter(overall_status=overall_status)
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
