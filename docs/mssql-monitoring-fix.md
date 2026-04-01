# 监控采集 MSSQL/Oracle 连接修复文档

## 问题

`http://localhost:3002/monitor-test` 页面的数据库采集测试功能中：
- **MSSQL**：使用 `pyodbc` + ODBC Driver 18 连接，遇到 TLS 握手兼容性问题
- **Oracle**：使用 `cx_Oracle`，需要安装 Oracle 客户端库，部署复杂

错误表现：
- MSSQL：`SSL Provider: error:0A000102:SSL routines::unsupported protocol`
- Oracle：`ImportError: No module named 'cx_Oracle'`

## 根因

与巡检模块相同的问题：
1. **pymssql 2.3.x** 底层 FreeTDS 与新版 MSSQL 的 TLS 握手不兼容
2. **ODBC Driver 18** 强制 TLS 握手，但 OpenSSL 3.0 禁用了 TLS 1.0/1.1
3. **cx_Oracle** 需要完整的 Oracle Instant Client 安装

## 解决方案

### MSSQL：使用 FreeTDS tsql 命令行工具

改造 `backend/apps/monitoring/protocols.py` 中的 `DatabaseProtocol._test_mssql()` 方法：

**改造前：**
```python
def _test_mssql(self):
    import pyodbc
    conn_str = f"DRIVER={driver};SERVER={host},{port};UID={user};PWD={pwd};"
    conn = pyodbc.connect(conn_str)  # ❌ TLS 握手失败
```

**改造后：**
```python
def _test_mssql(self):
    import subprocess, os
    # 配置 FreeTDS 关闭加密
    conf_path = '/tmp/freetds.conf'
    with open(conf_path, 'w') as f:
        f.write('[global]\n    tds version = 7.4\n    encryption = off\n')
    
    cmd = f'TDSVER=7.4 tsql -H {host} -p {port} -U {user} -P "{pwd}" -D {db}'
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                           env={**os.environ, 'FREETDSCONF': conf_path})
    stdout, _ = proc.communicate(input='SELECT @@VERSION\nGO\n')
    # 解析版本信息...
```

### Oracle：使用 sqlplus 命令行工具

改造 `DatabaseProtocol._test_oracle()` 方法：

**改造前：**
```python
def _test_oracle(self):
    import cx_Oracle  # ❌ 需要安装 Oracle 客户端
    conn = cx_Oracle.connect(user, pwd, dsn)
```

**改造后：**
```python
def _test_oracle(self):
    import subprocess
    dsn = f'{user}/{pwd}@{host}:{port}/{db}'
    proc = subprocess.Popen(f'sqlplus -S {dsn}', ...)
    stdout, _ = proc.communicate(input='SELECT banner FROM v$version;\nEXIT;')
    # 解析版本信息...
```

## 前置条件

```bash
# 安装 FreeTDS（MSSQL 连接）
sudo apt-get install -y tdsodbc freetds-bin

# Oracle 需要安装 sqlplus 客户端（如果需要 Oracle 监控）
```

## 修改文件

- `backend/apps/monitoring/protocols.py`
  - `DatabaseProtocol._test_mssql()` — 用 FreeTDS tsql 替代 pyodbc
  - `DatabaseProtocol._test_oracle()` — 用 sqlplus 替代 cx_Oracle

## 测试验证

```bash
cd backend
python3 -c "
import django; import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; django.setup()
from apps.monitoring.protocols import DatabaseProtocol

# 测试 MSSQL
proto = DatabaseProtocol(host='172.26.11.50', port=1433, username='sa', password='Beyondit@123', database='master', db_type='mssql')
print(proto.test_connect())
# 期望输出: {'success': True, 'connected': True, 'version': 'Microsoft SQL Server 2014...', 'error': None}
"
```

## 关联修复

此修复与巡检模块的 MSSQL 连接修复方案一致，共用 FreeTDS 配置：
- 巡检：`backend/apps/inspection/db_connectors.py` → `MSSQLConnector`
- 监控：`backend/apps/monitoring/protocols.py` → `DatabaseProtocol._test_mssql()`

两处共用 `/tmp/freetds.conf` 配置文件。
