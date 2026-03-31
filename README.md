# 通用运维管理系统

基于Vue + Django的通用运维管理系统，支持多客户、多类型的IT资产管理。

## 功能特性

- ✅ **多客户支持**: 通过插件系统支持不同行业客户的资产管理
- ✅ **资产管理**: 支持服务器、网络设备、安全设备、存储设备等多种资产类型
- ✅ **扩展资产类型**: 支持数据库、中间件、API接口、云服务、应用程序
- ✅ **动态字段**: 支持根据资产类型自定义字段
- ✅ **增删改查**: 完整的资产管理CRUD功能
- ✅ **用户权限**: 基于角色的权限控制系统
- ✅ **插件系统**: 可扩展的插件架构

## 资产分类

### 基础资产类型
1. **服务器** (SERVER) - 服务器设备
2. **网络设备** (NETWORK) - 路由器、交换机等
3. **安全设备** (SECURITY) - 防火墙、IDS/IPS等
4. **存储设备** (STORAGE) - 磁盘阵列、NAS等
5. **基础设施** (INFRA) - 机房、机柜等

### 扩展资产类型（运维专用）
6. **数据库** (DATABASE) - MySQL、PostgreSQL、Oracle、MongoDB、Redis等
   - 运维字段：类型、版本、端口、主机地址、数据库名、连接数、数据大小、备份策略等
7. **中间件** (MIDDLEWARE) - Nginx、Apache、Tomcat、WebLogic等
   - 运维字段：类型、版本、端口、JVM配置、线程池、请求数等
8. **API接口** (API) - RESTful、GraphQL、gRPC等
   - 运维字段：类型、版本、地址、状态、响应时间、QPS、认证方式等
9. **云服务** (CLOUD_SERVICE) - ECS、RDS、OSS、SLB等
   - 运维字段：云服务商、服务类型、地域、规格、费用等
10. **应用程序** (APPLICATION) - Web应用、后台服务、定时任务等
    - 运维字段：类型、语言、框架、版本、Git仓库、部署环境等

## 技术栈

### 后端
- Django 4.2 + Django REST Framework
- MySQL 8.0
- Session认证

### 前端
- Vue.js 3 + Composition API
- Element Plus
- Pinia 状态管理
- Vue Router

## 项目结构

```
ops-system/
├── backend/                 # Django后端
│   ├── apps/              # Django应用
│   │   ├── assets/        # 资产管理
│   │   ├── customers/      # 客户管理
│   │   ├── users/          # 用户管理
│   │   ├── monitoring/     # 监控管理(预留)
│   │   └── alerts/         # 告警管理(预留)
│   ├── config/            # 配置文件
│   ├── scripts/           # 脚本文件
│   └── requirements.txt    # Python依赖
│
├── frontend/              # Vue前端
│   ├── src/
│   │   ├── api/          # API调用
│   │   ├── views/        # 页面组件
│   │   ├── components/   # 通用组件
│   │   ├── router/      # 路由配置
│   │   ├── store/       # 状态管理
│   │   └── utils/       # 工具函数
│   └── package.json
│
├── plugins/               # 插件目录
│   └── hospital_assets/  # 医院资产插件
│
├── docs/                  # 文档
│
└── scripts/              # 脚本
    └── init_extended_asset_types.py  # 扩展资产类型初始化
```

## 快速开始

### 1. 安装依赖

```bash
# 克隆项目
cd /home/zhang/botcode/ops-system

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install
```

### 2. 配置数据库

编辑 `backend/config/settings.py` 中的数据库配置:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'ops_system',
        'USER': 'root',
        'PASSWORD': 'zjp2046',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 3. 初始化数据库

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser
```

### 4. 初始化扩展资产类型

```bash
cd backend
python manage.py shell < ../scripts/init_extended_asset_types.py
```

### 5. 启动服务

```bash
# 启动后端
python manage.py runserver 0.0.0.0:8000

# 启动前端 (新终端)
cd frontend
npm run dev
```

### 6. 访问系统

- 前端: http://localhost:3000
- 后端API: http://localhost:8000/api
- API文档: http://localhost:8000/swagger/

默认账号: admin / admin123

## 示例数据

系统初始化后会自动创建以下示例数据：

### 客户
- 藏书卫生院
- 太湖度假区医院

### 资产类型（每客户10种）
- 服务器、网络设备、安全设备、存储设备、基础设施
- 数据库、中间件、API接口、云服务、应用程序

### 测试资产
- 服务器: SRV-001 (数据库服务器)
- 数据库: DB-001 (HIS系统MySQL数据库)
- 中间件: MW-001 (Web服务器Nginx)
- API接口: API-001 (患者信息查询API)

## 数据库运维功能

### 数据库监控字段
- 数据库类型 (MySQL/PostgreSQL/Oracle/MongoDB/Redis等)
- 版本、端口、主机地址
- 连接数 (当前/最大)
- 数据大小
- 备份策略

### 中间件监控字段
- 中间件类型 (Nginx/Apache/Tomcat/WebLogic等)
- JVM配置 (初始/最大内存)
- 线程池大小
- 请求统计

### API接口监控字段
- API状态 (正常/异常/维护/下线)
- 响应时间、QPS
- 认证方式
- 所属服务

## 下一步开发

- [x] 监控功能开发 (Ping监控、性能采集) ✅
- [x] 告警功能开发 (阈值告警、通知) ✅
- [ ] 巡检功能开发 (定期巡检任务)
- [ ] 报表功能开发 (统计报表)
- [ ] 数据导入功能 (Excel/CSV导入)

## 监控功能

### 监控类型
- **Ping检测** - 检测服务器、网络设备是否在线
- **端口检测** - 检测服务端口是否可达
- **SNMP检测** - 通过SNMP协议采集设备信息
- **HTTP检测** - 检测Web服务是否正常
- **SSL证书检测** - 检测SSL证书有效期
- **性能采集** - CPU、内存、磁盘、网络等性能指标

### 监控任务
- 支持按资产创建监控任务
- 可配置执行间隔（1分钟~1天）
- 支持手动执行和自动执行
- 记录执行结果和统计

### 告警规则
- 支持多种指标监控（CPU、内存、端口等）
- 可配置阈值和条件
- 支持多种通知渠道（邮件、短信等）
- 告警状态管理（未处理、已确认、已解决、已关闭）

### API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/monitoring/tasks/` | GET/POST | 监控任务列表/创建 |
| `/api/monitoring/tasks/{id}/` | GET/PUT/DELETE | 监控任务详情 |
| `/api/monitoring/tasks/{id}/execute/` | POST | 手动执行任务 |
| `/api/monitoring/results/` | GET | 监控结果列表 |
| `/api/monitoring/rules/` | GET/POST | 告警规则列表/创建 |
| `/api/monitoring/alerts/` | GET | 告警记录列表 |
| `/api/monitoring/alerts/{id}/acknowledge/` | POST | 确认告警 |
| `/api/monitoring/alerts/{id}/resolve/` | POST | 解决告警 |

## 许可证

MIT License
---

## SNMP监控功能 (2026-03-28)

### 功能概述

系统支持SNMP v1/v2c协议监控，可对网络设备、服务器、存储设备等进行 SNMP 监控。

### 实现方式

| 方式 | 说明 |
|------|------|
| 系统snmp工具 | 如果系统安装了snmpwalk/snmpget，优先使用 |
| Python原生SNMP | 使用socket发送SNMP请求，不依赖外部库 |
| 模拟数据 | 网络不可达时使用，用于测试演示 |

### SNMP OID支持

| OID | 说明 |
|-----|------|
| 1.3.6.1.2.1.1.1.0 | 系统描述 (sysDescr) |
| 1.3.6.1.2.1.1.3.0 | 系统运行时间 (sysUpTime) |
| 1.3.6.1.2.1.1.5.0 | 系统名称 (sysName) |
| 1.3.6.1.2.1.2.1.0 | 接口数量 (ifNumber) |
| 1.3.6.1.2.1.2.2.1.8 | 接口状态 (ifStatus) |
| 1.3.6.1.2.1.2.2.1.2 | 接口描述 (ifDescr) |
| 1.3.6.1.2.1.2.2.1.5 | 接口速度 (ifSpeed) |

### 监控任务类型

| 类型 | 代码 | 说明 |
|------|------|------|
| SNMP基础监控 | snmp | 获取设备系统信息、接口状态 |
| SNMP性能监控 | snmp_perf | 获取CPU、内存等性能数据 |

### 配置参数

在监控任务的`config`字段中配置：

```json
{
    "snmp_version": "v2c",      // SNMP版本: v1, v2c
    "snmp_port": 161,            // SNMP端口
    "snmp_community": "public",  // 社区名
    "snmp_timeout": 5,           // 超时时间(秒)
    "snmp_retries": 3            // 重试次数
}
```

### 文件列表

| 文件 | 说明 |
|------|------|
| `apps/monitoring/snmp_client.py` | 原生Python SNMP客户端 |
| `apps/monitoring/snmp_executor.py` | SNMP监控执行器 |

### 已知问题

1. **网络超时**: 当目标设备不可达时，会自动降级到模拟数据模式
2. **需要真实设备**: 要获得真实的SNMP数据，需要有可访问的SNMP设备
3. **pysnmp库**: pysnmp 7.x版本API有较大变化，未使用

