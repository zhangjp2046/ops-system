#!/usr/bin/env python3
import os
os.environ['TDS_VERSION'] = '7.4'
os.environ['TDSDUMP'] = '/tmp/tds.log'  # 开启调试日志

import pymssql

print("尝试连接...")
try:
    conn = pymssql.connect(
        server='192.168.1.11',
        port=1433,
        user='sa',
        password='abc123',
        database='',
        login_timeout=10
    )
    print("连接成功！")
    conn.close()
except Exception as e:
    print(f"连接失败: {e}")

# 查看调试日志
print("\n--- TDS 日志 ---")
with open('/tmp/tds.log', 'r') as f:
    print(f.read())