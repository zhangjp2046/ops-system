"""
医院资产插件
基于藏书卫生院和太湖度假区医院示例开发的通用医院资产插件
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class HospitalAssetsPlugin:
    """医院资产插件主类"""
    
    def __init__(self, plugin_config: Dict[str, Any]):
        """
        初始化插件
        
        Args:
            plugin_config: 插件配置
        """
        self.plugin_config = plugin_config
        self.plugin_id = "hospital.assets"
        self.plugin_name = "医院资产插件"
        self.version = "1.0.0"
        
        logger.info(f"初始化医院资产插件 v{self.version}")
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            "plugin_id": self.plugin_id,
            "name": self.plugin_name,
            "version": self.version,
            "type": "asset",
            "description": "医院IT资产管理系统插件",
            "config_schema": self.get_config_schema(),
            "assets_schema": self.get_assets_schema()
        }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置schema"""
        return {
            "type": "object",
            "properties": {
                "hospital_code": {
                    "type": "string",
                    "title": "医院编码",
                    "description": "医院的唯一编码",
                    "required": True
                },
                "hospital_name": {
                    "type": "string",
                    "title": "医院名称",
                    "description": "医院的完整名称",
                    "required": True
                },
                "asset_prefix": {
                    "type": "string",
                    "title": "资产编号前缀",
                    "description": "资产编号的前缀",
                    "default": ""
                }
            }
        }
    
    def get_assets_schema(self) -> Dict[str, Any]:
        """获取资产schema"""
        # 从plugin.json文件加载schema
        try:
            with open(__file__.replace('__init__.py', 'plugin.json'), 'r', encoding='utf-8') as f:
                plugin_data = json.load(f)
                return plugin_data.get('assets_schema', {})
        except Exception as e:
            logger.error(f"加载资产schema失败: {e}")
            return {}
    
    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建医院客户
        
        Args:
            customer_data: 客户数据
            
        Returns:
            创建结果
        """
        try:
            # 验证必要字段
            required_fields = ['hospital_code', 'hospital_name']
            for field in required_fields:
                if field not in customer_data:
                    return {
                        "success": False,
                        "error": f"缺少必要字段: {field}"
                    }
            
            # 创建客户配置
            customer_config = {
                "customer_code": customer_data['hospital_code'],
                "customer_name": customer_data['hospital_name'],
                "customer_type": "HOSPITAL",
                "industry": "医疗",
                "config": {
                    "hospital_code": customer_data['hospital_code'],
                    "hospital_name": customer_data['hospital_name'],
                    "asset_prefix": customer_data.get('asset_prefix', ''),
                    "plugins": [self.plugin_id]
                },
                "plugins": [self.plugin_id]
            }
            
            logger.info(f"创建医院客户: {customer_data['hospital_name']}")
            return {
                "success": True,
                "data": customer_config
            }
            
        except Exception as e:
            logger.error(f"创建医院客户失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def import_assets(self, customer_id: int, assets_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        导入医院资产
        
        Args:
            customer_id: 客户ID
            assets_data: 资产数据列表
            
        Returns:
            导入结果
        """
        try:
            results = {
                "total": len(assets_data),
                "success": 0,
                "failed": 0,
                "errors": []
            }
            
            for asset in assets_data:
                try:
                    # 验证资产数据
                    validated_asset = self._validate_asset(asset)
                    if validated_asset:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"资产验证失败: {asset.get('asset_name', '未知')}")
                        
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(str(e))
            
            logger.info(f"导入医院资产完成: 成功{results['success']}, 失败{results['failed']}")
            return {
                "success": True,
                "data": results
            }
            
        except Exception as e:
            logger.error(f"导入医院资产失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_asset(self, asset_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """验证资产数据"""
        required_fields = ['asset_type', 'asset_name']
        
        for field in required_fields:
            if field not in asset_data:
                raise ValueError(f"缺少必要字段: {field}")
        
        # 根据资产类型验证字段
        asset_type = asset_data['asset_type']
        
        if asset_type == 'server':
            return self._validate_server_asset(asset_data)
        elif asset_type == 'network':
            return self._validate_network_asset(asset_data)
        elif asset_type == 'security':
            return self._validate_security_asset(asset_data)
        elif asset_type == 'storage':
            return self._validate_storage_asset(asset_data)
        elif asset_type == 'infrastructure':
            return self._validate_infrastructure_asset(asset_data)
        else:
            raise ValueError(f"不支持的资产类型: {asset_type}")
    
    def _validate_server_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证服务器资产"""
        validated = {
            "asset_type": "server",
            "asset_name": asset_data['asset_name'],
            "fields": {}
        }
        
        # 服务器类型
        server_type = asset_data.get('server_type', 'VIRTUAL_MACHINE')
        validated['fields']['server_type'] = server_type
        
        # 主机名
        if 'host_name' in asset_data:
            validated['fields']['host_name'] = asset_data['host_name']
        
        # IP地址
        if 'ip_address' in asset_data:
            validated['fields']['ip_address'] = asset_data['ip_address']
        
        # 操作系统
        if 'os_type' in asset_data:
            validated['fields']['os_type'] = asset_data['os_type']
        if 'os_name' in asset_data:
            validated['fields']['os_name'] = asset_data['os_name']
        
        # 硬件配置
        if 'cpu_cores' in asset_data:
            validated['fields']['cpu_cores'] = int(asset_data['cpu_cores'])
        if 'memory_gb' in asset_data:
            validated['fields']['memory_gb'] = int(asset_data['memory_gb'])
        if 'disk_gb' in asset_data:
            validated['fields']['disk_gb'] = int(asset_data['disk_gb'])
        
        # 管理信息
        if 'admin_account' in asset_data:
            validated['fields']['admin_account'] = asset_data['admin_account']
        
        return validated
    
    def _validate_network_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证网络设备资产"""
        validated = {
            "asset_type": "network",
            "asset_name": asset_data['asset_name'],
            "fields": {}
        }
        
        # 设备类型
        device_type = asset_data.get('device_type', 'SWITCH')
        validated['fields']['device_type'] = device_type
        
        # IP地址
        if 'ip_address' in asset_data:
            validated['fields']['ip_address'] = asset_data['ip_address']
        
        # 型号
        if 'model' in asset_data:
            validated['fields']['model'] = asset_data['model']
        
        # 固件版本
        if 'firmware_version' in asset_data:
            validated['fields']['firmware_version'] = asset_data['firmware_version']
        
        # 端口数量
        if 'port_count' in asset_data:
            validated['fields']['port_count'] = int(asset_data['port_count'])
        
        return validated
    
    def _validate_security_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证安全设备资产"""
        validated = {
            "asset_type": "security",
            "asset_name": asset_data['asset_name'],
            "fields": {}
        }
        
        # 安全设备类型
        security_type = asset_data.get('security_type', 'FIREWALL')
        validated['fields']['security_type'] = security_type
        
        # IP地址
        if 'ip_address' in asset_data:
            validated['fields']['ip_address'] = asset_data['ip_address']
        
        # 型号
        if 'model' in asset_data:
            validated['fields']['model'] = asset_data['model']
        
        # 许可证信息
        if 'license_key' in asset_data:
            validated['fields']['license_key'] = asset_data['license_key']
        if 'license_expiry' in asset_data:
            validated['fields']['license_expiry'] = asset_data['license_expiry']
        
        return validated
    
    def _validate_storage_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证存储设备资产"""
        validated = {
            "asset_type": "storage",
            "asset_name": asset_data['asset_name'],
            "fields": {}
        }
        
        # 存储类型
        storage_type = asset_data.get('storage_type', 'SAN')
        validated['fields']['storage_type'] = storage_type
        
        # IP地址
        if 'ip_address' in asset_data:
            validated['fields']['ip_address'] = asset_data['ip_address']
        
        # 容量信息
        if 'total_capacity_tb' in asset_data:
            validated['fields']['total_capacity_tb'] = float(asset_data['total_capacity_tb'])
        if 'used_capacity_tb' in asset_data:
            validated['fields']['used_capacity_tb'] = float(asset_data['used_capacity_tb'])
        
        # RAID级别
        if 'raid_level' in asset_data:
            validated['fields']['raid_level'] = asset_data['raid_level']
        
        return validated
    
    def _validate_infrastructure_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证基础设施资产"""
        validated = {
            "asset_type": "infrastructure",
            "asset_name": asset_data['asset_name'],
            "fields": {}
        }
        
        # 基础设施类型
        infra_type = asset_data.get('infra_type', 'UPS')
        validated['fields']['infra_type'] = infra_type
        
        # 容量信息
        if 'power_capacity_kva' in asset_data:
            validated['fields']['power_capacity_kva'] = float(asset_data['power_capacity_kva'])
        if 'cooling_capacity_kw' in asset_data:
            validated['fields']['cooling_capacity_kw'] = float(asset_data['cooling_capacity_kw'])
        if 'runtime_hours' in asset_data:
            validated['fields']['runtime_hours'] = float(asset_data['runtime_hours'])
        
        # 维护信息
        if 'last_maintenance_date' in asset_data:
            validated['fields']['last_maintenance_date'] = asset_data['last_maintenance_date']
        
        return validated
    
    def generate_asset_code(self, asset_type: str, sequence: int) -> str:
        """
        生成资产编号
        
        Args:
            asset_type: 资产类型
            sequence: 序列号
            
        Returns:
            资产编号
        """
        prefix = self.plugin_config.get('asset_prefix', '')
        
        # 资产类型前缀
        type_prefix = {
            'server': 'SVR',
            'network': 'NET',
            'security': 'SEC',
            'storage': 'STOR',
            'infrastructure': 'INFRA'
        }.get(asset_type, 'ASSET')
        
        return f"{prefix}{type_prefix}-{sequence:03d}"
    
    def create_monitoring_tasks(self, customer_id: int) -> List[Dict[str, Any]]:
        """
        创建默认监控任务
        
        Args:
            customer_id: 客户ID
            
        Returns:
            监控任务列表
        """
        tasks = [
            {
                "task_name": "服务器Ping监控",
                "task_type": "server_ping",
                "plugin_id": "hospital.assets",
                "config": {
                    "timeout": 5,
                    "retry_count": 3
                },
                "schedule": "*/5 * * * *",  # 每5分钟
                "alert_enabled": True
            },
            {
                "task_name": "服务器性能监控",
                "task_type": "server_performance",
                "plugin_id": "hospital.assets",
                "config": {
                    "check_cpu": True,
                    "check_memory": True,
                    "check_disk": True,
                    "warning_threshold": 80,
                    "critical_threshold": 90
                },
                "schedule": "*/10 * * * *",  # 每10分钟
                "alert_enabled": True
            }
        ]
        
        return tasks


# 插件工厂函数
def create_plugin(plugin_config: Dict[str, Any]) -> HospitalAssetsPlugin:
    """创建插件实例"""
    return HospitalAssetsPlugin(plugin_config)