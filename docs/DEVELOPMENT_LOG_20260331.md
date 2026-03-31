# 开发记录 - 2026年3月31日

## 项目
**ops-system** - 通用运维管理系统

---

## 今日完成

### 1. 项目会话隔离
- 为 ops-system 设置独立的 Cookie 名称，避免与 goodsproject 冲突
- Session Cookie: `ops_sessionid`
- CSRF Cookie: `ops_csrftoken`
- localStorage 前缀: `ops_`

### 2. 采集测试页面优化
- 修复了 Axios 数据响应解析问题（`res.data` vs `res`）
- 优化了测试结果显示界面
- 添加了协议标签类型分类显示
- 添加了可折叠的原始返回数据查看

### 3. 监控协议支持
| 协议 | 状态 | 备注 |
|------|------|------|
| Ping | ✅ 正常 | |
| 端口检测 | ✅ 正常 | |
| SSH | ✅ 正常 | |
| SNMP | ✅ 正常 | |
| MySQL | ✅ 正常 | |
| PostgreSQL | ✅ 正常 | |
| MSSQL | ❌ 有问题 | TLS 握手失败 |

---

## 待解决问题

### MSSQL 连接失败
**错误信息**:
```
Adaptive Server connection failed (192.168.1.11)
TLS handshake failed
```

**原因分析**:
- SQL Server 要求 TLS 加密连接
- FreeTDS 无法完成 TLS 握手
- pyodbc 需要 ODBC Driver，但安装失败

**尝试过的解决方案**:
1. ❌ `encryption = off` 配置 → 无效
2. ❌ TDS 版本切换 (7.4 / 8.0) → 无效
3. ❌ 禁用 ForceEncryption 注册表 → 已经是 0
4. ❌ pyodbc 驱动 → 系统没有 ODBC 驱动
5. ❌ msodbcsql17 → Ubuntu 24.04 兼容性问题，安装失败

**下一步方案**:
1. 在 SQL Server 端禁用强制加密（最可能有效）
   - 位置：SQL Server Configuration Manager → TCP/IP → Encrypt → No
   - 或修改注册表 `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Microsoft SQL Server\...\SuperSocketNetLib`
2. 升级 FreeTDS 到最新版重新编译
3. 安装 Microsoft ODBC Driver 17（需要解决 Ubuntu 24.04 兼容性问题）

**SQL Server 信息**:
- 地址: 192.168.1.11
- 端口: 1433
- 用户: sa
- 密码: abc123
- 版本: SQL Server 2014

---

## 项目状态

### 运行服务
- 前端: http://localhost:3000
- 后端: http://localhost:8000

### 关键文件
- 后端协议实现: `/home/zhang/botcode/ops-system/backend/apps/monitoring/protocols.py`
- 前端采集测试页面: `/home/zhang/botcode/ops-system/frontend/src/views/monitoring/MonitorTest.vue`
- 后端测试视图: `/home/zhang/botcode/ops-system/backend/apps/monitoring/test_views.py`

### 修改过的文件
- `protocols.py` - MSSQL 连接代码已改用 pyodbc（但驱动缺失）
- `MonitorTest.vue` - 修复 Axios 响应解析和结果展示优化

---

## 明日计划
1. 解决 MSSQL 连接问题
2. 测试其他数据库协议（MySQL、PostgreSQL）确保正常工作
3. 继续完善监控功能
