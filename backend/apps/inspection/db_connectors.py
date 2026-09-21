#!/usr/bin/env python3
"""
数据库巡检连接器 - 增强版
支持 MySQL、MSSQL、Oracle 三种数据库的深度巡检
每种数据库有专属的巡检项目和 SQL
支持自定义 SQL 执行
"""

import os
import sys
import tempfile
import subprocess
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.assets.models import Asset, AssetData


class BaseConnector:
    """数据库连接器基类"""

    def __init__(self, config):
        self.config = config
        self.connected = False

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def query(self, sql):
        """执行 SQL 返回列表[dict]"""
        raise NotImplementedError

    def check_connection(self):
        try:
            self.connect()
            self.query('SELECT 1')
            self.connected = True
            return {'status': 'success', 'message': '连接正常'}
        except Exception as e:
            self.connected = False
            return {'status': 'failed', 'message': str(e)}

    # ========== 通用巡检项 ==========

    def get_server_info(self):
        raise NotImplementedError

    def get_databases(self):
        raise NotImplementedError

    def get_database_sizes(self):
        """数据库文件大小（数据文件 + 日志文件）"""
        raise NotImplementedError

    def get_tablespace_info(self):
        raise NotImplementedError

    def get_session_info(self):
        raise NotImplementedError

    def get_performance_info(self):
        raise NotImplementedError

    def get_backup_info(self):
        raise NotImplementedError

    def get_error_logs(self):
        """错误日志"""
        raise NotImplementedError

    def get_archive_logs(self):
        """归档日志（Oracle）"""
        return None  # 仅 Oracle

    def get_lock_info(self):
        """锁信息"""
        return None

    def get_slow_queries(self):
        """慢查询"""
        return None

    # ========== 自定义 SQL ==========

    def execute_custom_sql(self, sql):
        """执行自定义 SQL 并返回格式化结果"""
        try:
            results = self.query(sql)
            if not results:
                return {'status': 'success', 'columns': [], 'rows': [], 'row_count': 0}
            columns = list(results[0].keys())
            rows = [list(r.values()) for r in results]
            return {
                'status': 'success',
                'columns': columns,
                'rows': rows,
                'row_count': len(rows)
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


class MySQLConnector(BaseConnector):
    """MySQL 连接器"""

    def __init__(self, config):
        super().__init__(config)
        self._conn = None
        import pymysql
        self._pymysql = pymysql

    def connect(self):
        self._conn = self._pymysql.connect(
            host=self.config['host'],
            port=int(self.config.get('port', 3306)),
            user=self.config['username'],
            password=self.config['password'],
            database=self.config.get('database', 'mysql'),
            connect_timeout=10
        )

    def disconnect(self):
        if self._conn:
            self._conn.close()

    def query(self, sql):
        with self._conn.cursor(self._pymysql.cursors.DictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()

    def get_server_time(self):
        """取数据库服务器当前时间（UTC epoch），用于时间同步检查。
        只读查询，不需要任何写权限。"""
        r = self.query('SELECT UNIX_TIMESTAMP(NOW(6)) AS EPOCH')
        return {'epoch': _first_epoch(r)} if _first_epoch(r) is not None else {}

    def get_server_info(self):
        r = self.query('SELECT @@version AS version, @@version_comment AS comment, @@datadir AS datadir, @@basedir AS basedir, @@max_connections AS max_connections, @@wait_timeout AS wait_timeout')
        if not r: return {}
        row = r[0]
        uptime_r = self.query("SHOW STATUS LIKE 'Uptime'")
        uptime = int(uptime_r[0]['Value']) if uptime_r else 0
        row['uptime_seconds'] = uptime
        row['uptime_days'] = uptime // 86400
        return row

    def get_databases(self):
        return self.query("SELECT schema_name AS name, default_character_set_name AS charset FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema','mysql','performance_schema','sys')")

    def get_database_sizes(self):
        return self.query("""
            SELECT table_schema AS database_name,
                   ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS total_size_mb,
                   ROUND(SUM(data_length) / 1024 / 1024, 2) AS data_size_mb,
                   ROUND(SUM(index_length) / 1024 / 1024, 2) AS index_size_mb,
                   COUNT(*) AS table_count
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema','mysql','performance_schema','sys')
            GROUP BY table_schema ORDER BY total_size_mb DESC
        """)

    def get_tablespace_info(self):
        return self.query("""
            SELECT table_schema AS name,
                   ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb,
                   COUNT(*) AS table_count
            FROM information_schema.tables
            GROUP BY table_schema ORDER BY size_mb DESC
        """)

    def get_session_info(self):
        total = self.query("SHOW STATUS LIKE 'Threads_connected'")
        running = self.query("SHOW STATUS LIKE 'Threads_running'")
        processes = self.query("""
            SELECT id, user, host, db, command, time AS duration, state, LEFT(info, 100) AS sql_preview
            FROM information_schema.processlist
            WHERE command != 'Sleep' ORDER BY time DESC LIMIT 20
        """)
        return {
            'threads_connected': int(total[0]['Value']) if total else 0,
            'threads_running': int(running[0]['Value']) if running else 0,
            'active_processes': processes
        }

    def get_performance_info(self):
        status = self.query("SHOW GLOBAL STATUS")
        s = {r['Variable_name']: r['Value'] for r in status}
        # InnoDB 缓冲池命中率
        read_req = int(s.get('Innodb_buffer_pool_read_requests', 1))
        reads = int(s.get('Innodb_buffer_pool_reads', 0))
        hit_ratio = round((read_req - reads) / max(read_req, 1) * 100, 2)
        return {
            'buffer_pool_hit_ratio': hit_ratio,
            'threads_connected': int(s.get('Threads_connected', 0)),
            'threads_running': int(s.get('Threads_running', 0)),
            'questions': int(s.get('Questions', 0)),
            'slow_queries': int(s.get('Slow_queries', 0)),
            'innodb_rows_read': int(s.get('Innodb_rows_read', 0)),
            'innodb_rows_inserted': int(s.get('Innodb_rows_inserted', 0)),
            'connections': int(s.get('Connections', 0)),
            'aborted_connects': int(s.get('Aborted_connects', 0)),
        }

    def get_backup_info(self):
        return {'status': 'UNKNOWN', 'message': 'MySQL 无内置备份状态，请检查备份脚本'}

    def get_error_logs(self):
        try:
            r = self.query("SHOW VARIABLES LIKE 'log_error'")
            return {'log_error_file': r[0]['Value'] if r else 'unknown'}
        except:
            return {'log_error_file': 'unknown'}

    def get_lock_info(self):
        return self.query("""
            SELECT trx_id, trx_state, trx_started, trx_mysql_thread_id AS thread_id,
                   trx_rows_locked, trx_rows_modified, LEFT(trx_query, 100) AS query
            FROM information_schema.innodb_trx
            WHERE trx_state != 'RUNNING' OR trx_rows_locked > 0
            LIMIT 20
        """)

    def get_slow_queries(self):
        try:
            return self.query("""
                SELECT start_time, query_time, lock_time, rows_sent, rows_examined, LEFT(sql_text, 200) AS sql_text
                FROM mysql.slow_log ORDER BY start_time DESC LIMIT 20
            """)
        except:
            return []


class MSSQLConnector(BaseConnector):
    """MSSQL 连接器（基于 FreeTDS tsql）"""

    # TDS 版本优先级：7.4(MSSQL2012+) → 7.3(MSSQL2008/R2) → 7.2(MSSQL2005) → 7.1(MSSQL2000)
    TDS_VERSIONS = ['7.4', '7.3', '7.2', '7.1']

    def __init__(self, config):
        super().__init__(config)
        self._tds_version = None  # 连接成功后记录
        self._setup_freetds_configs()

    def _setup_freetds_configs(self):
        """为所有 TDS 版本创建配置文件"""
        for tds_ver in self.TDS_VERSIONS:
            conf_path = f'/tmp/freetds_{tds_ver}.conf'
            if not os.path.exists(conf_path):
                with open(conf_path, 'w') as f:
                    f.write(f'[global]\n    tds version = {tds_ver}\n    encryption = off\n    client charset = UTF-8\n')

    def connect(self):
        """自动检测可用的 TDS 版本"""
        if self._tds_version:
            self.connected = True
            return

        for tds_ver in self.TDS_VERSIONS:
            conf_path = f'/tmp/freetds_{tds_ver}.conf'
            cmd = (f'TDSVER={tds_ver} tsql -H {self.config["host"]} '
                   f'-p {self.config.get("port", 1433)} '
                   f'-U {self.config["username"]} -P "{self.config["password"]}" '
                   f'-D {self.config.get("database", "master")}')
            try:
                proc = subprocess.Popen(
                    cmd, shell=True, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    env={**os.environ, 'FREETDSCONF': conf_path}
                )
                stdout, _ = proc.communicate(
                    input="SELECT @@VERSION AS v\nGO\n", timeout=10
                )
                if 'Microsoft SQL Server' in stdout or 'Adaptive Server' in stdout:
                    self._tds_version = tds_ver
                    self._tds_conf = conf_path
                    self.connected = True
                    return
            except Exception:
                continue

        self.connected = False
        raise ConnectionError(f'MSSQL 连接失败: 所有 TDS 版本均无法连接')

    def disconnect(self):
        self.connected = False

    def query(self, sql):
        if not self._tds_version:
            self.connect()
        cmd = (f'TDSVER={self._tds_version} tsql -H {self.config["host"]} '
               f'-p {self.config.get("port", 1433)} '
               f'-U {self.config["username"]} -P "{self.config["password"]}" '
               f'-D {self.config.get("database", "master")}')
        proc = subprocess.Popen(
            cmd, shell=True, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={**os.environ, 'FREETDSCONF': self._tds_conf}
        )
        stdout, _ = proc.communicate(input=f'{sql}\nGO\n')
        return self._parse_tsql_output(stdout)

    def _parse_tsql_output(self, stdout):
        results = []
        lines = stdout.split('\n')
        clean = []
        for line in lines:
            s = line.strip()
            if not s: continue
            if s.startswith('locale') or s.startswith('using') or s.startswith('Setting'): continue
            if re.match(r'^\(\d+ rows? affected\)', s): continue
            if re.match(r'^\d+>\s*$', s): continue
            s = re.sub(r'(?:\d+>\s*)+', '', s)
            if not s: continue
            clean.append(s)
        if len(clean) < 2: return results
        header = clean[0]
        # 尝试 tab 分割，回退空格分割（兼容不同 tsql 输出格式）
        if '\t' in header:
            headers = [h for h in header.split('\t') if h]  # 过滤空字符串（FreeTDS 多 tab 对齐）
        else:
            # 空格分割：如果第一行全是英文字母（无数字），视为表头
            if re.match(r'^[a-zA-Z_ /()]+$', header):
                headers = header.split()
            else:
                return results
        num_cols = len(headers)
        use_tabs = '\t' in header  # 记录该查询的输出是 tab 分隔还是空格分隔
        merged = []
        current = []
        for line in clean[1:]:
            parts = [p for p in (line.split('\t') if use_tabs else line.split()) if p]  # 过滤空字符串（多 tab 对齐）
            # 如果过滤后列数不够，尝试不过滤（兼容某些值可能为空的场景）
            if len(parts) < num_cols:
                parts2 = line.split('\t') if use_tabs else line.split()
                if len(parts2) >= num_cols:
                    parts = parts2[:num_cols]
            if not current:
                current = parts
            elif (use_tabs and '\t' in line and len(current) >= num_cols) \
                 or (not use_tabs and len(line.split()) == num_cols and len(current) >= num_cols):
                merged.append(current[:num_cols])
                current = parts
            elif use_tabs and '\t' in line:
                current.extend(parts)
            else:
                if current:
                    current[-1] += '\n' + line
        if current:
            if len(current) >= num_cols:
                merged.append(current[:num_cols])
            else:
                # 列数不够，可能需要填充
                while len(current) < num_cols:
                    current.append('')
                merged.append(current[:num_cols])
        for row in merged:
            results.append(dict(zip(headers, row)))
        return results

    def get_server_time(self):
        """取数据库服务器当前时间（UTC epoch）。
        DATEDIFF_BIG 需要 SQL Server 2016+，不支持时回退到秒级 DATEDIFF。"""
        for sql in (
            "SELECT DATEDIFF_BIG(MILLISECOND, '19700101', SYSUTCDATETIME()) / 1000.0 AS EPOCH",
            "SELECT CONVERT(BIGINT, DATEDIFF(SECOND, '19700101', GETUTCDATE())) AS EPOCH",
        ):
            try:
                epoch = _first_epoch(self.query(sql))
            except Exception:
                continue
            if epoch is not None:
                return {'epoch': epoch}
        return {}

    def get_server_info(self):
        r = self.query('SELECT @@VERSION AS version, @@SERVERNAME AS server_name, @@MAX_CONNECTIONS AS max_connections')
        if not r: return {}
        row = r[0]
        row['version'] = (row.get('version', '') or '').split('\n')[0]
        return row

    def get_databases(self):
        return self.query("SELECT name, state_desc AS state, recovery_model_desc AS recovery_model FROM sys.databases ORDER BY name")

    def get_database_sizes(self):
        """获取每个数据库的数据文件和日志文件大小（分别聚合）"""
        try:
            return self.query("""
                SELECT DB_NAME(database_id) AS database_name,
                       SUM(CASE WHEN type=0 THEN CAST(size AS BIGINT) ELSE 0 END)*8/1024 AS data_size_mb,
                       SUM(CASE WHEN type=1 THEN CAST(size AS BIGINT) ELSE 0 END)*8/1024 AS log_size_mb
                FROM sys.master_files
                GROUP BY database_id
                ORDER BY database_name
            """)
        except Exception:
            pass
        # 回退：如果上面报错，尝试不 CAST 的版本
        try:
            return self.query("""
                SELECT DB_NAME(database_id) AS database_name,
                       SUM(CASE WHEN type=0 THEN size ELSE 0 END)*8/1024 AS data_size_mb,
                       SUM(CASE WHEN type=1 THEN size ELSE 0 END)*8/1024 AS log_size_mb
                FROM sys.master_files
                GROUP BY database_id
                ORDER BY database_name
            """)
        except Exception:
            return []

    def get_tablespace_info(self):
        return self.query("""
            SELECT DB_NAME(database_id) AS database_name,
                   CASE WHEN type = 0 THEN 'ROWS' WHEN type = 1 THEN 'LOG' ELSE 'OTHER' END AS file_type,
                   CAST(SUM(size) * 8.0 / 1024 AS DECIMAL(10,2)) AS total_size_mb,
                   COUNT(*) AS file_count
            FROM sys.master_files
            GROUP BY database_id, type
            ORDER BY database_id, type
        """)

    def get_session_info(self):
        sessions = self.query("""
            SELECT s.session_id, s.status, s.login_time, s.host_name, s.program_name,
                   LEFT(COALESCE(c.text, ''), 100) AS sql_preview
            FROM sys.dm_exec_sessions s
            LEFT JOIN sys.dm_exec_requests r ON s.session_id = r.session_id
            OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) c
            WHERE s.is_user_process = 1
            ORDER BY s.login_time DESC
        """)
        return {
            'total_sessions': len(sessions),
            'active_sessions': [s for s in sessions if s.get('status') == 'running'],
            'all_sessions': sessions
        }

    def get_performance_info(self):
        try:
            hit = self.query("SELECT TOP 1 cntr_value AS val FROM sys.dm_os_performance_counters WHERE counter_name = 'Buffer cache hit ratio'")
            ple = self.query("SELECT TOP 1 cntr_value AS val FROM sys.dm_os_performance_counters WHERE counter_name = 'Page life expectancy' AND object_name LIKE '%Manager%'")
            batch = self.query("SELECT TOP 1 cntr_value AS val FROM sys.dm_os_performance_counters WHERE counter_name = 'Batch Requests/sec' AND cntr_type = 272696576")
            mem = self.query("SELECT TOP 1 cntr_value / 1024 AS val FROM sys.dm_os_performance_counters WHERE counter_name = 'Total Server Memory (KB)'")
            return {
                'buffer_cache_hit_ratio': float(hit[0]['val']) if hit else 0,
                'page_life_expectancy': int(ple[0]['val']) if ple else 0,
                'batch_requests_per_sec': int(batch[0]['val']) if batch else 0,
                'total_server_memory_mb': int(mem[0]['val']) if mem else 0,
            }
        except Exception:
            return {}

    def get_backup_info(self):
        try:
            return self.query("""
                SELECT database_name,
                       MAX(backup_start_date) AS last_backup_time,
                       CAST(MAX(backup_size) / 1024 / 1024 AS DECIMAL(10,2)) AS backup_size_mb,
                       type AS backup_type
                FROM msdb.dbo.backupset
                GROUP BY database_name, type
                ORDER BY last_backup_time DESC
            """)
        except:
            return []

    def get_error_logs(self):
        """MSSQL 错误日志（通过 sp_readerrorlog，最近7天）"""
        try:
            from datetime import datetime, timedelta
            date_filter = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            return self.query(f"EXEC xp_readerrorlog 0, 1, N'Error', NULL, NULL, NULL, N'{date_filter}'")
        except:
            return []

    def get_lock_info(self):
        return self.query("""
            SELECT request_session_id AS session_id, resource_type, resource_description,
                   request_mode, request_status
            FROM sys.dm_tran_locks
            WHERE request_status != 'GRANT'
            ORDER BY request_session_id
        """)

    def get_slow_queries(self):
        """获取最耗时的查询"""
        try:
            return self.query("""
                SELECT TOP 10
                    qs.total_elapsed_time / 1000000.0 AS total_seconds,
                    qs.execution_count,
                    qs.total_elapsed_time / qs.execution_count / 1000000.0 AS avg_seconds,
                    LEFT(st.text, 200) AS query_text
                FROM sys.dm_exec_query_stats qs
                CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
                ORDER BY qs.total_elapsed_time DESC
            """)
        except:
            return []


class OracleConnector(BaseConnector):
    """Oracle 连接器（基于 sqlplus）"""

    def __init__(self, config):
        super().__init__(config)

    def connect(self):
        # Oracle 用 sqlplus 命令行，先检查 sqlplus 是否存在
        sqlplus_path = subprocess.run(
            ['which', 'sqlplus'], capture_output=True, text=True
        ).stdout.strip()
        if not sqlplus_path:
            self.connected = False
            raise ConnectionError('Oracle 连接失败: sqlplus 命令未安装')
        dsn = f'{self.config["username"]}/{self.config["password"]}@{self.config["host"]}:{self.config.get("port", 1521)}/{self.config.get("database", "ORCL")}'
        env = os.environ.copy()
        env['NLS_LANG'] = 'AMERICAN_AMERICA.AL32UTF8'
        sql = 'SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF\nSELECT 1 FROM DUAL;\nEXIT\n'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write(sql)
            sqlfile = f.name
        try:
            proc = subprocess.run(
                ['sqlplus', '-S', dsn, f'@{sqlfile}'],
                capture_output=True, text=True, timeout=10, env=env
            )
            if proc.returncode != 0 or 'ORA-' in proc.stdout:
                self.connected = False
                raise ConnectionError(f'Oracle 连接失败: {proc.stderr or proc.stdout}'[:200])
            self.connected = True
        finally:
            os.unlink(sqlfile)

    def disconnect(self):
        self.connected = False

    def query(self, sql):
        """使用 sqlplus 执行查询（通过临时 SQL 文件，防 EXIT 干扰）"""
        import tempfile
        dsn = f'{self.config["username"]}/{self.config["password"]}@{self.config["host"]}:{self.config.get("port", 1521)}/{self.config.get("database", "ORCL")}'
        env_cmds = [
            'SET PAGESIZE 1000 FEEDBACK OFF VERIFY OFF HEADING ON ECHO OFF',
            'SET COLSEP |',
            'SET LINESIZE 4000',
            'SET TRIMSPOOL ON',
        ]
        full_sql = '\n'.join(env_cmds) + '\n' + sql.rstrip(';') + ';\nEXIT;'
        env = {**os.environ, 'NLS_LANG': 'AMERICAN_AMERICA.AL32UTF8'}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write(full_sql)
            sqlfile = f.name
        try:
            proc = subprocess.run(
                ['sqlplus', '-S', dsn, f'@{sqlfile}'],
                capture_output=True, text=True, timeout=15, env=env
            )
            return self._parse_sqlplus_output(proc.stdout)
        except subprocess.TimeoutExpired:
            return []
        finally:
            try:
                os.unlink(sqlfile)
            except:
                pass

    def _parse_sqlplus_output(self, stdout):
        """
        解析 sqlplus 输出（HEADING ON + COLSEP | 格式）
        第一行=表头，第二行=分隔线（---），之后=数据行
        """
        results = []
        lines = stdout.strip().split('\n')
        if not lines:
            return results
        clean = []
        for line in lines:
            s = line.strip()
            if not s:
                continue
            # 过滤 sqlplus 系统消息
            if s.startswith('Connected') or s.startswith('SQL>') or s.startswith('Disconnected'):
                continue
            # 过滤错误行
            if re.match(r'^ORA-', s) or re.match(r'^SP2-', s) or s.startswith('ERROR'):
                continue
            # 过滤分隔线（---）
            if re.match(r'^[-]+$', s) or all(c in '-+| ' for c in s):
                continue
            clean.append(s)
        if not clean:
            return results
        # 第一行是表头
        headers = [h.strip() for h in clean[0].split('|')]
        for data_line in clean[1:]:
            values = [v.strip() for v in data_line.split('|')]
            if len(values) == len(headers):
                results.append(dict(zip(headers, values)))
            elif len(values) > 1:
                # 补齐或截断
                if len(values) < len(headers):
                    values += [''] * (len(headers) - len(values))
                else:
                    values = values[:len(headers)]
                results.append(dict(zip(headers, values)))
        return results

    def get_server_time(self):
        """取数据库服务器当前时间（UTC epoch）。
        SYS_EXTRACT_UTC 保证不受数据库/会话时区影响。"""
        r = self.query(
            "SELECT (CAST(SYS_EXTRACT_UTC(SYSTIMESTAMP) AS DATE) "
            "- TO_DATE('19700101','YYYYMMDD')) * 86400 AS EPOCH FROM DUAL")
        epoch = _first_epoch(r)
        return {'epoch': epoch} if epoch is not None else {}

    def get_server_info(self):
        try:
            r = self.query("SELECT banner AS version FROM v$version WHERE ROWNUM = 1")
            inst = self.query("SELECT instance_name, status, database_status, startup_time FROM v$instance")
            # 调试：打印原始数据
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'[OracleInspect] v$version raw: {r}')
            logger.warning(f'[OracleInspect] v$instance raw: {inst}')
            logger.warning(f'[OracleInspect] v$version keys: {r[0].keys() if r else "empty"}')
            logger.warning(f'[OracleInspect] v$instance keys: {inst[0].keys() if inst else "empty"}')
            return {
                'version': r[0]['VERSION'] if r else '',
                'instance_name': inst[0]['INSTANCE_NAME'] if inst else '',
                'status': inst[0]['STATUS'] if inst else '',
                'database_status': inst[0]['DATABASE_STATUS'] if inst else '',
                'startup_time': inst[0]['STARTUP_TIME'] if inst else '',
            }
        except Exception as e:
            raise ConnectionError(f'查询 v$instance 失败: {e}')

    def get_databases(self):
        """Oracle 只有一个实例，返回表空间信息"""
        try:
            return self.query("SELECT tablespace_name AS name, status, contents FROM dba_tablespaces ORDER BY tablespace_name")
        except:
            try:
                return self.query("SELECT name AS name, DECODE(BITAND(flags, 1), 0, 'ONLINE', 'OFFLINE') AS status FROM v$tablespace ORDER BY name")
            except:
                return []

    def get_database_sizes(self):
        """获取表空间大小（优先 dba_data_files，失败用 v$datafile）"""
        try:
            return self.query("""
                SELECT tablespace_name,
                       ROUND(SUM(bytes) / 1024 / 1024, 2) AS total_size_mb,
                       COUNT(*) AS file_count
                FROM dba_data_files
                GROUP BY tablespace_name
                ORDER BY total_size_mb DESC
            """)
        except:
            try:
                return self.query("""
                    SELECT t.name AS tablespace_name,
                           ROUND(SUM(d.bytes) / 1024 / 1024, 2) AS total_size_mb,
                           COUNT(*) AS file_count
                    FROM v$tablespace t, v$datafile d
                    WHERE t.ts# = d.ts#
                    GROUP BY t.name
                    ORDER BY t.name
                """)
            except:
                return []

    def get_tablespace_info(self):
        """表空间使用率（优先 dba，失败用 v$datafile）"""
        try:
            return self.query("""
                SELECT df.tablespace_name,
                       ROUND(df.total_mb, 2) AS total_mb,
                       ROUND(df.total_mb - NVL(fs.free_mb, 0), 2) AS used_mb,
                       ROUND(NVL(fs.free_mb, 0), 2) AS free_mb,
                       ROUND((df.total_mb - NVL(fs.free_mb, 0)) / df.total_mb * 100, 2) AS used_pct
                FROM (SELECT tablespace_name, SUM(bytes) / 1024 / 1024 AS total_mb FROM dba_data_files GROUP BY tablespace_name) df
                LEFT JOIN (SELECT tablespace_name, SUM(bytes) / 1024 / 1024 AS free_mb FROM dba_free_space GROUP BY tablespace_name) fs
                ON df.tablespace_name = fs.tablespace_name
                ORDER BY used_pct DESC
            """)
        except:
            try:
                return self.query("""
                    SELECT t.name AS tablespace_name,
                           ROUND(SUM(d.bytes) / 1024 / 1024, 2) AS total_mb,
                           'N/A' AS used_mb,
                           'N/A' AS free_mb,
                           'N/A' AS used_pct
                    FROM v$tablespace t, v$datafile d
                    WHERE t.ts# = d.ts#
                    GROUP BY t.name
                    ORDER BY t.name
                """)
            except:
                return []

    def get_session_info(self):
        sessions = self.query("""
            SELECT s.sid, s.serial#, s.username, s.status, s.machine, s.program,
                   s.logon_time, ROUND(s.last_call_et / 60, 1) AS idle_minutes,
                   SUBSTR(q.sql_text, 1, 100) AS sql_preview
            FROM v$session s
            LEFT JOIN v$sql q ON s.sql_id = q.sql_id
            WHERE s.type = 'USER'
            ORDER BY s.logon_time DESC
        """)
        return {
            'total_sessions': len(sessions),
            'active_sessions': [s for s in sessions if s.get('STATUS') == 'ACTIVE'],
            'all_sessions': sessions
        }

    def get_performance_info(self):
        try:
            stats = self.query("SELECT name, value FROM v$sysstat WHERE name IN ('session logical reads', 'physical reads', 'physical writes', 'parse count (total)', 'parse count (hard)', 'execute count')")
            s = {r['NAME']: int(r['VALUE']) for r in stats}
            logical = s.get('session logical reads', 1)
            physical = s.get('physical reads', 0)
            hit_ratio = round((logical - physical) / max(logical, 1) * 100, 2)
            # 内存
            mem = self.query("SELECT ROUND(value / 1024 / 1024, 0) AS sga_mb FROM v$parameter WHERE name = 'sga_max_size'")
            return {
                'buffer_hit_ratio': hit_ratio,
                'session_logical_reads': s.get('session logical reads', 0),
                'physical_reads': s.get('physical reads', 0),
                'physical_writes': s.get('physical writes', 0),
                'parse_count_total': s.get('parse count (total)', 0),
                'parse_count_hard': s.get('parse count (hard)', 0),
                'execute_count': s.get('execute count', 0),
                'sga_size_mb': int(mem[0]['SGA_MB']) if mem else 0,
            }
        except:
            return {}

    def get_backup_info(self):
        try:
            return self.query("""
                SELECT session_key, input_type, status,
                       TO_CHAR(start_time, 'YYYY-MM-DD HH24:MI:SS') AS start_time,
                       TO_CHAR(end_time, 'YYYY-MM-DD HH24:MI:SS') AS end_time,
                       ROUND(elapsed_seconds / 60, 1) AS duration_minutes,
                       ROUND(output_bytes / 1024 / 1024, 2) AS output_mb
                FROM v$rman_backup_job_details
                ORDER BY start_time DESC
            """)
        except:
            return []

    def get_error_logs(self):
        """Oracle alert log 中的 ORA- 错误（最近100条）"""
        try:
            return self.query("""
                SELECT * FROM (
                    SELECT originating_timestamp, message_text
                    FROM v$diag_alert_ext
                    WHERE message_text LIKE 'ORA-%'
                    ORDER BY originating_timestamp DESC
                ) WHERE ROWNUM < 100
            """)
        except:
            return []

    def get_archive_logs(self):
        """归档日志使用情况"""
        try:
            usage = self.query("""
                SELECT thread# AS thread, sequence# AS sequence,
                       TO_CHAR(first_time, 'YYYY-MM-DD HH24:MI:SS') AS first_time,
                       name AS archive_log_file,
                       ROUND(blocks * block_size / 1024 / 1024, 2) AS size_mb,
                       status
                FROM v$archived_log
                WHERE dest_id = 1
                ORDER BY sequence# DESC
            """)
            # 归档目标使用率
            dest = self.query("""
                SELECT name AS DESTINATION,
                       ROUND(space_used / 1024 / 1024, 2) AS USED_MB,
                       ROUND(space_limit / 1024 / 1024, 2) AS LIMIT_MB,
                       ROUND(space_used / space_limit * 100, 2) AS USED_PCT
                FROM v$recovery_file_dest
            """)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'[OracleArch] usage rows={len(usage)}, dest rows={len(dest)}, dest_data={dest}')
            return {
                'archive_logs': usage[:20],
                'recovery_dest': dest[0] if dest else {}
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'[OracleArch] 异常: {e}')
            return {'archive_logs': [], 'recovery_dest': {}}

    def get_lock_info(self):
        return self.query("""
            SELECT s.sid, s.serial#, s.username, s.status,
                   l.type, l.id1, l.id2, l.lmode, l.request
            FROM v$lock l
            JOIN v$session s ON l.sid = s.sid
            WHERE l.request > 0
            ORDER BY s.sid
        """)

    def get_slow_queries(self):
        """获取最耗资源的 SQL（Top 50）"""
        try:
            return self.query("""
                SELECT * FROM (
                    SELECT sql_id, executions,
                           ROUND(elapsed_time / 1000000, 2) AS total_seconds,
                           ROUND(elapsed_time / executions / 1000000, 4) AS avg_seconds,
                           ROUND(buffer_gets / executions) AS avg_buffer_gets,
                           SUBSTR(sql_text, 1, 200) AS sql_text
                    FROM v$sql
                    WHERE executions > 0
                    ORDER BY elapsed_time DESC
                ) WHERE ROWNUM < 50
            """)
        except:
            return []


def get_connector(config):
    """根据配置获取连接器"""
    db_type = config.get('db_type', 'MYSQL').upper()
    if db_type == 'MSSQL':
        return MSSQLConnector(config)
    elif db_type == 'ORACLE':
        return OracleConnector(config)
    else:
        return MySQLConnector(config)


def get_connector_from_asset(asset):
    """从资产信息构建连接器"""
    # 优先使用Asset模型的直接字段
    host = asset.ip_address or _get_field(asset, 'db_host') or _get_field(asset, 'host_address') or 'localhost'
    port = asset.port or _get_field(asset, 'db_port') or '3306'
    username = asset.username or _get_field(asset, 'db_username') or ''
    password = asset.password or _get_field(asset, 'db_password') or ''
    database = asset.database or _get_field(asset, 'db_name') or _get_field(asset, 'database_name') or ''
    
    config = {
        'host': host,
        'port': port,
        'database': database,
        'username': username,
        'password': password,
        'db_type': _get_field(asset, 'database_type') or (asset.db_type.upper() if asset.db_type else ''),
    }

    # 如果 database_type 字段为空，才从资产名猜测
    if not config['db_type']:
        name = asset.asset_name.lower()
        if 'mssql' in name or 'sql server' in name:
            config['db_type'] = 'MSSQL'
        elif 'oracle' in name:
            config['db_type'] = 'ORACLE'
        elif 'mysql' in name or 'mariadb' in name:
            config['db_type'] = 'MYSQL'
        else:
            config['db_type'] = 'MYSQL'

    # 设置默认端口和数据库名
    if config['db_type'] == 'MSSQL':
        if not config['port']: config['port'] = '1433'
        if not config['database']: config['database'] = 'master'
    elif config['db_type'] == 'ORACLE':
        if not config['port']: config['port'] = '1521'
    elif config['db_type'] == 'MYSQL':
        if not config['port']: config['port'] = '3306'
        if not config['database']: config['database'] = 'mysql'

    return get_connector(config)


def _get_field(asset, field_code):
    try:
        data = AssetData.objects.filter(asset=asset, field__field_code=field_code).first()
        return data.get_value() if data else None
    except:
        return None


# ========== 巡检模板定义 ==========

def _first_epoch(rows):
    """从 SQL 查询结果里取第一个值并转 float。

    各引擎结果形态不一（MySQL DictCursor 得 dict、MSSQL tsql 文本解析、Oracle
    sqlplus COLSEP 解析），列名大小写也不保证，所以取「首行的首个值」最稳。
    """
    if not rows:
        return None
    try:
        row = rows[0]
        val = list(row.values())[0] if isinstance(row, dict) else row[0]
        return float(val)
    except (TypeError, ValueError, IndexError, KeyError, AttributeError):
        return None


INSPECTION_TEMPLATES = {
    'MYSQL': {
        'name': 'MySQL 巡检',
        'checks': [
            {'code': 'DB_CONNECTION', 'name': '数据库连接', 'method': 'check_connection'},
            {'code': 'TIME_SYNC', 'name': '时间同步', 'method': 'get_server_time'},
            {'code': 'DB_VERSION', 'name': '数据库版本', 'method': 'get_server_info'},
            {'code': 'DB_SIZE', 'name': '数据库大小', 'method': 'get_database_sizes'},
            {'code': 'SESSIONS', 'name': '会话信息', 'method': 'get_session_info'},
            {'code': 'BUFFER_HIT', 'name': '缓冲池命中率', 'method': 'get_performance_info'},
            {'code': 'SLOW_QUERIES', 'name': '慢查询', 'method': 'get_slow_queries'},
            {'code': 'BACKUP', 'name': '备份状态', 'method': 'get_backup_info'},
            {'code': 'ERROR_LOG', 'name': '错误日志', 'method': 'get_error_logs'},
        ]
    },
    'MSSQL': {
        'name': 'MSSQL 巡检',
        'checks': [
            {'code': 'DB_CONNECTION', 'name': '数据库连接', 'method': 'check_connection'},
            {'code': 'TIME_SYNC', 'name': '时间同步', 'method': 'get_server_time'},
            {'code': 'DB_VERSION', 'name': '数据库版本', 'method': 'get_server_info'},
            {'code': 'DB_LIST', 'name': '数据库列表', 'method': 'get_databases'},
            {'code': 'DB_SIZE', 'name': '数据库文件大小', 'method': 'get_database_sizes'},
            {'code': 'SESSIONS', 'name': '会话信息', 'method': 'get_session_info'},
            {'code': 'BUFFER_HIT', 'name': '缓冲命中率', 'method': 'get_performance_info'},
            {'code': 'BACKUP', 'name': '备份状态', 'method': 'get_backup_info'},
            {'code': 'SLOW_QUERIES', 'name': '慢查询', 'method': 'get_slow_queries'},
            {'code': 'LOCK_INFO', 'name': '锁信息', 'method': 'get_lock_info'},
        ]
    },
    'ORACLE': {
        'name': 'Oracle 巡检',
        'checks': [
            {'code': 'DB_CONNECTION', 'name': '数据库连接', 'method': 'check_connection'},
            {'code': 'TIME_SYNC', 'name': '时间同步', 'method': 'get_server_time'},
            {'code': 'DB_VERSION', 'name': '数据库版本', 'method': 'get_server_info'},
            {'code': 'TABLESPACE', 'name': '表空间使用率', 'method': 'get_tablespace_info'},
            {'code': 'DB_SIZE', 'name': '数据文件大小', 'method': 'get_database_sizes'},
            {'code': 'SESSIONS', 'name': '会话信息', 'method': 'get_session_info'},
            {'code': 'BUFFER_HIT', 'name': '缓冲命中率', 'method': 'get_performance_info'},
            {'code': 'ARCHIVE_LOG', 'name': '归档日志', 'method': 'get_archive_logs'},
            {'code': 'BACKUP', 'name': 'RMAN备份', 'method': 'get_backup_info'},
            {'code': 'ERROR_LOG', 'name': '错误日志(ORA-)', 'method': 'get_error_logs'},
            {'code': 'SLOW_SQL', 'name': '资源消耗SQL', 'method': 'get_slow_queries'},
            {'code': 'LOCK_INFO', 'name': '锁信息', 'method': 'get_lock_info'},
        ]
    }
}


if __name__ == '__main__':
    # 测试
    config = {
        'host': '172.26.11.50',
        'port': '1433',
        'database': 'master',
        'username': 'sa',
        'password': 'Beyondit@123',
        'db_type': 'MSSQL'
    }
    conn = get_connector(config)
    print(conn.check_connection())
    print(conn.get_server_info())
    print(conn.get_database_sizes())
