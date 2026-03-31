#!/usr/bin/env python3
"""
扩展资产类型初始化脚本
添加：数据库、中间件、API接口等资产类型
"""

import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.assets.models import AssetType, AssetField
from apps.customers.models import Customer

def init_extended_asset_types():
    """初始化扩展资产类型"""
    
    # 获取所有客户
    customers = Customer.objects.all()
    print(f"找到 {customers.count()} 个客户")
    
    # 定义新的资产类型
    new_types = [
        {
            'type_code': 'DATABASE',
            'type_name': '数据库',
            'icon': 'Database',
            'color': '#1890ff',
            'fields': [
                {'field_code': 'db_type', 'field_name': '数据库类型', 'field_label': '数据库类型', 'field_type': 'select', 'is_required': True,
                 'options': [
                     {'label': 'MySQL', 'value': 'mysql'},
                     {'label': 'PostgreSQL', 'value': 'postgresql'},
                     {'label': 'Oracle', 'value': 'oracle'},
                     {'label': 'SQL Server', 'value': 'sqlserver'},
                     {'label': 'MongoDB', 'value': 'mongodb'},
                     {'label': 'Redis', 'value': 'redis'},
                     {'label': 'Elasticsearch', 'value': 'elasticsearch'},
                     {'label': '其他', 'value': 'other'},
                 ]},
                {'field_code': 'db_version', 'field_name': '版本', 'field_label': '版本', 'field_type': 'string'},
                {'field_code': 'db_port', 'field_name': '端口', 'field_label': '端口', 'field_type': 'number', 'is_required': True},
                {'field_code': 'db_host', 'field_name': '主机地址', 'field_label': '主机地址', 'field_type': 'string', 'is_required': True},
                {'field_code': 'db_name', 'field_name': '数据库名', 'field_label': '数据库名', 'field_type': 'string'},
                {'field_code': 'db_username', 'field_name': '用户名', 'field_label': '用户名', 'field_type': 'string'},
                {'field_code': 'db_password', 'field_name': '密码', 'field_label': '密码', 'field_type': 'password'},
                {'field_code': 'db_charset', 'field_name': '字符集', 'field_label': '字符集', 'field_type': 'string'},
                {'field_code': 'max_connections', 'field_name': '最大连接数', 'field_label': '最大连接数', 'field_type': 'number'},
                {'field_code': 'current_connections', 'field_name': '当前连接数', 'field_label': '当前连接数', 'field_type': 'number'},
                {'field_code': 'data_size', 'field_name': '数据大小(G)', 'field_label': '数据大小(G)', 'field_type': 'number'},
                {'field_code': 'backup_enabled', 'field_name': '是否启用备份', 'field_label': '是否启用备份', 'field_type': 'select',
                 'options': [{'label': '是', 'value': 'yes'}, {'label': '否', 'value': 'no'}]},
                {'field_code': 'backup_schedule', 'field_name': '备份策略', 'field_label': '备份策略', 'field_type': 'string'},
            ]
        },
        {
            'type_code': 'MIDDLEWARE',
            'type_name': '中间件',
            'icon': 'Connection',
            'color': '#52c41a',
            'fields': [
                {'field_code': 'mw_type', 'field_name': '中间件类型', 'field_label': '中间件类型', 'field_type': 'select', 'is_required': True,
                 'options': [
                     {'label': 'Nginx', 'value': 'nginx'},
                     {'label': 'Apache', 'value': 'apache'},
                     {'label': 'Tomcat', 'value': 'tomcat'},
                     {'label': 'Jetty', 'value': 'jetty'},
                     {'label': 'WebLogic', 'value': 'weblogic'},
                     {'label': 'WebSphere', 'value': 'websphere'},
                     {'label': 'JBoss', 'value': 'jboss'},
                     {'label': '其他', 'value': 'other'},
                 ]},
                {'field_code': 'mw_version', 'field_name': '版本', 'field_label': '版本', 'field_type': 'string'},
                {'field_code': 'mw_port', 'field_name': '端口', 'field_label': '端口', 'field_type': 'number'},
                {'field_code': 'mw_host', 'field_name': '主机地址', 'field_label': '主机地址', 'field_type': 'string'},
                {'field_code': 'java_version', 'field_name': 'Java版本', 'field_label': 'Java版本', 'field_type': 'string'},
                {'field_code': 'jvm_xms', 'field_name': 'JVM初始内存', 'field_label': 'JVM初始内存', 'field_type': 'string'},
                {'field_code': 'jvm_xmx', 'field_name': 'JVM最大内存', 'field_label': 'JVM最大内存', 'field_type': 'string'},
                {'field_code': 'thread_pool_size', 'field_name': '线程池大小', 'field_label': '线程池大小', 'field_type': 'number'},
                {'field_code': 'request_count', 'field_name': '请求数/天', 'field_label': '请求数/天', 'field_type': 'number'},
                {'field_code': 'upstream_servers', 'field_name': '上游服务器', 'field_label': '上游服务器', 'field_type': 'textarea'},
            ]
        },
        {
            'type_code': 'API',
            'type_name': 'API接口',
            'icon': 'Share',
            'color': '#722ed1',
            'fields': [
                {'field_code': 'api_type', 'field_name': 'API类型', 'field_label': 'API类型', 'field_type': 'select', 'is_required': True,
                 'options': [
                     {'label': 'RESTful API', 'value': 'rest'},
                     {'label': 'GraphQL', 'value': 'graphql'},
                     {'label': 'gRPC', 'value': 'grpc'},
                     {'label': 'WebSocket', 'value': 'websocket'},
                     {'label': 'SOAP', 'value': 'soap'},
                     {'label': '其他', 'value': 'other'},
                 ]},
                {'field_code': 'api_version', 'field_name': 'API版本', 'field_label': 'API版本', 'field_type': 'string'},
                {'field_code': 'api_url', 'field_name': 'API地址', 'field_label': 'API地址', 'field_type': 'string', 'is_required': True},
                {'field_code': 'api_method', 'field_name': '请求方法', 'field_label': '请求方法', 'field_type': 'select',
                 'options': [
                     {'label': 'GET', 'value': 'GET'},
                     {'label': 'POST', 'value': 'POST'},
                     {'label': 'PUT', 'value': 'PUT'},
                     {'label': 'DELETE', 'value': 'DELETE'},
                     {'label': 'PATCH', 'value': 'PATCH'},
                 ]},
                {'field_code': 'api_status', 'field_name': 'API状态', 'field_label': 'API状态', 'field_type': 'select',
                 'options': [
                     {'label': '正常', 'value': 'healthy'},
                     {'label': '异常', 'value': 'unhealthy'},
                     {'label': '维护中', 'value': 'maintenance'},
                     {'label': '已下线', 'value': 'deprecated'},
                 ]},
                {'field_code': 'response_time', 'field_name': '响应时间(ms)', 'field_label': '响应时间(ms)', 'field_type': 'number'},
                {'field_code': 'qps', 'field_name': 'QPS', 'field_label': 'QPS', 'field_type': 'number'},
                {'field_code': 'auth_type', 'field_name': '认证方式', 'field_label': '认证方式', 'field_type': 'select',
                 'options': [
                     {'label': '无需认证', 'value': 'none'},
                     {'label': 'API Key', 'value': 'apikey'},
                     {'label': 'OAuth2', 'value': 'oauth2'},
                     {'label': 'JWT', 'value': 'jwt'},
                     {'label': 'Basic Auth', 'value': 'basic'},
                 ]},
                {'field_code': 'owner_service', 'field_name': '所属服务', 'field_label': '所属服务', 'field_type': 'string'},
                {'field_code': 'documentation', 'field_name': 'API文档', 'field_label': 'API文档', 'field_type': 'string'},
            ]
        },
        {
            'type_code': 'CLOUD_SERVICE',
            'type_name': '云服务',
            'icon': 'Cloud',
            'color': '#13c2c2',
            'fields': [
                {'field_code': 'cloud_provider', 'field_name': '云服务商', 'field_label': '云服务商', 'field_type': 'select', 'is_required': True,
                 'options': [
                     {'label': '阿里云', 'value': 'aliyun'},
                     {'label': '腾讯云', 'value': 'tencent'},
                     {'label': '华为云', 'value': 'huawei'},
                     {'label': 'AWS', 'value': 'aws'},
                     {'label': 'Azure', 'value': 'azure'},
                     {'label': '私有云', 'value': 'private'},
                 ]},
                {'field_code': 'service_type', 'field_name': '服务类型', 'field_label': '服务类型', 'field_type': 'select',
                 'options': [
                     {'label': 'ECS', 'value': 'ecs'},
                     {'label': 'RDS', 'value': 'rds'},
                     {'label': 'OSS', 'value': 'oss'},
                     {'label': 'SLB', 'value': 'slb'},
                     {'label': 'Redis', 'value': 'redis'},
                     {'label': '其他', 'value': 'other'},
                 ]},
                {'field_code': 'region', 'field_name': '地域', 'field_label': '地域', 'field_type': 'string'},
                {'field_code': 'instance_id', 'field_name': '实例ID', 'field_label': '实例ID', 'field_type': 'string'},
                {'field_code': 'specification', 'field_name': '规格', 'field_label': '规格', 'field_type': 'string'},
                {'field_code': 'monthly_cost', 'field_name': '月费用(元)', 'field_label': '月费用(元)', 'field_type': 'number'},
            ]
        },
        {
            'type_code': 'APPLICATION',
            'type_name': '应用程序',
            'icon': 'App',
            'color': '#fa8c16',
            'fields': [
                {'field_code': 'app_type', 'field_name': '应用类型', 'field_label': '应用类型', 'field_type': 'select',
                 'options': [
                     {'label': 'Web应用', 'value': 'web'},
                     {'label': '桌面应用', 'value': 'desktop'},
                     {'label': '移动应用', 'value': 'mobile'},
                     {'label': '后台服务', 'value': 'service'},
                     {'label': '定时任务', 'value': 'cronjob'},
                     {'label': '其他', 'value': 'other'},
                 ]},
                {'field_code': 'app_language', 'field_name': '开发语言', 'field_label': '开发语言', 'field_type': 'select',
                 'options': [
                     {'label': 'Java', 'value': 'java'},
                     {'label': 'Python', 'value': 'python'},
                     {'label': 'Node.js', 'value': 'nodejs'},
                     {'label': 'Go', 'value': 'go'},
                     {'label': 'PHP', 'value': 'php'},
                     {'label': 'C#', 'value': 'csharp'},
                     {'label': '其他', 'value': 'other'},
                 ]},
                {'field_code': 'app_framework', 'field_name': '框架', 'field_label': '框架', 'field_type': 'string'},
                {'field_code': 'app_version', 'field_name': '版本', 'field_label': '版本', 'field_type': 'string'},
                {'field_code': 'app_port', 'field_name': '端口', 'field_label': '端口', 'field_type': 'number'},
                {'field_code': 'app_url', 'field_name': '访问地址', 'field_label': '访问地址', 'field_type': 'string'},
                {'field_code': 'git_repository', 'field_name': 'Git仓库', 'field_label': 'Git仓库', 'field_type': 'string'},
                {'field_code': 'deployment_env', 'field_name': '部署环境', 'field_label': '部署环境', 'field_type': 'select',
                 'options': [
                     {'label': '开发环境', 'value': 'dev'},
                     {'label': '测试环境', 'value': 'test'},
                     {'label': '预发布环境', 'value': 'staging'},
                     {'label': '生产环境', 'value': 'prod'},
                 ]},
            ]
        },
    ]
    
    # 为每个客户创建新的资产类型
    for customer in customers:
        print(f"\n处理客户: {customer.customer_name}")
        
        for idx, type_data in enumerate(new_types):
            # 检查是否已存在
            exists = AssetType.objects.filter(
                customer=customer,
                type_code=type_data['type_code']
            ).exists()
            
            if exists:
                print(f"  - {type_data['type_name']} 已存在，跳过")
                continue
            
            # 创建资产类型
            asset_type = AssetType.objects.create(
                customer=customer,
                type_code=type_data['type_code'],
                type_name=type_data['type_name'],
                icon=type_data['icon'],
                color=type_data['color'],
                sort_order=10 + idx,  # 接在原有类型之后
                is_system=False,
                is_active=True
            )
            print(f"  + 创建资产类型: {type_data['type_name']} (ID: {asset_type.id})")
            
            # 创建字段
            for field_idx, field_data in enumerate(type_data.get('fields', [])):
                # 处理options（如果是列表）
                options = field_data.get('options', [])
                if options:
                    options = options  # 保持列表格式
                
                AssetField.objects.create(
                    asset_type=asset_type,
                    field_code=field_data['field_code'],
                    field_name=field_data['field_name'],
                    field_label=field_data['field_label'],
                    field_type=field_data['field_type'],
                    is_required=field_data.get('is_required', False),
                    is_unique=field_data.get('is_unique', False),
                    is_searchable=True,
                    is_filterable=True,
                    sort_order=field_idx,
                    options=options,
                    placeholder=field_data.get('placeholder', ''),
                    default_value=field_data.get('default_value', '')
                )
                print(f"      + 字段: {field_data['field_label']}")
    
    print("\n=== 初始化完成 ===")

if __name__ == '__main__':
    init_extended_asset_types()
