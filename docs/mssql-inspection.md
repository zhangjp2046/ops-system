# MSSQL 数据库巡检配置指南

## 问题背景

在 Linux 服务器上使用 Python 连接 MSSQL 时遇到以下问题：
1. **pymssql 2.3.x TLS 握手失败** — `OperationalError: (20002, 'Adaptive Server connection failed')`
2. **ODBC Driver 18 SSL 错误** — `SSL Provider: error:0A000102:SSL routines::unsupported protocol`
3. 原因：pymssql 底层 FreeTDS 库与新版 MSSQL 的 TLS 握手不兼容；ODBC Driver 18 强制 TLS 但 OpenSSL 3.0 禁用了 TLS 1.0/1.1

## 解决方案

使用 **FreeTDS tsql 命令行工具** 替代 pymssql/ODBC，配置关闭加密。

### 1. 安装依赖

```bash
sudo apt-get update
sudo apt-get install -y tdsodbc freetds-bin
```

### 2. 配置 FreeTDS（关闭加密）

创建 `/tmp/freetds.conf`：

```ini
[global]
    tds version = 7.4
    encryption = off
    client charset = UTF-8
```

### 3. 测试连接

```bash
export FREETDSCONF=/tmp/freetds.conf
TDSVER=7.4 tsql -H <MSSQL_IP> -p 1433 -U sa -P <密码> -D master
```

连接成功后执行 SQL：
```sql
SELECT @@VERSION
GO
```

### 4. Python 集成

项目中已实现 `MSSQLConnector` 类（`backend/apps/inspection/mssql_connector.py`）：

```python
from apps.inspection.mssql_connector import MSSQLConnector

conn = MSSQLConnector(
    host='172.26.11.50',
    port=1433,
    user='sa',
    password='Beyondit@123',
    database='master'
)

# 获取服务器信息
info = conn.get_server_info()
print(info)

# 执行查询
results = conn.query('SELECT name FROM sys.databases')
print(results)
```

### 5. 巡检检查项

| 检查项 | 编码 | 说明 |
|--------|------|------|
| 数据库连接 | DB_CONNECTION | 测试 MSSQL 连接是否正常 |
| 数据库版本 | DB_VERSION | 检查 SQL Server 版本 |
| 服务器名称 | SERVER_NAME | 获取服务器主机名 |
| 最大连接数 | MAX_CONNECTIONS | 检查最大连接数配置 |
| 数据库状态 | DB_STATUS | 检查所有数据库是否 ONLINE |
| 活跃会话数 | ACTIVE_SESSIONS | 当前用户会话数 |
| 备份状态 | BACKUP_STATUS | 最近备份时间和状态 |

## 已知问题

- pymssql 2.3.x 不兼容 OpenSSL 3.0 + MSSQL TLS 握手
- ODBC Driver 18 强制要求 TLS，与老版 MSSQL 不兼容
- FreeTDS tsql 的输出解析需要处理多行值（如 @@VERSION）和提示符前缀（1>/2>）
