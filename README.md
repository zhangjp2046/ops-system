# ops-system 通用运维管理系统

> **租户端** — 多客户、多类型的 IT 资产管理与运维监控平台

ops-system 是一个面向 MSP（托管服务提供商）场景的轻量级运维管理系统。作为 **租户端（Agent）**，它部署在各租户侧，负责资产录入、监控采集、告警生成、定时巡检等工作，并通过 API 将数据上报至 **ops-center（中心端）** 进行多租户聚合展示与通知分发。

---

## 功能特性

### ✅ 已实现模块

| 模块 | 说明 |
|------|------|
| **资产管理 (assets)** | 多类型资产 CRUD，支持服务器、网络设备、安全设备、存储等基础类型及数据库、中间件等扩展类型；动态自定义字段；资产状态流转（领用/转移/维修/报废/借用） |
| **客户管理 (customers)** | 多客户（租户）管理，支持插件扩展客户自定义资产类型；API-Key 认证 |
| **用户管理 (users)** | 用户/角色/权限管理，Session 认证 + API-Key 双模式 |
| **监控中心 (monitoring)** | 多协议监控采集：Ping、端口、SNMP(v1/v2c)、SSH、HTTP/HTTPS、SSL 证书、MySQL、MSSQL、Oracle、PostgreSQL；手动/定时执行；采集测试 |
| **告警管理 (alerts)** | 阈值规则配置（按协议+检查项）；告警状态流转（未处理→已确认→已解决→已关闭）；自动推送至 ops-center |
| **巡检管理 (inspection)** | 巡检计划/任务/结果管理；支持模板；支持多种协议（SNMP/SSH/数据库等）；合规检查项；数据库专项巡检 |
| **驾驶舱 (dashboard)** | 资产统计、监控概览、告警概览、ECharts 图表展示 |
| **自动发现 (discovery)** | 网络扫描自动发现资产；网络拓扑可视化 |
| **定时调度 (scheduler_v2)** | Cron 式定时任务调度，支持监控/巡检等周期性任务 |
| **技能模块 (skills)** | 可插拔的任务技能引擎，支持 ops/dashboard/inspection/push 等技能 |
| **系统设置 (system)** | 系统级配置项管理 |
| **数据推送 (dashboard.push_service)** | 向 ops-center 推送心跳、告警、巡检结果、资产状态、监控数据等 |
| **知识包管理 (knowledge_updater)** | 从 ops-center 同步知识包（检查项模板），支持版本管理 |

### 🔜 规划中

| 模块 | 说明 |
|------|------|
| **工单管理 (workorder)** | 工单创建/流转/处理（骨架预留） |
| **实验室库存 (lab_inventory)** | 与 labrms 共享的实验室库存模块 |

---

## 资产类型

### 基础资产类型

| 类型 | 标识 | 说明 |
|------|------|------|
| 服务器 | `SERVER` | 物理服务器、虚拟机 |
| 网络设备 | `NETWORK` | 路由器、交换机、防火墙 |
| 安全设备 | `SECURITY` | 防火墙、IDS/IPS、WAF |
| 存储设备 | `STORAGE` | 磁盘阵列、NAS、SAN |
| 基础设施 | `INFRA` | 机房、机柜、UPS |

### 扩展资产类型（运维专项）

| 类型 | 标识 | 运维字段 |
|------|------|----------|
| 数据库 | `DATABASE` | 类型/版本/端口/主机/连接数/数据大小/备份策略 |
| 中间件 | `MIDDLEWARE` | 类型/版本/端口/JVM配置/线程池/请求数 |
| API 接口 | `API` | 类型/版本/地址/状态/响应时间/QPS/认证方式 |
| 云服务 | `CLOUD_SERVICE` | 云服务商/服务类型/地域/规格/费用 |
| 应用程序 | `APPLICATION` | 类型/语言/框架/版本/Git仓库/部署环境 |

### 插件扩展

通过 `plugins/` 目录下的自定义插件，可为特定行业客户扩展资产类型（如 `hospital_assets` 医院资产插件）。

---

## 技术栈

### 后端

| 组件 | 技术 |
|------|------|
| 框架 | Django 4.2 + Django REST Framework |
| 运行 | Gunicorn / `manage.py runserver` |
| 数据库 | MySQL 8.0（Docker: `mysql-ops`） |
| 认证 | Session + API-Key 双模式 |
| 端口 | **8002** |
| 其他 | Python 3.12, requests, pysnmp, croniter |

### 前端

| 组件 | 技术 |
|------|------|
| 框架 | Vue 3 + Composition API |
| 构建 | Vite 4 |
| UI | Element Plus |
| 状态管理 | Pinia |
| 图表 | ECharts |
| 路由 | Vue Router 4 |
| 端口 | **3099** (dev) |

---

## 项目结构

```
ops-system/
├── backend/                          # Django 后端
│   ├── apps/
│   │   ├── assets/                   # 资产管理
│   │   ├── customers/                # 客户管理（多租户+插件）
│   │   ├── users/                    # 用户/角色/权限
│   │   ├── monitoring/               # 监控采集（Ping/Port/SNMP/HTTP/SSL等）
│   │   ├── alerts/                   # 告警管理（阈值规则/状态流转）
│   │   ├── inspection/               # 巡检管理（计划/任务/结果）
│   │   ├── dashboard/                # 驾驶舱 + 推送服务（push_service）
│   │   │   ├── push_service.py       # → 推送数据至 ops-center
│   │   │   └── knowledge_updater.py  # → 从 ops-center 同步知识包
│   │   ├── discovery/                # 自动发现
│   │   ├── scheduler_v2/             # 定时任务调度
│   │   ├── skills/                   # 技能模块
│   │   ├── system/                   # 系统设置
│   │   ├── workorder/                # 工单管理（预留）
│   │   └── lab_inventory/            # 实验室库存（与 labrms 共享）
│   ├── config/                       # Django 配置
│   │   ├── settings.py
│   │   └── urls.py                   # 全局 URL 路由
│   ├── scripts/                      # 运维脚本
│   └── requirements.txt
│
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── api/                      # API 调用
│   │   ├── views/                    # 页面组件
│   │   ├── components/               # 通用组件
│   │   ├── router/                   # 路由配置
│   │   ├── stores/                   # Pinia 状态管理
│   │   └── utils/                    # 工具函数
│   ├── vite.config.js
│   └── package.json
│
├── plugins/                          # 客户插件目录
│   └── hospital_assets/              # 医院资产类型插件
│
├── docs/                             # 文档
└── scripts/                          # 项目级脚本
    └── init_extended_asset_types.py
```

---

## API 端口映射

| 模块 | 路由前缀 | 说明 |
|------|----------|------|
| 认证 | `/api/auth/` | 登录/登出/用户/角色/权限 |
| 客户 | `/api/customers/` | 客户 CRUD + 插件配置 |
| 资产 | `/api/assets/` | 资产 CRUD（含扩展类型） |
| 监控 | `/api/monitoring/` | 监控项/采集任务/结果/测试 |
| 告警 | `/api/alerts/` | 告警记录/阈值规则/状态操作 |
| 巡检 | `/api/inspection/` | 巡检计划/任务/结果/报告 |
| 驾驶舱 | `/api/dashboard/` | 统计图表/概览数据 |
| 系统 | `/api/system/` | 系统设置 |
| 发现 | `/api/discovery/` | 自动发现/拓扑 |
| 技能 | `/api/skills/` | 技能模块执行 |
| 调度 | `/api/scheduler/v2/` | 定时任务 |
| 库存 | `/api/lab/` | 实验室库存 |
| Admin | `/admin/` | Django 管理后台 |
| Swagger | `/swagger/` | API 文档 |

---

## 与 ops-center 的关联

ops-system 作为 **租户端（Agent）**，与 **ops-center（中心端）** 协同工作：

```
┌──────────────────┐         ┌──────────────────┐
│   ops-system     │  ───→   │   ops-center     │
│   (租户端)       │  push   │   (中心端)       │
│                  │  ───→   │                  │
│  各客户/租户侧   │  data   │  多租户聚合      │
│  资产管理        │  ───→   │  告警分发        │
│  监控采集        │         │  通知推送        │
│  告警生成        │  ←───   │  知识包/补丁同步 │
│  巡检执行        │  sync   │  统一配置管理    │
└──────────────────┘         └──────────────────┘
```

### 数据推送内容（push_service）

| 推送内容 | 说明 | 频率 |
|----------|------|------|
| **心跳** | 租户在线状态 | 每 5 分钟 |
| **告警** | 新告警及状态变更 | 实时/批量 |
| **巡检结果** | 巡检任务完成数据 | 每次巡检后 |
| **监控数据** | 异常监控数据点 | 采集后 |
| **资产状态** | 资产在线/离线状态 | 按需 |
| **采集测试结果** | 测试采集数据 | 测试后 |

### 数据同步内容（knowledge_updater）

| 同步内容 | 说明 |
|----------|------|
| **知识包** | 检查项模板/阈值定义 |
| **补丁** | 系统升级包版本检查 |

### 推送配置

推送到 ops-center 的配置存储在 `system_settings` 表中，包括：
- `push.center_url` — ops-center 地址
- `push.enabled` — 是否启用推送
- `push.api_key` — API 鉴权密钥

---

## 快速启动

### 前置依赖

- Python 3.10+
- Node.js 18+
- MySQL 8.0（推荐 Docker: `docker run --name mysql-ops -e MYSQL_ROOT_PASSWORD=root123 -e MYSQL_DATABASE=ops_system -p 3306:3306 -d mysql:8.0`）

### 一键启动

```bash
cd /home/zhang/.openclaw/workspace/ops-system
bash ops-system-start.sh
```

### 分步启动

```bash
# 1. 安装后端依赖
cd /home/zhang/.openclaw/workspace/ops-system/backend
pip install -r requirements.txt

# 2. 数据库迁移
python manage.py migrate

# 3. 初始化扩展资产类型
python manage.py shell < ../scripts/init_extended_asset_types.py

# 4. 启动后端（端口 8002）
python manage.py runserver 0.0.0.0:8002

# 5. 安装前端依赖
cd ../frontend
npm install

# 6. 启动前端开发服务器（端口 3099）
npm run dev
```

### 访问系统

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost:3099 |
| 后端 API | http://localhost:8002/api/ |
| API 文档 | http://localhost:8002/swagger/ |
| Django Admin | http://localhost:8002/admin/ |

### 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | 超级管理员 |

---

## 数据库配置

默认数据库配置（MySQL 8.0）：

| 参数 | 值 |
|------|-----|
| 主机 | 127.0.0.1 |
| 端口 | 3306 |
| 数据库 | `ops_system` |
| 用户名 | `root` |
| 密码 | `root123` |
| Docker 容器 | `mysql-ops` |

---

## 示例数据

系统初始化后自动创建以下示例数据：

### 客户
- 藏书卫生院
- 太湖度假区医院

### 资产类型（每客户 10 种）
- 服务器、网络设备、安全设备、存储设备、基础设施
- 数据库、中间件、API 接口、云服务、应用程序

### 测试资产
- **SRV-001** — 数据库服务器
- **DB-001** — HIS 系统 MySQL 数据库
- **MW-001** — Web 服务器 Nginx
- **API-001** — 患者信息查询 API

---

## 常用命令

```bash
# 查看日志
tail -f /tmp/ops-backend.log
tail -f /tmp/ops-frontend.log

# 数据库迁移
cd /home/zhang/.openclaw/workspace/ops-system/backend
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 采集测试
curl -X POST http://localhost:8002/api/monitoring/test/ \
  -H "Content-Type: application/json" \
  -d '{"protocol": "ping", "target": "8.8.8.8"}'
```

---

## 许可证

MIT License
