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
from .check_items import get_check_items_by_protocol, get_all_protocols, get_protocol_categories


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
        protocol_filter = self.request.query_params.get('protocol')
        if protocol_filter:
            queryset = queryset.filter(protocol=protocol_filter)
        return queryset
    
    @action(detail=False, methods=['get'])
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
            return Response({
                'success': False,
                'message': '请指定协议类型'
            }, status=400)
        items = get_check_items_by_protocol(protocol)
        return Response({
            'success': True,
            'data': items
        })
    
    def perform_create(self, serializer):
        """创建时自动设置默认巡检项目"""
        instance = serializer.save()
        # 如果未指定巡检项目，使用该协议的全部默认项目
        if not instance.check_items:
            instance.check_items = get_check_items_by_protocol(instance.protocol)
            instance.save()
    
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
        
        # 保存结果
        for r in results:
            InspectionResult.objects.create(
                task=task, asset=task.asset,
                check_item=r['check_item'], check_item_code=r['check_item_code'],
                status=r['status'], result_value=r.get('result_value', ''),
                result_message=r.get('result_message', ''), suggestion=r.get('suggestion', '')
            )
        
        pass_count = sum(1 for r in results if r['status'] == 'pass')
        warning_count = sum(1 for r in results if r['status'] == 'warning')
        fail_count = sum(1 for r in results if r['status'] == 'fail')
        overall = 'fail' if fail_count > 0 else ('warning' if warning_count > 0 else 'pass')
        
        from django.utils import timezone as tz
        InspectionRecord.objects.create(
            task=task, asset=task.asset,
            total_checks=len(results),
            pass_checks=pass_count, warning_checks=warning_count, fail_checks=fail_count,
            status='completed', overall_status=overall,
            summary=f'{len(results)}项检查: {pass_count}通过, {warning_count}警告, {fail_count}异常',
            executor=request.user if request.user.is_authenticated else None,
            started_at=task.executed_time, completed_at=tz.now()
        )
        
        task.status = 'completed'
        task.save()
        
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
        community = task.asset.password or 'public'
        port = int(task.asset.port) if task.asset.port else 161
        
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
            v = snmp_get('1.3.6.1.2.1.1.3.0')  # sysUpTime
            results.append({
                'check_item': '运行时间', 'check_item_code': 'SYS_UPTIME',
                'status': 'pass' if v else 'warning',
                'result_value': (v or '无数据')[:100],
                'result_message': f'Uptime: {v}' if v else '无法获取'
            })
        
        # ====== CPU使用率 (UCD-SNMP-MIB: ssCpuUser + ssCpuSystem) ======
        if 'CPU_USAGE' in codes:
            cpu_user = snmp_get('1.3.6.1.4.1.2021.11.9.0')   # ssCpuUser.0
            cpu_sys = snmp_get('1.3.6.1.4.1.2021.11.10.0')    # ssCpuSystem.0
            cpu_idle = snmp_get('1.3.6.1.4.1.2021.11.11.0')   # ssCpuIdle.0
            
            try:
                idle = int(cpu_idle) if cpu_idle else None
                if idle is not None:
                    usage = 100 - idle
                    status = 'pass' if usage < 70 else ('warning' if usage < 90 else 'fail')
                    results.append({
                        'check_item': 'CPU使用率', 'check_item_code': 'CPU_USAGE',
                        'status': status, 'result_value': f'{usage}%',
                        'result_message': f'CPU用户:{cpu_user}%, 系统:{cpu_sys}%, 空闲:{cpu_idle}%',
                        'suggestion': '' if usage < 70 else 'CPU使用率偏高'
                    })
                else:
                    # fallback: hrProcessorLoad (HOST-RESOURCES-MIB)
                    loads = snmp_walk('1.3.6.1.2.1.25.3.3.1.2')  # hrProcessorLoad
                    if loads:
                        max_load = max(int(x) for x in loads if x.isdigit()) if any(x.isdigit() for x in loads) else 0
                        status = 'pass' if max_load < 70 else ('warning' if max_load < 90 else 'fail')
                        results.append({
                            'check_item': 'CPU使用率', 'check_item_code': 'CPU_USAGE',
                            'status': status, 'result_value': f'{max_load}% (最大核)',
                            'result_message': f'各核负载: {", ".join(loads[:8])}'
                        })
                    else:
                        results.append({
                            'check_item': 'CPU使用率', 'check_item_code': 'CPU_USAGE',
                            'status': 'warning', 'result_value': '无数据',
                            'result_message': '无法获取CPU使用率，设备可能不支持UCD-SNMP-MIB'
                        })
            except Exception as e:
                results.append({
                    'check_item': 'CPU使用率', 'check_item_code': 'CPU_USAGE',
                    'status': 'warning', 'result_value': '解析失败',
                    'result_message': f'cpu_user={cpu_user}, cpu_sys={cpu_sys}, cpu_idle={cpu_idle}, err={e}'
                })
        
        # ====== 内存使用率 (HOST-RESOURCES-MIB: hrStorage) ======
        if 'MEM_USAGE' in codes:
            # hrStorageType = 1.3.6.1.2.1.25.2.3.1.2, hrStorageDescr = .3, hrStorageSize = .5, hrStorageUsed = .6
            # hrStorageType = hrStorageRam(1.3.6.1.2.1.25.2.1.2) 表示物理内存
            storage_table = snmp_walk_table({
                'type': '1.3.6.1.2.1.25.2.3.1.2',
                'descr': '1.3.6.1.2.1.25.2.3.1.3',
                'units': '1.3.6.1.2.1.25.2.3.1.4',
                'size': '1.3.6.1.2.1.25.2.3.1.5',
                'used': '1.3.6.1.2.1.25.2.3.1.6',
            })
            
            # 找物理内存行 (hrStorageType 末尾为 .2 = hrStorageRam)
            ram_found = False
            for idx, row in storage_table.items():
                stype = row.get('type', '')
                if stype.endswith('.2') or 'Physical' in row.get('descr', '') or 'RAM' in row.get('descr', '').upper():
                    try:
                        units = int(row.get('units', 1))
                        size = int(row.get('size', 0))
                        used = int(row.get('used', 0))
                        total_kb = size * units / 1024
                        used_kb = used * units / 1024
                        pct = round(used / size * 100, 1) if size > 0 else 0
                        status = 'pass' if pct < 80 else ('warning' if pct < 95 else 'fail')
                        results.append({
                            'check_item': '内存使用率', 'check_item_code': 'MEM_USAGE',
                            'status': status,
                            'result_value': f'{pct}% ({used_kb/1024:.0f}MB/{total_kb/1024:.0f}MB)',
                            'result_message': f'{row.get("descr", "内存")}: 已用{used_kb/1024:.0f}MB / 总计{total_kb/1024:.0f}MB ({pct}%)',
                            'suggestion': '' if pct < 80 else '内存使用率偏高'
                        })
                        ram_found = True
                        break
                    except Exception as e:
                        results.append({
                            'check_item': '内存使用率', 'check_item_code': 'MEM_USAGE',
                            'status': 'warning', 'result_value': '解析失败',
                            'result_message': f'行数据: {row}, 错误: {e}'
                        })
                        ram_found = True
                        break
            
            if not ram_found:
                # fallback: UCD-SNMP-MIB memTotalReal / memAvailReal
                mem_total = snmp_get('1.3.6.1.4.1.2021.4.5.0')   # memTotalReal.0 (KB)
                mem_avail = snmp_get('1.3.6.1.4.1.2021.4.6.0')   # memAvailReal.0 (KB)
                try:
                    total = int(mem_total) if mem_total else 0
                    avail = int(mem_avail) if mem_avail else 0
                    used = total - avail
                    pct = round(used / total * 100, 1) if total > 0 else 0
                    if total > 0:
                        status = 'pass' if pct < 80 else ('warning' if pct < 95 else 'fail')
                        results.append({
                            'check_item': '内存使用率', 'check_item_code': 'MEM_USAGE',
                            'status': status,
                            'result_value': f'{pct}% ({used/1024:.0f}MB/{total/1024:.0f}MB)',
                            'result_message': f'总计:{total/1024:.0f}MB, 可用:{avail/1024:.0f}MB',
                            'suggestion': '' if pct < 80 else '内存使用率偏高'
                        })
                    else:
                        results.append({
                            'check_item': '内存使用率', 'check_item_code': 'MEM_USAGE',
                            'status': 'warning', 'result_value': '无数据',
                            'result_message': '设备不支持内存OID'
                        })
                except:
                    results.append({
                        'check_item': '内存使用率', 'check_item_code': 'MEM_USAGE',
                        'status': 'warning', 'result_value': '无数据',
                        'result_message': f'memTotal={mem_total}, memAvail={mem_avail}'
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
                    'result_value': f'{up_count}UP/{down_count}DOWN',
                    'result_message': '\n'.join(details[:15])
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
