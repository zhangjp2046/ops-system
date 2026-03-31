#!/usr/bin/env python3
"""
监控执行器
实现Ping检测、端口检测、SNMP检测等功能
"""

import os
import sys
import time
import socket
import subprocess
import json
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.monitoring.models import MonitoringTask, MonitoringResult, Alert, AlertRule
from apps.assets.models import Asset


class BaseExecutor:
    """监控执行器基类"""
    
    name = 'base'
    timeout = 5
    
    def __init__(self, task):
        self.task = task
        self.asset = task.asset
        self.config = task.config or {}
    
    def execute(self):
        """执行监控，返回结果"""
        raise NotImplementedError
    
    def get_field_value(self, field_code):
        """获取资产字段值"""
        try:
            from apps.assets.models import AssetData
            data = AssetData.objects.filter(
                asset=self.asset,
                field__field_code=field_code
            ).first()
            if data:
                return data.get_value()
        except:
            pass
        return None
    
    def _check_alert(self, status, response_time=None, uptime=None):
        """检查是否触发告警"""
        if status == 'success':
            return  # 成功不触发告警
        
        # 获取该资产类型的所有启用的告警规则
        rules = AlertRule.objects.filter(
            asset_type=self.asset.asset_type,
            is_enabled=True
        )
        
        for rule in rules:
            triggered = False
            trigger_value = None
            
            # 根据指标名称判断是否触发
            if rule.metric_name == 'response_time' and response_time:
                if self._compare_value(response_time, rule.condition, rule.threshold):
                    triggered = True
                    trigger_value = response_time
            elif rule.metric_name == 'uptime' and uptime is not None:
                if self._compare_value(uptime, rule.condition, rule.threshold):
                    triggered = True
                    trigger_value = uptime
            elif rule.metric_name == 'port_status' and status != 'success':
                triggered = True
                trigger_value = 0 if status == 'critical' else 1
            
            if triggered:
                # 创建告警
                Alert.objects.create(
                    title=f'{self.asset.asset_name} - {rule.name}',
                    message=f'{self.asset.asset_name} 监控异常: {status}',
                    severity=rule.severity,
                    status='open',
                    asset=self.asset,
                    alert_rule=rule,
                    trigger_value=trigger_value,
                    threshold=rule.threshold
                )
    
    def _compare_value(self, value, condition, threshold):
        """比较值是否满足条件"""
        try:
            value = float(value)
            threshold = float(threshold)
            
            if condition == 'gt':
                return value > threshold
            elif condition == 'lt':
                return value < threshold
            elif condition == 'eq':
                return value == threshold
            elif condition == 'ne':
                return value != threshold
            elif condition == 'gte':
                return value >= threshold
            elif condition == 'lte':
                return value <= threshold
        except:
            pass
        return False


class PingExecutor(BaseExecutor):
    """Ping检测执行器"""
    
    name = 'ping'
    
    def execute(self):
        """执行Ping检测"""
        # 获取IP地址
        ip_address = self.get_field_value('ip_address')
        if not ip_address:
            ip_address = self.asset.location  # 备用
        
        if not ip_address:
            return self._create_result(
                status='error',
                error_message='无法获取IP地址'
            )
        
        # 获取配置
        count = self.config.get('count', 4)
        timeout = self.config.get('timeout', self.timeout)
        
        try:
            # 执行Ping命令
            cmd = ['ping', '-c', str(count), '-W', str(timeout), ip_address]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout * count + 5
            )
            
            if result.returncode == 0:
                # 解析Ping结果
                output = result.stdout
                
                # 提取响应时间
                times = re.findall(r'time=(\d+\.?\d*)', output)
                avg_time = sum(float(t) for t in times) / len(times) if times else 0
                
                # 提取丢包率
                match = re.search(r'(\d+)% packet loss', output)
                packet_loss = int(match.group(1)) if match else 0
                
                # 计算可用率
                uptime = 100 - packet_loss
                
                return self._create_result(
                    status='success' if packet_loss == 0 else 'warning',
                    response_time=avg_time,
                    uptime=uptime,
                    raw_data={
                        'packets_sent': count,
                        'packets_received': count - int(count * packet_loss / 100),
                        'packet_loss': packet_loss
                    }
                )
            else:
                return self._create_result(
                    status='critical',
                    error_message=f'Ping失败: {result.stderr}'
                )
                
        except subprocess.TimeoutExpired:
            return self._create_result(
                status='timeout',
                error_message='Ping超时'
            )
        except Exception as e:
            return self._create_result(
                status='error',
                error_message=str(e)
            )
    
    def _create_result(self, status, response_time=None, uptime=None, error_message=None, raw_data=None):
        """创建监控结果"""
        result = MonitoringResult.objects.create(
            task=self.task,
            asset=self.asset,
            status=status,
            response_time=response_time,
            uptime=uptime if uptime is not None else 100 if status == 'success' else 0,
            error_message=error_message or '',
            raw_data=raw_data or {}
        )
        
        # 更新任务统计
        self.task.status = 'completed'
        self.task.last_run_time = datetime.now()
        
        if status == 'success':
            self.task.success_count += 1
            self.task.last_success_time = datetime.now()
        else:
            self.task.failure_count += 1
            self.task.last_failure_time = datetime.now()
        
        self.task.save()
        
        # 检查是否触发告警
        self._check_alert(status, response_time, uptime)
        
        return result


class PortExecutor(BaseExecutor):
    """端口检测执行器"""
    
    name = 'port'
    
    def execute(self):
        """执行端口检测"""
        # 获取IP地址和端口
        ip_address = self.get_field_value('ip_address')
        port = self.config.get('port')
        
        if not ip_address:
            ip_address = self.asset.location
        
        if not port:
            # 尝试从资产字段获取
            port = self.get_field_value('ssh_port') or self.get_field_value('mw_port') or 22
        
        timeout = self.config.get('timeout', self.timeout)
        
        try:
            # 创建socket连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            start_time = time.time()
            result = sock.connect_ex((ip_address, int(port)))
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            sock.close()
            
            if result == 0:
                return self._create_result(
                    status='success',
                    response_time=response_time,
                    port_check={'port': port, 'status': 'open'}
                )
            else:
                return self._create_result(
                    status='critical',
                    error_message=f'端口 {port} 连接失败',
                    port_check={'port': port, 'status': 'closed'}
                )
                
        except socket.timeout:
            return self._create_result(
                status='timeout',
                error_message=f'端口 {port} 连接超时'
            )
        except Exception as e:
            return self._create_result(
                status='error',
                error_message=str(e)
            )
    
    def _create_result(self, status, response_time=None, error_message=None, port_check=None):
        """创建监控结果"""
        result = MonitoringResult.objects.create(
            task=self.task,
            asset=self.asset,
            status=status,
            response_time=response_time,
            uptime=100 if status == 'success' else 0,
            error_message=error_message or '',
            port_check=port_check or {}
        )
        
        # 更新任务统计
        self.task.status = 'completed'
        self.task.last_run_time = datetime.now()
        
        if status == 'success':
            self.task.success_count += 1
            self.task.last_success_time = datetime.now()
        else:
            self.task.failure_count += 1
            self.task.last_failure_time = datetime.now()
        
        self.task.save()
        
        # 检查是否触发告警
        self._check_alert(status, response_time)
        
        return result


class HttpExecutor(BaseExecutor):
    """HTTP检测执行器"""
    
    name = 'http'
    
    def execute(self):
        """执行HTTP检测"""
        url = self.config.get('url')
        
        if not url:
            # 尝试从资产字段获取
            url = self.get_field_value('api_url') or self.get_field_value('app_url')
        
        if not url:
            return self._create_result(
                status='error',
                error_message='未配置检测URL'
            )
        
        timeout = self.config.get('timeout', self.timeout)
        
        try:
            start_time = time.time()
            
            # 使用curl进行检测
            cmd = ['curl', '-o', '/dev/null', '-s', '-w', '%{http_code}|%{time_total}', url]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            if result.returncode == 0:
                output = result.stdout.strip()
                parts = output.split('|')
                
                if len(parts) == 2:
                    status_code = parts[0]
                    curl_time = float(parts[1]) * 1000
                    
                    if status_code.startswith('2'):
                        return self._create_result(
                            status='success',
                            response_time=curl_time,
                            raw_data={'http_code': status_code}
                        )
                    else:
                        return self._create_result(
                            status='warning',
                            response_time=curl_time,
                            error_message=f'HTTP状态码: {status_code}',
                            raw_data={'http_code': status_code}
                        )
            
            return self._create_result(
                status='critical',
                error_message=f'HTTP请求失败: {result.stderr}'
            )
            
        except subprocess.TimeoutExpired:
            return self._create_result(
                status='timeout',
                error_message='HTTP请求超时'
            )
        except Exception as e:
            return self._create_result(
                status='error',
                error_message=str(e)
            )
    
    def _create_result(self, status, response_time=None, error_message=None, raw_data=None):
        """创建监控结果"""
        result = MonitoringResult.objects.create(
            task=self.task,
            asset=self.asset,
            status=status,
            response_time=response_time,
            uptime=100 if status == 'success' else 0,
            error_message=error_message or '',
            raw_data=raw_data or {}
        )
        
        # 更新任务统计
        self.task.status = 'completed'
        self.task.last_run_time = datetime.now()
        
        if status == 'success':
            self.task.success_count += 1
            self.task.last_success_time = datetime.now()
        else:
            self.task.failure_count += 1
            self.task.last_failure_time = datetime.now()
        
        self.task.save()
        
        # 检查是否触发告警
        self._check_alert(status, response_time)
        
        return result


class MonitoringExecutor:
    """监控执行器管理器"""
    
    _executors = {
        'ping': PingExecutor,
        'port': PortExecutor,
        'http': HttpExecutor,
        'snmp': None,  # SNMP执行器单独处理
        'snmp_perf': None,  # SNMP性能执行器单独处理
    }
    
    @classmethod
    def get_executor(cls, task):
        """获取任务对应的执行器"""
        # SNMP执行器单独处理
        if task.task_type == 'snmp':
            from .snmp_executor import SNMPExecutor
            return SNMPExecutor(task)
        elif task.task_type == 'snmp_perf':
            from .snmp_executor import SNMPPerformanceExecutor
            return SNMPPerformanceExecutor(task)
        
        executor_class = cls._executors.get(task.task_type)
        if executor_class:
            return executor_class(task)
        
        # 默认使用Ping执行器
        return PingExecutor(task)
    
    @classmethod
    def execute_task(cls, task_id):
        """执行指定的监控任务"""
        try:
            task = MonitoringTask.objects.get(id=task_id)
            executor = cls.get_executor(task)
            return executor.execute()
        except MonitoringTask.DoesNotExist:
            raise ValueError(f'监控任务 {task_id} 不存在')
    
    @classmethod
    def execute_all_enabled_tasks(cls, task_type=None):
        """执行所有启用的监控任务"""
        tasks = MonitoringTask.objects.filter(is_enabled=True)
        
        if task_type:
            tasks = tasks.filter(task_type=task_type)
        
        results = []
        for task in tasks:
            try:
                result = cls.execute_task(task.id)
                results.append(result)
            except Exception as e:
                print(f'执行任务 {task.id} 失败: {e}')
        
        return results
    
    @classmethod
    def execute_asset_tasks(cls, asset_id):
        """执行指定资产的所有监控任务"""
        tasks = MonitoringTask.objects.filter(
            asset_id=asset_id,
            is_enabled=True
        )
        
        results = []
        for task in tasks:
            try:
                result = cls.execute_task(task.id)
                results.append(result)
            except Exception as e:
                print(f'执行任务 {task.id} 失败: {e}')
        
        return results


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='监控执行器')
    parser.add_argument('--task-id', type=int, help='执行指定任务ID')
    parser.add_argument('--asset-id', type=int, help='执行指定资产的所有任务')
    parser.add_argument('--type', type=str, help='执行指定类型的所有任务')
    parser.add_argument('--all', action='store_true', help='执行所有启用的任务')
    
    args = parser.parse_args()
    
    if args.task_id:
        print(f'执行任务 {args.task_id}...')
        result = MonitoringExecutor.execute_task(args.task_id)
        print(f'结果: {result.status}')
    
    elif args.asset_id:
        print(f'执行资产 {args.asset_id} 的所有任务...')
        results = MonitoringExecutor.execute_asset_tasks(args.asset_id)
        print(f'完成 {len(results)} 个任务')
    
    elif args.type:
        print(f'执行类型 {args.type} 的所有任务...')
        results = MonitoringExecutor.execute_all_enabled_tasks(args.type)
        print(f'完成 {len(results)} 个任务')
    
    elif args.all:
        print('执行所有启用的任务...')
        results = MonitoringExecutor.execute_all_enabled_tasks()
        print(f'完成 {len(results)} 个任务')
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
