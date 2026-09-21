# ops-system 通用运维管理系统

> 多客户、多类型的IT资产管理平台（租户端）

## 技术栈

- **后端：** Django 4.2 + Django REST Framework + MySQL 8.0
- **前端：** Vue 3 + Vite 4 + Element Plus + Pinia + Vue Router + ECharts
- **数据库：** MySQL 8.0（DB: `ops_system`, localhost:3306, root/root123）
- **认证：** Session 认证（cookie: `ops_sessionid`）
- **插件系统：** 支持客户自定义资产类型

## 目录结构

```
ops-system/
├── backend/
│   ├── apps/
│   │   ├── assets/         # 资产管理（服务器/网络/安全/存储/数据库/中间件等）
│   │   ├── customers/      # 客户管理（多租户+插件）
│   │   ├── users/          # 用户/角色/权限管理
│   │   ├── monitoring/     # 监控管理（Ping/端口/SNMP/HTTP/SSL）
│   │   ├── alerts/         # 告警管理（阈值/状态流转）
│   │   ├── inspection/     # 巡检管理（计划/任务/记录）
│   │   ├── dashboard/      # 驾驶舱统计
│   │   ├── workorder/      # 工单管理（需确认路径）
│   │   ├── scheduler_v2/   # 定时任务调度
│   │   ├── discovery/      # 自动发现
│   │   ├── system/         # 系统设置
│   │   ├── skills/         # 技能模块
│   │   └── lab_inventory/  # 实验室库存（与 labrms 共享模块）
│   ├── config/             # Django 配置
│   └── scripts/            # 脚本工具
├── frontend/
│   ├── src/
│   │   ├── api/            # API 调用
│   │   ├── views/          # 页面组件
│   │   ├── components/     # 通用组件
│   │   ├── router/         # 路由配置
│   │   ├── stores/         # Pinia 状态管理
│   │   └── utils/          # 工具函数
│   └── package.json
├── plugins/                # 客户插件目录
│   └── hospital_assets/    # 医院资产插件
└── docs/
```

## API 端口映射

| 模块 | 路由 | 说明 |
|------|------|------|
| 认证 | `/api/auth/` | 登录/权限/角色 |
| 客户 | `/api/customers/` | 客户 CRUD + 插件 |
| 资产 | `/api/assets/` | 资产 CRUD（含扩展类型） |
| 监控 | `/api/monitoring/` | 监控项/采集/结果 |
| 告警 | `/api/alerts/` | 告警规则/记录 |
| 巡检 | `/api/inspection/` | 计划/任务/报告 |
| 驾驶舱 | `/api/dashboard/` | 统计图表 |
| 系统 | `/api/system/` | 系统设置 |
| 发现 | `/api/discovery/` | 自动发现 |
| 技能 | `/api/skills/` | 技能模块 |
| 调度 | `/api/scheduler/v2/` | 定时任务 |
| 库存 | `/api/lab/` | 实验室库存 |
| Admin | `/admin/` | Django Admin |

## 常用命令

```bash
# 后端启动（端口 8002）
cd ~/.openclaw/workspace/ops-system/backend
source venv/bin/activate
python manage.py runserver 0.0.0.0:8002

# 前端启动（端口 3099）
cd ~/.openclaw/workspace/ops-system/frontend
npm run dev

# 一键启动
bash ~/.openclaw/workspace/ops-system/ops-system-start.sh

# 数据库迁移
cd ~/.openclaw/workspace/ops-system/backend
python manage.py makemigrations
python manage.py migrate

# 查看日志
tail -f /tmp/ops-backend.log
tail -f /tmp/ops-frontend.log
```

## 关键端口

| 服务 | 端口 |
|------|------|
| Django 后端 | 8002 |
| Vite 前端 | 3099 |
| MySQL | 3306 |
| API 文档 | http://localhost:8002/swagger/ |

## 默认账号

- admin / admin123

## 与 ops-center 的关系

ops-system（租户端）负责各租户的资产管理、监控、告警、巡检等本地运维功能，通过 API 将告警/巡检数据上报到 ops-center（中心端）。ops-center 负责多租户聚合展示和通知分发。
