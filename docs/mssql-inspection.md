# MSSQL 数据库巡检配置指南

## 连接方式

本项目使用 FreeTDS 连接 MSSQL，解决了 pymssql 和 ODBC Driver 18 的 TLS 兼容性问题。

### 前置条件

1. **安装 FreeTDS**
```bash
sudo apt-get install -y tdsodbc freetds-bin
```

2. **配置 FreeTDS（关闭加密）**

创建 `/tmp/freetds.conf` 或 `~/.freetds/freetds.conf`：

```ini
[global]
    tds version = 7.4
    encryption = off
    client charset = UTF-8
```

3. **设置环境变量**
```bash
export FREETDSCONF=/tmp/freetds.conf
```

### 测试连接

```bash
export FREETDSCONF=/tmp/freetds.conf
TDSVER=7.4 tsql -H <MSSQL_IP> -p 1433 -U sa -P <密码> -D master
```

连接成功后执行 SQL：
```sql
SELECT @@VERSION
GO
```

## Python 连接代码

```python
import subprocess
import os

os.environ['FREETDSCONF'] = '/tmp/freetds.conf'

def query_mssql(host, port, user, password, database, sql):
    """使用 tsql 执行 MSSQL 查询"""
    cmd = f'TDSVER=7.4 tsql -H {host} -p {port} -U {user} -P "{password}" -D {database}'
    proc = subprocess.Popen(
        cmd, shell=True, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = proc.communicate(input=f'{sql}\nGO\n')
    return stdout
```

## 遇到的问题及解决方案

### 问题1: pymssql TLS 握手失败
- **现象**: `pymssql.OperationalError: (20002, 'Adaptive Server connection failed')`
- **原因**: pymssql 2.3.x 使用 FreeTDS 库，与新版 MSSQL 的 TLS 握手不兼容
- **解决**: 使用 FreeTDS 命令行工具 `tsql`，配置 `encryption = off`

### 问题2: ODBC Driver 18 SSL 错误
- **现象**: `SSL Provider: error:0A000102:SSL routines::unsupported protocol`
- **原因**: Microsoft ODBC Driver 18 强制 TLS 握手，OpenSSL 3.0 禁用了 TLS 1.0/1.1
- **解决**: 改用 FreeTDS `tsql` 工具，配置 `encryption = off`

### 问题3: MySQL 8.0 CPU 不支持 x86-64-v2
- **现象**: `Fatal glibc error: CPU does not support x86-64-v2`
- **原因**: MySQL 8.0 Docker 镜像要求 CPU 支持 x86-64-v2 指令集
- **解决**: 使用 MariaDB 10.11 或改用 PostgreSQL

### 问题4: 网络不通
- **现象**: ping 100% 丢包，1433 端口不通
- **原因**: IP 地址错误（172.16.11.50 → 实际为 172.26.11.50）
- **解决**: 确认正确的 IP 地址，检查网关路由

## 巡检检查项

| 检查项 | 编码 | 说明 |
|--------|------|------|
| 数据库连接 | DB_CONNECTION | 测试 MSSQL 连接是否正常 |
| 数据库版本 | DB_VERSION | 检查 SQL Server 版本 |
| 服务器名称 | SERVER_NAME | 获取服务器主机名 |
| 最大连接数 | MAX_CONNECTIONS | 检查最大连接数配置 |
| 数据库状态 | DB_STATUS | 检查所有数据库是否 ONLINE |
| 活跃会话数 | ACTIVE_SESSIONS | 当前用户会话数 |
| 备份状态 | BACKUP_STATUS | 最近备份时间和状态 |
