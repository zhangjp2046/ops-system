from rest_framework import viewsets, status, pagination
from rest_framework.decorators import action
from rest_framework.response import Response


class RestFrameworkPageNumberPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100
from django.utils import timezone
from datetime import datetime, timedelta
import subprocess

from .models import InspectionPlan, InspectionTask, InspectionResult, InspectionRecord, Inspection
from .serializers import (
    InspectionPlanSerializer, InspectionTaskSerializer,
    InspectionResultSerializer, InspectionRecordSerializer,
    InspectionRecordDetailSerializer, InspectionSerializer
)
from .check_items import get_check_items_by_protocol, get_all_protocols, get_protocol_categories




class InspectionPlanViewSet(viewsets.ModelViewSet):
    """巡检计划视图集 - 定义巡检模板和关联资产"""

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
        protocol_filter = self.request.query_params.get('protocol')
        if protocol_filter:
            queryset = queryset.filter(protocol=protocol_filter)
        return queryset

    @action(detail=False, methods=['get'])
    def perform_destroy(self, instance):
        """删除前先解除调度计划的关联，避免外键约束"""
        from apps.scheduler_v2.models import Plan
        # 先把关联的调度计划指向 null，再删除巡检计划
        Plan.objects.filter(inspection_plan=instance).update(inspection_plan=None, inspection_plan_name=None)
        instance.delete()

    def protocols(self, request):
        """获取所有巡检协议分类"""
        return Response({
            'success': True,
            'data': get_all_protocols()
        })

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """获取协议分类（按数据库/设备/网络分组）"""
        return Response({
            'success': True,
            'data': get_protocol_categories()
        })

    @action(detail=False, methods=['get'])
    def check_items(self, request):
        """获取指定协议的巡检项目"""
        protocol = request.query_params.get('protocol', '')
        if not protocol:
            return Response({'success': False, 'message': '请指定协议类型'}, status=400)
        items = get_check_items_by_protocol(protocol)
        return Response({'success': True, 'data': items})

    @action(detail=False, methods=['get'])
    def assets_by_protocol(self, request):
        """获取某协议下的资产，按设备类型分组，方便创建计划时选择"""
        protocol = request.query_params.get('protocol', '')
        if not protocol:
            return Response({'success': False, 'error': '请指定协议'}, status=400)
        
        from apps.assets.models import Asset, AssetType
        
        # 查询该协议的资产
        matched = Asset.objects.filter(protocol=protocol, status__in=['ACTIVE', 'ONLINE'])
        
        # 按 asset_type 分组
        from collections import defaultdict
        type_groups = defaultdict(list)
        for asset in matched.select_related('asset_type'):
            at = asset.asset_type
            type_groups[at.id].append({
                'id': asset.id,
                'name': asset.asset_name,
                'ip': asset.ip_address or '',
                'asset_code': asset.asset_code,
            })
        
        # 构建返回
        groups = []
        for type_id, assets in type_groups.items():
            try:
                at_obj = AssetType.objects.get(id=type_id)
                type_name = at_obj.type_name
            except AssetType.DoesNotExist:
                type_name = '未知类型'
            groups.append({
                'type_id': type_id,
                'type_name': type_name,
                'asset_count': len(assets),
                'assets': assets,
            })
        
        # 按数量排序
        groups.sort(key=lambda g: g['asset_count'], reverse=True)
        
        return Response({
            'success': True,
            'data': {
                'protocol': protocol,
                'total_assets': sum(g['asset_count'] for g in groups),
                'type_groups': groups,
            }
        })

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行巡检计划（遍历所有关联任务）"""
        from apps.skills.inspection import InspectionSkill
        skill = InspectionSkill()
        result = skill.execute(
            config={'inspection_plan_id': int(pk)},
            context={'triggered_by': 'manual', 'customer_id': None}
        )
        return Response({
            'success': result.success,
            'message': result.error or f"执行完成，共巡检 {result.data.get('inspected', 0)} 个资产",
            'data': result.data
        })

    def perform_destroy(self, instance):
        """删除前清除所有关联数据（跨多个legacy表的外键约束）"""
        from django.db import connection
        with connection.cursor() as c:
            # 1. scheduler_task_instances → scheduler_plan_executions → scheduler_plans
            c.execute("""
                DELETE ti FROM scheduler_task_instances ti
                INNER JOIN scheduler_plan_executions pe ON ti.plan_execution_id = pe.id
                INNER JOIN scheduler_plans sp ON pe.plan_id = sp.id
                WHERE sp.inspection_plan_id = %s
            """, [instance.id])
            # 2. scheduler_plan_executions → scheduler_plans
            c.execute("""
                DELETE pe FROM scheduler_plan_executions pe
                INNER JOIN scheduler_plans sp ON pe.plan_id = sp.id
                WHERE sp.inspection_plan_id = %s
            """, [instance.id])
            # 3. scheduler_plans（引用 inspection_plans）
            c.execute("DELETE FROM scheduler_plans WHERE inspection_plan_id = %s", [instance.id])
            # 4. inspection_tasks（引用 inspection_plans，plan_id 为 NOT NULL，只能删除）
            c.execute("DELETE FROM inspection_tasks WHERE plan_id = %s", [instance.id])
            # 5. 最后删 inspection_plans 本身
        instance.delete()

    def perform_create(self, serializer):
        """创建时自动设置默认巡检项目和时间"""
        validated = serializer.validated_data
        # 数据库 scheduled_time 不能为 null，设默认值
        if not validated.get('scheduled_time'):
            validated['scheduled_time'] = '09:00:00'
        if not validated.get('cycle'):
            validated['cycle'] = 'daily'
        instance = serializer.save()


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
        """执行巡检任务 - 根据计划协议和巡检项目执行"""
        task = self.get_object()
        
        # 更新任务状态
        task.status = 'in_progress'
        task.executed_time = timezone.now()
        task.save()
        
        # 获取资产IP
        ip = task.asset.ip_address
        if not ip:
            try:
                from apps.assets.models import AssetData
                ip_data = AssetData.objects.filter(asset=task.asset, field__field_code='ip_address').first()
                ip = ip_data.string_value if ip_data else None
            except Exception:
                ip = None
        
        # 从名称提取IP
        if not ip:
            import re
            m = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', task.asset.asset_name or '')
            if m:
                ip = m.group()
        
        # 获取计划的协议和巡检项目
        plan = task.plan
        protocol = plan.protocol if plan else 'ping'
        check_items = plan.check_items if plan and plan.check_items else []
        
        results = []
        
        try:
            if protocol == 'ssh':
                results = self._execute_ssh_checks(task, ip, check_items)
            elif protocol in ('mysql', 'mssql', 'oracle', 'postgresql'):
                results = self._execute_db_checks(task, check_items)
            elif protocol == 'snmp':
                results = self._execute_snmp_checks(task, ip, check_items)
            elif protocol == 'ping':
                results = self._execute_ping_checks(task, ip, check_items)
            elif protocol == 'port':
                results = self._execute_port_checks(task, ip, check_items)
            else:
                results = self._execute_ping_checks(task, ip, check_items)
        except Exception as e:
            results.append({
                'check_item': '巡检执行', 'check_item_code': 'EXEC_ERROR',
                'status': 'fail', 'result_value': '异常',
                'result_message': f'巡检执行失败: {str(e)}'
            })
        
        # 清除旧结果
        InspectionResult.objects.filter(task=task).delete()
        InspectionRecord.objects.filter(task=task).delete()
        
        # 保存结果，同时计算严重程度
        from apps.alerts.alert_generator import get_threshold_severity
        for r in results:
            # 从阈值配置计算严重程度
            sev, sev_name, found = get_threshold_severity(
                r['check_item_code'],
                r.get('result_value', ''),
                customer_id=task.asset.customer_id,
                asset_type_id=task.asset.asset_type_id
            )
            # 如果没有找到阈值配置，使用status映射到severity
            if not found:
                sev = {'pass': 1, 'skip': 1, 'warning': 2, 'fail': 3}.get(r['status'], 1)

            InspectionResult.objects.create(
                task=task, asset=task.asset,
                check_item=r['check_item'], check_item_code=r['check_item_code'],
                status=r['status'], severity=sev,
                result_value=r.get('result_value', ''),
                result_message=r.get('result_message', ''), suggestion=r.get('suggestion', '')
            )

        # 基于severity计算总体状态（阈值可控制哪些情况算不合格）
        # severity: 1=信息(通过) 2=警告 3=错误 4=严重(不合格)
        pass_count = sum(1 for r in results if r['status'] == 'pass')
        pass_count = sum(1 for r in results if r['status'] == 'pass')
        warning_count = sum(1 for r in results if r['status'] == 'warning')
        fail_count = sum(1 for r in results if r['status'] == 'fail')
        # 从数据库重新读取severity判断fail（避免状态不一致）
        max_severity = InspectionResult.objects.filter(task=task).order_by('-severity').first()
        max_sev = max_severity.severity if max_severity else 1
        # 严重程度3=错误/4=严重 都算不合格，只有1=信息/2=警告不算不合格
        overall = 'fail' if max_sev >= 3 else ('warning' if max_sev == 2 else 'pass')
        
        from django.utils import timezone as tz
        InspectionRecord.objects.create(
            task=task, asset=task.asset,
            total_checks=len(results),
            pass_checks=pass_count, warning_checks=warning_count, fail_checks=InspectionResult.objects.filter(task=task, severity__gte=3).count(),
            status='completed', overall_status=overall,
            summary=f'{len(results)}项检查: {pass_count}通过, {warning_count}警告, {fail_count}异常',
            executor=request.user if request.user.is_authenticated else None,
            started_at=task.executed_time, completed_at=tz.now()
        )
        
        task.status = 'completed'
        task.save()

        # 同时写入 Inspection 表（兼容前端巡检记录列表）
        try:
            from django.utils import timezone as tz_now
            insp = Inspection.objects.create(
                name=f'手工巡检-{task.asset.asset_name}',
                description=f'手动执行巡检计划（任务ID: {task.id}）',
                inspection_type=protocol.upper(),
                customer=task.asset.customer,
                asset=task.asset,
                asset_type=task.asset.asset_type,
                status='COMPLETED',
                total_items=len(results),
                passed_items=pass_count,
                warning_items=warning_count,
                failed_items=fail_count,
                started_at=task.executed_time,
                completed_at=tz_now.now(),
                summary=f'{len(results)}项检查: {pass_count}通过, {warning_count}警告, {fail_count}异常'
            )
            # 同时写入 InspectionItem（与 run_inspection 保持一致）
            from apps.inspection.models import InspectionItem
            sev_map = {'pass': 'OK', 'warning': 'WARNING', 'fail': 'FAIL', 'skip': 'INFO'}
            for r in results:
                try:
                    InspectionItem.objects.create(
                        inspection=insp,
                        item_code=r.get('check_item_code', ''),
                        item_name=r.get('check_item', ''),
                        category='snmp',
                        result=r.get('status', '').upper(),
                        severity=sev_map.get(r.get('status', ''), 'INFO'),
                        actual_value=str(r.get('result_value', '')),
                        expected_value='',
                        message=r.get('result_message', ''),
                        details={}
                    )
                except Exception:
                    pass
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'创建 Inspection 记录失败: {e}')

        # 根据巡检结果生成告警
        try:
            from apps.alerts.alert_generator import generate_inspection_alerts
            generate_inspection_alerts(task)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'生成巡检告警失败: {e}')
        
        # 推送巡检结果到 ops-center
        try:
            from apps.dashboard.push_service import push_inspection_result
            push_inspection_result(task)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'推送巡检结果失败: {e}')

        # 记录监控数据点
        try:
            from apps.dashboard.push_service import record_monitoring_data
            record_monitoring_data(task)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'记录监控数据失败: {e}')

        return Response({
            'success': True,
            'message': f'巡检完成: {pass_count}通过, {warning_count}警告, {fail_count}异常',
            'results': results
        })
    
    def _run_command(self, ip, username, password, cmd, timeout=10):
        """通过SSH执行远程命令"""
        import paramiko
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username=username, password=password, timeout=timeout)
            stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            err = stderr.read().decode('utf-8', errors='ignore').strip()
            client.close()
            return output, err
        except Exception as e:
            return None, str(e)
    
    def _get_asset_cred(self, task):
        """获取资产连接凭据"""
        asset = task.asset
        ip = asset.ip_address
        if not ip:
            import re
            m = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', asset.asset_name or '')
            if m:
                ip = m.group()
        return {
            'ip': ip,
            'username': asset.username or 'root',
            'password': asset.password or '',
            'port': int(asset.port) if asset.port else 22,
        }
    
    def _execute_ssh_checks(self, task, ip, check_items):
        """执行SSH巡检"""
        cred = self._get_asset_cred(task)
        ip = cred['ip']
        if not ip:
            return [{'check_item': 'SSH连接', 'check_item_code': 'SSH_CONNECTION',
                     'status': 'fail', 'result_value': '无IP', 'result_message': '资产未配置IP地址'}]
        
        codes = [item.get('code') if isinstance(item, dict) else item for item in check_items]
        results = []
        
        # SSH连接测试
        if 'SSH_CONNECTION' in codes or not codes:
            import paramiko
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(ip, port=cred['port'], username=cred['username'],
                              password=cred['password'], timeout=10)
                client.close()
                results.append({
                    'check_item': 'SSH连接', 'check_item_code': 'SSH_CONNECTION',
                    'status': 'pass', 'result_value': '连接成功',
                    'result_message': f'{cred["username"]}@{ip}:{cred["port"]} 连接正常'
                })
            except Exception as e:
                results.append({
                    'check_item': 'SSH连接', 'check_item_code': 'SSH_CONNECTION',
                    'status': 'fail', 'result_value': '连接失败',
                    'result_message': str(e)
                })
                # 连接失败，剩余项目全部失败
                for code in codes:
                    if code != 'SSH_CONNECTION':
                        name = next((c['name'] for c in check_items if isinstance(c, dict) and c.get('code') == code), code)
                        results.append({
                            'check_item': name, 'check_item_code': code,
                            'status': 'fail', 'result_value': '跳过',
                            'result_message': 'SSH连接失败，无法执行检查'
                        })
                return results
        
        # 系统信息
        if 'SYS_INFO' in codes:
            out, err = self._run_command(ip, cred['username'], cred['password'], 'uname -a && cat /etc/os-release 2>/dev/null | head -5')
            results.append({
                'check_item': '系统信息', 'check_item_code': 'SYS_INFO',
                'status': 'pass' if out else 'warning',
                'result_value': (out or err or '无数据')[:200],
                'result_message': out[:500] if out else err
            })
        
        # CPU使用率
        if 'CPU_USAGE' in codes:
            out, err = self._run_command(ip, cred['username'], cred['password'],
                "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
            try:
                cpu = float(out.replace('%', '').strip()) if out else -1
                status = 'pass' if cpu < 70 else ('warning' if cpu < 90 else 'fail')
                results.append({
                    'check_item': 'CPU使用率', 'check_item_code': 'CPU_USAGE',
                    'status': status, 'result_value': f'{cpu}%',
                    'result_message': f'CPU使用率: {cpu}%',
                    'suggestion': '' if cpu < 70 else 'CPU使用率偏高，请关注'
                })
            except:
                results.append({
                    'check_item': 'CPU使用率', 'check_item_code': 'CPU_USAGE',
                    'status': 'warning', 'result_value': '解析失败',
                    'result_message': out or err
                })
        
        # 内存使用率
        if 'MEM_USAGE' in codes:
            out, err = self._run_command(ip, cred['username'], cred['password'],
                "free -m | awk 'NR==2{printf \"%.1f%% (%sMB/%sMB)\", $3*100/$2, $3, $2}'")
            try:
                pct_str = out.split('%')[0] if out else '0'
                pct = float(pct_str)
                status = 'pass' if pct < 80 else ('warning' if pct < 95 else 'fail')
                results.append({
                    'check_item': '内存使用率', 'check_item_code': 'MEM_USAGE',
                    'status': status, 'result_value': out or '无数据',
                    'result_message': f'内存: {out}' if out else err,
                    'suggestion': '' if pct < 80 else '内存使用率偏高'
                })
            except:
                results.append({
                    'check_item': '内存使用率', 'check_item_code': 'MEM_USAGE',
                    'status': 'warning', 'result_value': '解析失败',
                    'result_message': out or err
                })
        
        # 磁盘使用率
        if 'DISK_USAGE' in codes:
            out, err = self._run_command(ip, cred['username'], cred['password'],
                "df -h | awk 'NR>1{printf \"%s %s %s\\n\", $6, $5, $4}'")
            if out:
                warnings = []
                for line in out.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            pct = int(parts[1].replace('%', ''))
                            if pct > 85:
                                warnings.append(f'{parts[0]}: {parts[1]}')
                        except:
                            pass
                status = 'warning' if warnings else 'pass'
                results.append({
                    'check_item': '磁盘使用率', 'check_item_code': 'DISK_USAGE',
                    'status': status, 'result_value': f'{len(out.strip().split(chr(10)))}个分区',
                    'result_message': out[:500],
                    'suggestion': '磁盘空间不足: ' + ', '.join(warnings) if warnings else ''
                })
            else:
                results.append({
                    'check_item': '磁盘使用率', 'check_item_code': 'DISK_USAGE',
                    'status': 'warning', 'result_value': '获取失败', 'result_message': err
                })
        
        # 系统负载
        if 'LOAD_AVERAGE' in codes:
            out, err = self._run_command(ip, cred['username'], cred['password'],
                "cat /proc/loadavg | awk '{print $1, $2, $3}'")
            if out:
                loads = out.strip().split()
                try:
                    l1 = float(loads[0])
                    status = 'pass' if l1 < 4 else ('warning' if l1 < 8 else 'fail')
                    results.append({
                        'check_item': '系统负载', 'check_item_code': 'LOAD_AVERAGE',
                        'status': status, 'result_value': out.strip(),
                        'result_message': f'1min/5min/15min: {out.strip()}'
                    })
                except:
                    results.append({
                        'check_item': '系统负载', 'check_item_code': 'LOAD_AVERAGE',
                        'status': 'warning', 'result_value': out.strip(), 'result_message': out
                    })
            else:
                results.append({
                    'check_item': '系统负载', 'check_item_code': 'LOAD_AVERAGE',
                    'status': 'warning', 'result_value': '获取失败', 'result_message': err
                })
        
        # 进程数
        if 'PROCESS_COUNT' in codes:
            out, err = self._run_command(ip, cred['username'], cred['password'],
                "ps aux | wc -l")
            try:
                count = int(out.strip()) if out else 0
                status = 'pass' if count < 300 else ('warning' if count < 500 else 'fail')
                results.append({
                    'check_item': '进程数', 'check_item_code': 'PROCESS_COUNT',
                    'status': status, 'result_value': f'{count}个',
                    'result_message': f'当前进程数: {count}'
                })
            except:
                results.append({
                    'check_item': '进程数', 'check_item_code': 'PROCESS_COUNT',
                    'status': 'warning', 'result_value': '解析失败', 'result_message': out or err
                })
        
        # 服务状态
        if 'SERVICE_STATUS' in codes:
            out, err = self._run_command(ip, cred['username'], cred['password'],
                "systemctl list-units --type=service --state=running --no-pager | head -20")
            results.append({
                'check_item': '服务状态', 'check_item_code': 'SERVICE_STATUS',
                'status': 'pass' if out else 'warning',
                'result_value': f'{len(out.strip().split(chr(10)))}个运行中' if out else '无数据',
                'result_message': out[:500] if out else err
            })
        
        # 日志检查
        if 'LOG_CHECK' in codes:
            out, err = self._run_command(ip, cred['username'], cred['password'],
                "journalctl --since '1 hour ago' -p err --no-pager | tail -10 2>/dev/null || dmesg | grep -i error | tail -10")
            count = len(out.strip().split('\n')) if out and out.strip() else 0
            status = 'pass' if count <= 1 else ('warning' if count < 10 else 'fail')
            results.append({
                'check_item': '日志检查', 'check_item_code': 'LOG_CHECK',
                'status': status, 'result_value': f'{count}条错误',
                'result_message': out[:500] if out else '无错误日志'
            })
        
        return results
    
    def _execute_snmp_checks(self, task, ip, check_items):
        """执行SNMP巡检 - 使用标准HOST-RESOURCES-MIB和UCD-SNMP-MIB"""
        cred = self._get_asset_cred(task)
        ip = cred['ip']
        if not ip:
            return [{'check_item': 'SNMP可达性', 'check_item_code': 'SNMP_REACHABLE',
                     'status': 'fail', 'result_value': '无IP', 'result_message': '资产未配置IP地址'}]
        
        codes = [item.get('code') if isinstance(item, dict) else item for item in check_items]
        results = []
        
        # 从AssetData读取SNMP配置（与monitoring模块一致）
        def _get_snmp_field(field_code, default=None):
            try:
                from apps.assets.models import AssetData
                data = AssetData.objects.filter(asset=task.asset, field__field_code=field_code).first()
                if data:
                    return data.get_value()
            except Exception:
                pass
            return default
        
        snmp_port = _get_snmp_field('snmp_port') or 161
        snmp_community = _get_snmp_field('snmp_community') or 'public'
        port = int(snmp_port) if snmp_port else 161
        community = snmp_community
        
        def snmp_get(oid):
            """SNMP GET 单个值"""
            try:
                r = subprocess.run(
                    ['snmpget', '-v2c', '-c', community, '-Oqv', f'{ip}:{port}', oid],
                    capture_output=True, text=True, timeout=8
                )
                if r.returncode == 0:
                    return r.stdout.strip()
            except Exception:
                pass
            return None
        
        def snmp_walk(oid):
            """SNMP WALK 获取多值列表"""
            try:
                r = subprocess.run(
                    ['snmpwalk', '-v2c', '-c', community, '-Oqv', f'{ip}:{port}', oid],
                    capture_output=True, text=True, timeout=10
                )
                if r.returncode == 0:
                    return [line.strip() for line in r.stdout.strip().split('\n') if line.strip()]
            except Exception:
                pass
            return []
        
        def snmp_walk_table(oids_dict):
            """获取SNMP表格（多列对齐）"""
            import re
            result = {}
            for col_name, base_oid in oids_dict.items():
                try:
                    r = subprocess.run(
                        ['snmpwalk', '-v2c', '-c', community, '-Oqn', f'{ip}:{port}', base_oid],
                        capture_output=True, text=True, timeout=10
                    )
                    if r.returncode == 0:
                        for line in r.stdout.strip().split('\n'):
                            if not line.strip():
                                continue
                            parts = line.strip().split(None, 1)
                            if len(parts) == 2:
                                full_oid, val = parts
                                # 提取索引号 (OID末尾)
                                idx = full_oid.split('.')[-1]
                                if idx not in result:
                                    result[idx] = {}
                                result[idx][col_name] = val.strip().strip('"')
                except Exception:
                    pass
            return result
        
        # ====== SNMP可达性 ======
        if 'SNMP_REACHABLE' in codes or not codes:
            sys_descr = snmp_get('1.3.6.1.2.1.1.1.0')  # sysDescr.0
            results.append({
                'check_item': 'SNMP可达性', 'check_item_code': 'SNMP_REACHABLE',
                'status': 'pass' if sys_descr else 'fail',
                'result_value': '可达' if sys_descr else '不可达',
                'result_message': sys_descr[:200] if sys_descr else f'SNMP {ip}:{port} 无响应'
            })
            # 如果SNMP不可达，剩余项目全部标记失败
            if not sys_descr:
                for code in codes:
                    if code != 'SNMP_REACHABLE':
                        name = next((c['name'] for c in check_items if isinstance(c, dict) and c.get('code') == code), code)
                        results.append({
                            'check_item': name, 'check_item_code': code,
                            'status': 'fail', 'result_value': '跳过',
                            'result_message': 'SNMP不可达，无法执行检查'
                        })
                return results
        
        # ====== 系统描述 ======
        if 'SYS_DESCR' in codes:
            v = snmp_get('1.3.6.1.2.1.1.1.0')  # sysDescr.0
            results.append({
                'check_item': '系统描述', 'check_item_code': 'SYS_DESCR',
                'status': 'pass' if v else 'warning',
                'result_value': (v or '无数据')[:150],
                'result_message': v or '无法获取'
            })
        
        # ====== 运行时间 ======
        if 'SYS_UPTIME' in codes:
            v = snmp_get('1.3.6.1.2.1.1.3.0')  # sysUpTime (timeticks format)
            # 解析 timeticks 格式: "123:45:67.89" = days:hours:minutes:seconds.cs，转换为秒
            uptime_seconds = None
            if v:
                try:
                    parts = v.split(':')
                    if len(parts) == 4:
                        days, hours, minutes, seconds = parts
                        uptime_seconds = int(days) * 86400 + int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                    elif len(parts) == 2:  # 可能是另一种格式
                        uptime_seconds = float(v)
                except:
                    pass
            results.append({
                'check_item': '运行时间', 'check_item_code': 'SYS_UPTIME',
                'status': 'pass' if uptime_seconds and uptime_seconds > 86400 else 'warning',
                'result_value': str(int(uptime_seconds)) if uptime_seconds else '0',
                'result_message': f'运行时间: {v}' if v else '无法获取'
            })
        
        # ====== CPU使用率 ======
        # 优先使用 hrProcessorLoad (HOST-RESOURCES-MIB)
        #   - Windows Server: 支持 (hrProcessorLoad)
        #   - Linux (NET-SNMP): 支持 (hrProcessorLoad)
        #   - 网络设备: 通常支持
        # 备用 UCD-SNMP ssCpuIdle (仅 Linux)
        if 'CPU_USAGE' in codes:
            cpu_done = False

            # 方式1: hrProcessorLoad (通用，所有平台)
            raw_loads = snmp_walk('1.3.6.1.2.1.25.3.3.1.2')
            if raw_loads:
                try:
                    loads = [int(x) for x in raw_loads if x.isdigit()]
                    if loads:
                        avg_load = round(sum(loads) / len(loads), 1)
                        max_load = max(loads)
                        usage = avg_load
                        status = 'pass' if usage < 70 else ('warning' if usage < 90 else 'fail')
                        results.append({
                            'check_item': 'CPU使用率', 'check_item_code': 'CPU_USAGE',
                            'status': status, 'result_value': f'{usage}% (平均), 最高{max_load}%',
                            'result_message': f'各核负载: {", ".join(str(x) for x in loads[:8])}{'...' if len(loads) > 8 else ''}',
                            'suggestion': '' if usage < 70 else 'CPU使用率偏高'
                        })
                        cpu_done = True
                except Exception:
                    pass

            # 方式2: UCD-SNMP (仅 Linux，Windows 跳过)
            if not cpu_done:
                cpu_idle = snmp_get('1.3.6.1.4.1.2021.11.11.0')   # ssCpuIdle.0
                if cpu_idle and cpu_idle.isdigit():
                    idle = int(cpu_idle)
                    usage = 100 - idle
                    cpu_user = snmp_get('1.3.6.1.4.1.2021.11.9.0')   # ssCpuUser.0
                    cpu_sys = snmp_get('1.3.6.1.4.1.2021.11.10.0')  # ssCpuSystem.0
                    status = 'pass' if usage < 70 else ('warning' if usage < 90 else 'fail')
                    results.append({
                        'check_item': 'CPU使用率', 'check_item_code': 'CPU_USAGE',
                        'status': status, 'result_value': f'{usage}%',
                        'result_message': f'用户:{cpu_user or "?"}%, 系统:{cpu_sys or "?"}%, 空闲:{idle}%',
                        'suggestion': '' if usage < 70 else 'CPU使用率偏高'
                    })
                    cpu_done = True

            if not cpu_done:
                results.append({
                    'check_item': 'CPU使用率', 'check_item_code': 'CPU_USAGE',
                    'status': 'warning', 'result_value': '不支持',
                    'result_message': '该设备SNMP agent不支持CPU使用率采集（建议配置SSH巡检）'
                })
        
        # ====== 内存使用率 ======
        # 计算口径: (MemTotal - MemAvailable) / MemTotal
        # 这与系统监视器和 free -m 一致，准确反映"实际需要干预与否"
        # 优先使用 UCD-SNMP memTotalReal - memAvailReal（与系统监视器同源）
        # 备用 hrStorageSize - hrStorageUsed
        # ====== 内存使用率 ======
        # SNMP 口径: (MemTotal - MemAvailReal) / MemTotal
        # MemAvailReal = MemFree (物理内存中完全未使用的部分)
        # 与系统监视器(含可回收cache) 不同，SNMP 数据会显著偏高，这是正常现象
        # 如需与系统监视器一致，请使用 SSH 巡检方式
        if 'MEM_USAGE' in codes:
            mem_total = snmp_get('1.3.6.1.4.1.2021.4.5.0')   # memTotalReal.0 (KB)
            mem_avail = snmp_get('1.3.6.1.4.1.2021.4.6.0')   # memAvailReal.0 (KB)

            memory_ok = False
            if mem_total and mem_avail:
                try:
                    total_kb = int(mem_total)
                    avail_kb = int(mem_avail)
                    used_kb = total_kb - avail_kb
                    pct = round(used_kb / total_kb * 100, 1) if total_kb > 0 else 0
                    status = 'pass' if pct < 80 else ('warning' if pct < 95 else 'fail')
                    results.append({
                        'check_item': '内存使用率', 'check_item_code': 'MEM_USAGE',
                        'status': status,
                        'result_value': f'{pct}% ({used_kb/1024:.0f}MB/{total_kb/1024:.0f}MB)',
                        'result_message': (
                            f'物理内存: 已分配{used_kb/1024:.0f}MB / 总计{total_kb/1024:.0f}MB ({pct}%)'
                        ),
                        'suggestion': '' if pct < 80 else '内存使用率偏高（SNMP口径：含buffers/cache），如系统监视器正常则无需干预'
                    })
                    memory_ok = True
                except Exception:
                    pass

            if not memory_ok:
                results.append({
                    'check_item': '内存使用率', 'check_item_code': 'MEM_USAGE',
                    'status': 'warning', 'result_value': '不支持',
                    'result_message': '该设备SNMP agent不支持内存SNMP OID（建议配置SSH巡检以获取准确数据）'
                })
        
        # ====== 磁盘使用率 (HOST-RESOURCES-MIB: hrStorage) ======
        if 'DISK_USAGE' in codes:
            # hrStorageType = 1.3.6.1.2.1.25.2.3.1.2
            # hrStorageFixedDisk = 1.3.6.1.2.1.25.2.1.4 (类型值，表示固定磁盘)
            storage_table = snmp_walk_table({
                'type': '1.3.6.1.2.1.25.2.3.1.2',
                'descr': '1.3.6.1.2.1.25.2.3.1.3',
                'units': '1.3.6.1.2.1.25.2.3.1.4',
                'size': '1.3.6.1.2.1.25.2.3.1.5',
                'used': '1.3.6.1.2.1.25.2.3.1.6',
            })
            
            disk_items = []
            for idx, row in storage_table.items():
                stype = row.get('type', '')
                # .4 = hrStorageFixedDisk, 也可能是 Network Disk .5
                if stype.endswith('.4') or stype.endswith('.5'):
                    try:
                        units = int(row.get('units', 1))
                        size = int(row.get('size', 0))
                        used = int(row.get('used', 0))
                        if size > 0:
                            pct = round(used / size * 100, 1)
                            total_mb = size * units / 1024 / 1024
                            used_mb = used * units / 1024 / 1024
                            free_mb = total_mb - used_mb
                            descr = row.get('descr', f'磁盘{idx}')
                            disk_items.append({
                                'name': descr,
                                'total_mb': round(total_mb, 1),
                                'used_mb': round(used_mb, 1),
                                'free_mb': round(free_mb, 1),
                                'pct': pct,
                                'status': 'pass' if pct < 80 else ('warning' if pct < 90 else 'fail')
                            })
                    except Exception:
                        pass
            
            if disk_items:
                max_pct = max(d['pct'] for d in disk_items)
                worst_status = 'pass' if max_pct < 80 else ('warning' if max_pct < 90 else 'fail')
                details = []
                warnings = []
                for d in disk_items:
                    details.append(f"{d['name']}: {d['pct']}% ({d['used_mb']:.0f}/{d['total_mb']:.0f}MB)")
                    if d['pct'] >= 80:
                        warnings.append(d['name'])
                results.append({
                    'check_item': '磁盘使用率', 'check_item_code': 'DISK_USAGE',
                    'status': worst_status,
                    'result_value': f'{len(disk_items)}个磁盘, 最高{max_pct}%',
                    'result_message': '\n'.join(details),
                    'suggestion': '磁盘空间不足: ' + ', '.join(warnings) if warnings else ''
                })
            else:
                # fallback: UCD-SNMP-MIB dskPercent
                dsk_pct = snmp_walk('1.3.6.1.4.1.2021.9.1.9')  # dskPercent
                if dsk_pct:
                    items = []
                    max_pct = 0
                    for i, pct in enumerate(dsk_pct):
                        try:
                            p = int(pct)
                            max_pct = max(max_pct, p)
                            items.append(f'分区{i+1}: {p}%')
                        except:
                            pass
                    status = 'pass' if max_pct < 80 else ('warning' if max_pct < 90 else 'fail')
                    results.append({
                        'check_item': '磁盘使用率', 'check_item_code': 'DISK_USAGE',
                        'status': status,
                        'result_value': f'{len(items)}个分区, 最高{max_pct}%',
                        'result_message': '\n'.join(items)
                    })
                else:
                    results.append({
                        'check_item': '磁盘使用率', 'check_item_code': 'DISK_USAGE',
                        'status': 'warning', 'result_value': '无数据',
                        'result_message': '设备不支持磁盘OID (hrStorageFixedDisk / dskPercent)'
                    })
        
        # ====== 接口状态 (IF-MIB) ======
        if 'INTERFACE_STATUS' in codes:
            if_descr = snmp_walk('1.3.6.1.2.1.2.2.1.2')    # ifDescr
            if_status = snmp_walk('1.3.6.1.2.1.2.2.1.8')   # ifOperStatus (1=up, 2=down)
            
            if if_descr and if_status:
                up_count = sum(1 for s in if_status if s == '1')
                down_count = sum(1 for s in if_status if s == '2')
                details = []
                for i in range(min(len(if_descr), len(if_status))):
                    status_text = 'UP' if if_status[i] == '1' else 'DOWN'
                    details.append(f'{if_descr[i]}: {status_text}')
                results.append({
                    'check_item': '接口状态', 'check_item_code': 'INTERFACE_STATUS',
                    'status': 'pass' if down_count == 0 else 'warning',
                    'result_value': str(down_count),  # 用 DOWN 数量作为阈值判断依据
                    'result_message': f'{up_count}UP / {down_count}DOWN\n' + '\n'.join(details[:15])
                })
            else:
                results.append({
                    'check_item': '接口状态', 'check_item_code': 'INTERFACE_STATUS',
                    'status': 'warning', 'result_value': '无数据',
                    'result_message': '无法获取接口信息'
                })
        
        # ====== 接口流量 (IF-MIB) ======
        if 'INTERFACE_TRAFFIC' in codes:
            if_descr = snmp_walk('1.3.6.1.2.1.2.2.1.2')       # ifDescr
            if_in_octets = snmp_walk('1.3.6.1.2.1.2.2.1.10')   # ifInOctets
            if_out_octets = snmp_walk('1.3.6.1.2.1.2.2.1.16')  # ifOutOctets
            
            if if_descr and if_in_octets:
                details = []
                for i in range(min(len(if_descr), 10)):
                    in_b = int(if_in_octets[i]) if i < len(if_in_octets) and if_in_octets[i].isdigit() else 0
                    out_b = int(if_out_octets[i]) if i < len(if_out_octets) and if_out_octets[i].isdigit() else 0
                    in_mb = in_b / 1024 / 1024
                    out_mb = out_b / 1024 / 1024
                    details.append(f'{if_descr[i]}: 入{in_mb:.0f}MB / 出{out_mb:.0f}MB')
                results.append({
                    'check_item': '接口流量', 'check_item_code': 'INTERFACE_TRAFFIC',
                    'status': 'pass', 'result_value': f'{min(len(if_descr), 10)}个接口',
                    'result_message': '\n'.join(details)
                })
            else:
                results.append({
                    'check_item': '接口流量', 'check_item_code': 'INTERFACE_TRAFFIC',
                    'status': 'warning', 'result_value': '无数据',
                    'result_message': '无法获取接口流量'
                })
        
        # ====== Trap告警 ======
        if 'TRAP_STATUS' in codes:
            results.append({
                'check_item': 'Trap告警', 'check_item_code': 'TRAP_STATUS',
                'status': 'pass', 'result_value': '需配置Trap接收',
                'result_message': 'Trap告警需要配置SNMP Trap Receiver接收'
            })
        
        return results
    
    def _execute_ping_checks(self, task, ip, check_items):
        """执行Ping巡检"""
        if not ip:
            return [{'check_item': '主机可达性', 'check_item_code': 'PING_REACHABLE',
                     'status': 'fail', 'result_value': '无IP', 'result_message': '资产未配置IP地址'}]
        
        codes = [item.get('code') if isinstance(item, dict) else item for item in check_items]
        results = []
        
        import subprocess
        r = subprocess.run(['ping', '-c', '4', '-W', '2', ip], capture_output=True, text=True, timeout=15)
        
        # 可达性
        if 'PING_REACHABLE' in codes or not codes:
            reachable = r.returncode == 0
            results.append({
                'check_item': '主机可达性', 'check_item_code': 'PING_REACHABLE',
                'status': 'pass' if reachable else 'fail',
                'result_value': '可达' if reachable else '不可达',
                'result_message': f'{ip} {"可达" if reachable else "不可达"}'
            })
        
        # 延迟
        if 'PING_LATENCY' in codes:
            latencies = []
            for line in r.stdout.split('\n'):
                if 'time=' in line:
                    try:
                        ms = float(line.split('time=')[1].split()[0])
                        latencies.append(ms)
                    except:
                        pass
            if latencies:
                avg = sum(latencies) / len(latencies)
                status = 'pass' if avg < 50 else ('warning' if avg < 200 else 'fail')
                results.append({
                    'check_item': '响应延迟', 'check_item_code': 'PING_LATENCY',
                    'status': status, 'result_value': f'{avg:.1f}ms',
                    'result_message': f'平均延迟: {avg:.1f}ms (共{len(latencies)}次)'
                })
            else:
                results.append({
                    'check_item': '响应延迟', 'check_item_code': 'PING_LATENCY',
                    'status': 'fail', 'result_value': '无数据', 'result_message': '无法解析延迟'
                })
        
        # 丢包率
        if 'PING_PACKET_LOSS' in codes:
            for line in r.stdout.split('\n'):
                if 'packet loss' in line:
                    try:
                        pct = float(line.split('%')[0].split()[-1])
                        status = 'pass' if pct == 0 else ('warning' if pct < 20 else 'fail')
                        results.append({
                            'check_item': '丢包率', 'check_item_code': 'PING_PACKET_LOSS',
                            'status': status, 'result_value': f'{pct}%',
                            'result_message': line.strip()
                        })
                    except:
                        results.append({
                            'check_item': '丢包率', 'check_item_code': 'PING_PACKET_LOSS',
                            'status': 'warning', 'result_value': '解析失败', 'result_message': line
                        })
                    break
        
        return results
    
    def _execute_port_checks(self, task, ip, check_items):
        """执行端口检测巡检"""
        import socket
        codes = [item.get('code') if isinstance(item, dict) else item for item in check_items]
        results = []
        
        if not ip:
            return [{'check_item': '端口检测', 'check_item_code': 'PORT_OPEN',
                     'status': 'fail', 'result_value': '无IP', 'result_message': '资产未配置IP地址'}]
        
        port = int(task.asset.port) if task.asset.port else 80
        
        if 'PORT_OPEN' in codes or 'PORT_RESPONSE' in codes or not codes:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                import time
                start = time.time()
                result = sock.connect_ex((ip, port))
                elapsed = (time.time() - start) * 1000
                sock.close()
                
                if 'PORT_OPEN' in codes or not codes:
                    results.append({
                        'check_item': f'端口{port}开放', 'check_item_code': 'PORT_OPEN',
                        'status': 'pass' if result == 0 else 'fail',
                        'result_value': '开放' if result == 0 else '关闭',
                        'result_message': f'{ip}:{port} {"开放" if result == 0 else "关闭"}'
                    })
                if 'PORT_RESPONSE' in codes:
                    results.append({
                        'check_item': f'端口{port}响应', 'check_item_code': 'PORT_RESPONSE',
                        'status': 'pass' if result == 0 else 'fail',
                        'result_value': f'{elapsed:.1f}ms',
                        'result_message': f'响应时间: {elapsed:.1f}ms'
                    })
            except Exception as e:
                results.append({
                    'check_item': f'端口{port}', 'check_item_code': 'PORT_OPEN',
                    'status': 'fail', 'result_value': '异常', 'result_message': str(e)
                })
        
        return results
    
    def _execute_db_checks(self, task, check_items):
        """执行数据库巡检"""
        from apps.inspection.db_inspector_v2 import run_inspection
        try:
            record = run_inspection(task.id, custom_sql=None)
            results = []
            for ir in InspectionResult.objects.filter(task=task):
                status_map = {'pass': 'pass', 'warning': 'warning', 'fail': 'fail', 'error': 'fail', 'skip': 'skip'}
                results.append({
                    'check_item': ir.check_item, 'check_item_code': ir.check_item_code,
                    'status': status_map.get(ir.status, 'fail'),
                    'result_value': ir.result_value or '', 'result_message': ir.result_message or ''
                })
            # db_inspector 已经创建了 record，删除由外层统一处理
            return results
        except Exception as e:
            return [{
                'check_item': '数据库巡检', 'check_item_code': 'DB_INSPECTION',
                'status': 'fail', 'result_value': '错误',
                'result_message': f'数据库巡检失败: {str(e)}'
            }]

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

            # 刷新 task 对象（run_inspection 内部已更新状态）
            task.refresh_from_db()

            # 同时写入 Inspection 表（兼容前端巡检记录列表）
            try:
                from django.utils import timezone as tz_now
                insp = Inspection.objects.create(
                    name=f'手工巡检-{task.asset.asset_name}',
                    description=f'手动执行巡检计划（任务ID: {task.id}）',
                    inspection_type=task.plan.protocol.upper() if task.plan else 'DATABASE',
                    customer=task.asset.customer,
                    asset=task.asset,
                    asset_type=task.asset.asset_type or '',
                    status='COMPLETED',
                    total_items=record.total_checks,
                    passed_items=record.pass_checks,
                    warning_items=record.warning_checks,
                    failed_items=record.fail_checks,
                    started_at=task.executed_time,
                    completed_at=tz_now.now(),
                    summary=record.summary
                )
                # 写入 InspectionItem
                from apps.inspection.models import InspectionItem
                for ir in InspectionResult.objects.filter(task=task):
                    try:
                        InspectionItem.objects.create(
                            inspection=insp,
                            item_code=ir.check_item_code or '',
                            item_name=ir.check_item or '',
                            category='database',
                            result=ir.status.upper() if ir.status else 'PASS',
                            severity=ir.get_severity_display() if hasattr(ir, 'get_severity_display') else 'INFO',
                            actual_value=str(ir.result_value or ''),
                            expected_value=str(ir.expected_value or ''),
                            message=str(ir.result_message or ''),
                            details={}
                        )
                    except Exception:
                        pass
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f'创建 Inspection 记录失败: {e}')

            # 根据巡检结果生成告警
            try:
                from apps.alerts.alert_generator import generate_inspection_alerts
                generate_inspection_alerts(task)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f'生成巡检告警失败: {e}')

            # 推送巡检结果到 ops-center
            try:
                from apps.dashboard.push_service import push_inspection_result
                push_inspection_result(task)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f'推送巡检结果失败: {e}')

            # 记录监控数据点
            try:
                from apps.dashboard.push_service import record_monitoring_data
                record_monitoring_data(task)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f'记录监控数据失败: {e}')

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


class InspectionViewSet(viewsets.ModelViewSet):
    """巡检执行记录视图集（读 Inspection 表，items 兼容 InspectionResult）"""
    
    queryset = Inspection.objects.select_related('customer', 'asset').prefetch_related('items').all().order_by('-created_at')
    serializer_class = InspectionSerializer
    filterset_fields = ['status', 'inspection_type']
    pagination_class = RestFrameworkPageNumberPagination
    
    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """批量删除巡检记录"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': '请提供要删除的ID列表'}, status=400)
        deleted, _ = Inspection.objects.filter(id__in=ids).delete()
        return Response({'deleted': deleted})
