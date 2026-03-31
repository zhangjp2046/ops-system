#!/usr/bin/env python3
"""
导入医院示例数据脚本
基于藏书卫生院和太湖度假区医院的资产清单
"""

import json
import sys
import os
from typing import Dict, List, Any

# 添加插件路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'plugins'))

from hospital_assets import create_plugin


def load_plugin_config() -> Dict[str, Any]:
    """加载插件配置"""
    return {
        "asset_prefix": "",
        "default_location": "机房"
    }


def get_cangshu_hospital_assets() -> List[Dict[str, Any]]:
    """获取藏书卫生院资产数据"""
    assets = []
    
    # 物理服务器 (3台)
    assets.extend([
        {
            "asset_type": "server",
            "asset_name": "EXSi103",
            "server_type": "PHYSICAL_SERVER",
            "host_name": "EXSi103",
            "ip_address": "192.168.100.103",
            "os_type": "ESXi",
            "os_name": "ESXi 6.0",
            "memory_gb": 256,
            "admin_account": "root",
            "importance_level": "HIGH"
        },
        {
            "asset_type": "server",
            "asset_name": "EXSi102",
            "server_type": "PHYSICAL_SERVER",
            "host_name": "EXSi102",
            "ip_address": "192.168.100.102",
            "os_type": "ESXi",
            "os_name": "ESXi 6.0",
            "memory_gb": 256,
            "admin_account": "root",
            "importance_level": "HIGH"
        },
        {
            "asset_type": "server",
            "asset_name": "EXSi101",
            "server_type": "PHYSICAL_SERVER",
            "host_name": "EXSi101",
            "ip_address": "192.168.100.101",
            "os_type": "ESXi",
            "os_name": "ESXi 6.0",
            "memory_gb": 256,
            "admin_account": "root",
            "importance_level": "HIGH"
        }
    ])
    
    # 虚拟机 (20台) - 只列出部分示例
    vm_assets = [
        {
            "asset_type": "server",
            "asset_name": "省lis对接服务器",
            "server_type": "VIRTUAL_MACHINE",
            "host_name": "省lis对接服务器",
            "ip_address": "192.168.100.249",
            "os_type": "Windows",
            "os_name": "windows_server_2012R2",
            "cpu_cores": 8,
            "memory_gb": 32,
            "admin_account": "administrator"
        },
        {
            "asset_type": "server",
            "asset_name": "HIS-New",
            "server_type": "VIRTUAL_MACHINE",
            "host_name": "HIS-New",
            "ip_address": "192.168.14.2",
            "os_type": "Windows",
            "os_name": "windows_server_2012R2",
            "cpu_cores": 14,
            "memory_gb": 82,
            "admin_account": "administrator",
            "importance_level": "CRITICAL"
        },
        {
            "asset_type": "server",
            "asset_name": "PACS_14.67",
            "server_type": "VIRTUAL_MACHINE",
            "host_name": "PACS_14.67",
            "ip_address": "192.168.14.67",
            "os_type": "Windows",
            "os_name": "windows_server_2008R2",
            "cpu_cores": 4,
            "memory_gb": 32,
            "admin_account": "administrator",
            "importance_level": "HIGH"
        }
    ]
    assets.extend(vm_assets)
    
    # 网络设备 (3台)
    assets.extend([
        {
            "asset_type": "network",
            "asset_name": "RG-S7808C-CangShu",
            "device_type": "SWITCH",
            "ip_address": "192.168.1.254",
            "model": "RG-S7808C",
            "admin_account": "admin",
            "importance_level": "CRITICAL"
        },
        {
            "asset_type": "network",
            "asset_name": "HUAWEI-S2170",
            "device_type": "SWITCH",
            "ip_address": "192.168.100.10",
            "model": "HUAWEI-S2170",
            "admin_account": "admin"
        },
        {
            "asset_type": "network",
            "asset_name": "HUAWEI-S1720",
            "device_type": "SWITCH",
            "ip_address": "192.168.1.249",
            "model": "HUAWEI-S1720",
            "admin_account": "admin"
        }
    ])
    
    # 安全设备 (5台)
    assets.extend([
        {
            "asset_type": "security",
            "asset_name": "网御防火墙",
            "security_type": "FIREWALL",
            "ip_address": "192.168.200.1",
            "model": "Power V6000-F3810E",
            "admin_account": "admin",
            "importance_level": "CRITICAL"
        },
        {
            "asset_type": "security",
            "asset_name": "LAS日志审计",
            "security_type": "AUDIT",
            "ip_address": "192.168.14.156",
            "model": "LAS-1000-V20",
            "admin_account": "admin"
        },
        {
            "asset_type": "security",
            "asset_name": "EDR终端防护",
            "security_type": "ANTIVIRUS",
            "ip_address": "192.168.14.153",
            "model": "EDR",
            "admin_account": "admin"
        }
    ])
    
    # 存储设备 (2台)
    assets.extend([
        {
            "asset_type": "storage",
            "asset_name": "宏杉存储",
            "storage_type": "SAN",
            "ip_address": "192.168.100.200",
            "total_capacity_tb": 44.397,
            "admin_account": "admin",
            "importance_level": "HIGH"
        },
        {
            "asset_type": "storage",
            "asset_name": "爱数备份一体机",
            "storage_type": "BACKUP",
            "ip_address": "192.168.14.238",
            "total_capacity_tb": 12.58,
            "admin_account": "admin"
        }
    ])
    
    return assets


def get_taihu_hospital_assets() -> List[Dict[str, Any]]:
    """获取太湖度假区医院资产数据"""
    assets = []
    
    # 物理服务器 - 深信服超融合 (3台)
    assets.extend([
        {
            "asset_type": "server",
            "asset_name": "深信服超融合-200.8",
            "server_type": "PHYSICAL_SERVER",
            "host_name": "深信服超融合",
            "ip_address": "172.16.200.8",
            "os_type": "Sangfor",
            "os_name": "深信服超融合",
            "admin_account": "Admin",
            "virtualization_platform": "深信服超融合",
            "importance_level": "CRITICAL"
        },
        {
            "asset_type": "server",
            "asset_name": "深信服超融合-200.9",
            "server_type": "PHYSICAL_SERVER",
            "host_name": "深信服超融合",
            "ip_address": "172.16.200.9",
            "os_type": "Sangfor",
            "os_name": "深信服超融合",
            "admin_account": "Admin",
            "virtualization_platform": "深信服超融合",
            "importance_level": "CRITICAL"
        },
        {
            "asset_type": "server",
            "asset_name": "深信服超融合-200.10",
            "server_type": "PHYSICAL_SERVER",
            "host_name": "深信服超融合",
            "ip_address": "172.16.200.10",
            "os_type": "Sangfor",
            "os_name": "深信服超融合",
            "admin_account": "Admin",
            "virtualization_platform": "深信服超融合",
            "importance_level": "CRITICAL"
        }
    ])
    
    # 虚拟机 - 关键业务系统 (部分示例)
    vm_assets = [
        {
            "asset_type": "server",
            "asset_name": "南格医护患信息系统",
            "server_type": "VIRTUAL_MACHINE",
            "host_name": "南格医护患信息系统",
            "ip_address": "172.16.200.40",
            "os_type": "Windows",
            "os_name": "windows_server_2016",
            "cpu_cores": 8,
            "memory_gb": 16,
            "admin_account": "administrator",
            "importance_level": "CRITICAL"
        },
        {
            "asset_type": "server",
            "asset_name": "his-new",
            "server_type": "VIRTUAL_MACHINE",
            "host_name": "his-new",
            "ip_address": "192.168.1.171",
            "os_type": "Windows",
            "os_name": "windows_server_2016",
            "cpu_cores": 8,
            "memory_gb": 64,
            "admin_account": "administrator",
            "importance_level": "CRITICAL"
        },
        {
            "asset_type": "server",
            "asset_name": "PACS",
            "server_type": "VIRTUAL_MACHINE",
            "host_name": "PACS",
            "ip_address": "192.168.1.11",
            "os_type": "Windows",
            "os_name": "windows_server_2016",
            "cpu_cores": 8,
            "memory_gb": 50,
            "admin_account": "administrator",
            "importance_level": "HIGH"
        }
    ]
    assets.extend(vm_assets)
    
    # 网络设备 (4台)
    assets.extend([
        {
            "asset_type": "network",
            "asset_name": "内网核心",
            "device_type": "SWITCH",
            "ip_address": "192.168.100.254",
            "model": "Ruijie-S7808C",
            "admin_account": "admin",
            "importance_level": "CRITICAL"
        },
        {
            "asset_type": "network",
            "asset_name": "外网核心",
            "device_type": "SWITCH",
            "ip_address": "192.168.201.254",
            "model": "Ruijie-S7805C",
            "admin_account": "admin",
            "importance_level": "CRITICAL"
        }
    ])
    
    # 安全设备 (部分示例)
    security_assets = [
        {
            "asset_type": "security",
            "asset_name": "外网防火墙",
            "security_type": "FIREWALL",
            "ip_address": "192.168.201.2",
            "model": "FW-100-BN150-PM",
            "admin_account": "admin",
            "importance_level": "CRITICAL"
        },
        {
            "asset_type": "security",
            "asset_name": "外网IPS",
            "security_type": "IPS",
            "ip_address": "192.168.201.3",
            "model": "AF-1000-B1600-N1",
            "admin_account": "admin"
        },
        {
            "asset_type": "security",
            "asset_name": "明御综合日志审计平台",
            "security_type": "AUDIT",
            "ip_address": "172.16.201.22",
            "model": "DAS-Logger",
            "admin_account": "admin"
        }
    ]
    assets.extend(security_assets)
    
    # 基础设施 (3台)
    assets.extend([
        {
            "asset_type": "infrastructure",
            "asset_name": "伊顿-PX200kVA",
            "infra_type": "UPS",
            "power_capacity_kva": 200,
            "runtime_hours": 2,
            "importance_level": "CRITICAL"
        },
        {
            "asset_type": "infrastructure",
            "asset_name": "艾默生-P2040",
            "infra_type": "AC",
            "cooling_capacity_kw": 40,
            "importance_level": "HIGH"
        },
        {
            "asset_type": "infrastructure",
            "asset_name": "大榕树-DRS1000",
            "infra_type": "MONITOR",
            "importance_level": "MEDIUM"
        }
    ])
    
    # 存储设备 (1台)
    assets.append({
        "asset_type": "storage",
        "asset_name": "科力锐灾备",
        "storage_type": "BACKUP",
        "admin_account": "admin"
    })
    
    return assets


def create_customer_data(hospital_code: str, hospital_name: str) -> Dict[str, Any]:
    """创建客户数据"""
    return {
        "hospital_code": hospital_code,
        "hospital_name": hospital_name,
        "asset_prefix": hospital_code[:2].upper() + "-"
    }


def main():
    """主函数"""
    print("=== 医院示例数据导入工具 ===")
    print()
    
    # 创建插件实例
    plugin_config = load_plugin_config()
    plugin = create_plugin(plugin_config)
    
    print("1. 插件信息:")
    plugin_info = plugin.get_plugin_info()
    print(f"   插件名称: {plugin_info['name']}")
    print(f"   插件版本: {plugin_info['version']}")
    print(f"   插件类型: {plugin_info['type']}")
    print()
    
    # 创建藏书卫生院客户
    print("2. 创建藏书卫生院客户:")
    cangshu_data = create_customer_data("CSWSY", "藏书卫生院")
    cangshu_result = plugin.create_customer(cangshu_data)
    
    if cangshu_result["success"]:
        print(f"   ✓ 创建成功: {cangshu_data['hospital_name']}")
        print(f"     客户编码: {cangshu_data['hospital_code']}")
        print(f"     资产前缀: {cangshu_data['asset_prefix']}")
        
        # 导入资产
        cangshu_assets = get_cangshu_hospital_assets()
        print(f"   ✓ 加载资产数据: {len(cangshu_assets)} 台设备")
        
        # 按类型统计
        asset_types = {}
        for asset in cangshu_assets:
            asset_type = asset['asset_type']
            asset_types[asset_type] = asset_types.get(asset_type, 0) + 1
        
        print("     资产类型分布:")
        for asset_type, count in asset_types.items():
            print(f"       {asset_type}: {count} 台")
    else:
        print(f"   ✗ 创建失败: {cangshu_result['error']}")
    
    print()
    
    # 创建太湖度假区医院客户
    print("3. 创建太湖度假区医院客户:")
    taihu_data = create_customer_data("THDQYY", "太湖度假区医院")
    taihu_result = plugin.create_customer(taihu_data)
    
    if taihu_result["success"]:
        print(f"   ✓ 创建成功: {taihu_data['hospital_name']}")
        print(f"     客户编码: {taihu_data['hospital_code']}")
        print(f"     资产前缀: {taihu_data['asset_prefix']}")
        
        # 导入资产
        taihu_assets = get_taihu_hospital_assets()
        print(f"   ✓ 加载资产数据: {len(taihu_assets)} 台设备")
        
        # 按类型统计
        asset_types = {}
        for asset in taihu_assets:
            asset_type = asset['asset_type']
            asset_types[asset_type] = asset_types.get(asset_type, 0) + 1
        
        print("     资产类型分布:")
        for asset_type, count in asset_types.items():
            print(f"       {asset_type}: {count} 台")
    else:
        print(f"   ✗ 创建失败: {taihu_result['error']}")
    
    print()
    
    # 总结
    print("4. 数据导入总结:")
    print(f"   藏书卫生院: {len(get_cangshu_hospital_assets())} 台设备")
    print(f"   太湖度假区医院: {len(get_taihu_hospital_assets())} 台设备")
    print(f"   总计: {len(get_cangshu_hospital_assets()) + len(get_taihu_hospital_assets())} 台设备")
    print()
    
    # 生成示例配置文件
    print("5. 生成示例配置文件:")
    config_example = {
        "customers": [
            {
                "customer_code": "CSWSY",
                "customer_name": "藏书卫生院",
                "config": cangshu_data
            },
            {
                "customer_code": "THDQYY",
                "customer_name": "太湖度假区医院",
                "config": taihu_data
            }
        ],
        "plugin_config": plugin_config
    }
    
    config_file = "hospital_examples_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_example, f, ensure_ascii=False, indent=2)
    
    print(f"   ✓ 配置文件已生成: {config_file}")
    print()
    
    print("=== 导入完成 ===")
    print()
    print("下一步操作:")
    print("1. 查看配置文件: cat hospital_examples_config.json")
    print("2. 启动运维系统后端")
    print("3. 通过API导入实际数据")
