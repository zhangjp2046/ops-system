#!/usr/bin/env python3
"""
MSSQL 数据库连接器（基于 FreeTDS tsql）
解决了 pymssql 和 ODBC Driver 18 的 TLS 兼容性问题
"""
import subprocess
import os
import re


class MSSQLConnector:
    """MSSQL 数据库连接器 - 使用 FreeTDS tsql"""
    
    def __init__(self, host, port=1433, user='sa', password='', database='master'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._setup_freetds()
    
    def _setup_freetds(self):
        """配置 FreeTDS 环境"""
        conf_path = '/tmp/freetds.conf'
        if not os.path.exists(conf_path):
            with open(conf_path, 'w') as f:
                f.write('[global]\n    tds version = 7.4\n    encryption = off\n    client charset = UTF-8\n')
        os.environ['FREETDSCONF'] = conf_path
    
    def query(self, sql):
        """执行 SQL 查询，返回结果列表"""
        cmd = f'TDSVER=7.4 tsql -H {self.host} -p {self.port} -U {self.user} -P "{self.password}" -D {self.database}'
        proc = subprocess.Popen(
            cmd, shell=True, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={**os.environ, 'FREETDSCONF': '/tmp/freetds.conf'}
        )
        stdout, stderr = proc.communicate(input=f'{sql}\nGO\n')
        
        # 解析 tsql 输出
        results = []
        lines = stdout.strip().split('\n')
        if len(lines) < 3:
            return results
        
        # 找到数据行（跳过表头和分隔线）
        data_started = False
        headers = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('locale') or line.startswith('using') or line.startswith('Setting'):
                continue
            if '(row' in line or '1>' in line or '2>' in line:
                continue
            if not data_started:
                headers = re.split(r'\t', line)
                data_started = True
                continue
            if data_started and line:
                values = re.split(r'\t', line)
                if len(values) == len(headers):
                    results.append(dict(zip(headers, values)))
        return results
    
    def check_connection(self):
        """测试连接"""
        try:
            result = self.query('SELECT 1 AS test')
            return {'status': 'success', 'message': '连接正常'}
        except Exception as e:
            return {'status': 'failed', 'message': str(e)}
    
    def get_server_info(self):
        """获取服务器信息"""
        try:
            result = self.query('SELECT @@VERSION AS version, @@SERVERNAME AS server_name, @@MAX_CONNECTIONS AS max_connections')
            if result:
                return result[0]
        except:
            pass
        return {}
    
    def get_databases(self):
        """获取数据库列表"""
        try:
            return self.query('SELECT name, state_desc, recovery_model_desc FROM sys.databases ORDER BY name')
        except:
            return []
    
    def get_active_sessions(self):
        """获取活跃会话数"""
        try:
            result = self.query('SELECT COUNT(*) AS cnt FROM sys.dm_exec_sessions WHERE is_user_process = 1')
            if result:
                return int(result[0].get('cnt', 0))
        except:
            pass
        return 0
    
    def get_backup_info(self):
        """获取备份信息"""
        try:
            return self.query('''
                SELECT TOP 5 database_name, backup_start_date, 
                       CAST(backup_size/1024/1024 AS DECIMAL(10,2)) AS size_mb
                FROM msdb.dbo.backupset ORDER BY backup_start_date DESC
            ''')
        except:
            return []


if __name__ == '__main__':
    conn = MSSQLConnector('172.26.11.50', user='sa', password='Beyondit@123')
    
    print('=== 连接测试 ===')
    print(conn.check_connection())
    
    print('\n=== 服务器信息 ===')
    print(conn.get_server_info())
    
    print('\n=== 数据库列表 ===')
    for db in conn.get_databases():
        print(f"  {db.get('name')}: {db.get('state_desc')}")
    
    print('\n=== 活跃会话 ===')
    print(conn.get_active_sessions())
    
    print('\n=== 备份信息 ===')
    for bk in conn.get_backup_info():
        print(f"  {bk.get('database_name')}: {bk.get('backup_start_date')} ({bk.get('size_mb')} MB)")
