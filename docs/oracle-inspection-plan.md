# Oracle 数据库巡检规划

## 连接信息

需要在资产表单中配置：
- 采集协议：oracle
- 端口：1521
- 用户名：system（或 sys）
- 密码：xxx
- 数据库名：服务名（如 ORCL、orcl）

## 前置条件

```bash
# 安装 sqlplus 客户端
# 方式1：安装 Oracle Instant Client
# 方式2：如果已有 Oracle 数据库，直接用自带的 sqlplus

# 测试连接
sqlplus -S user/password@host:1521/service_name
```

## 巡检检查项

### 1. 数据库连接 ✅
- SQL: `SELECT 1 FROM dual`
- 判断：连接成功/失败

### 2. 数据库版本 ✅
- SQL: `SELECT banner FROM v$version WHERE ROWNUM = 1`
- 附加：`SELECT instance_name, status, startup_time FROM v$instance`

### 3. 实例状态 ✅
- SQL: `SELECT instance_name, status, database_status, logins FROM v$instance`
- 判断：status=OPENED, database_status=ACTIVE
- 异常：STARTED/MOUNTED/NOMOUNT

### 4. 表空间使用率 ⚠️ 重点
- SQL:
```sql
SELECT df.tablespace_name,
       ROUND(df.total_mb, 2) AS total_mb,
       ROUND(df.total_mb - NVL(fs.free_mb, 0), 2) AS used_mb,
       ROUND(NVL(fs.free_mb, 0), 2) AS free_mb,
       ROUND((df.total_mb - NVL(fs.free_mb, 0)) / df.total_mb * 100, 2) AS used_pct
FROM (SELECT tablespace_name, SUM(bytes)/1024/1024 AS total_mb FROM dba_data_files GROUP BY tablespace_name) df
LEFT JOIN (SELECT tablespace_name, SUM(bytes)/1024/1024 AS free_mb FROM dba_free_space GROUP BY tablespace_name) fs
ON df.tablespace_name = fs.tablespace_name
ORDER BY used_pct DESC
```
- 阈值：> 80% 警告，> 90% 危险
- 特别关注：SYSTEM, SYSAUX, UNDO

### 5. 数据文件 ✅
- SQL:
```sql
SELECT file_name, tablespace_name,
       ROUND(bytes/1024/1024, 2) AS size_mb,
       autoextensible,
       ROUND(maxbytes/1024/1024, 2) AS max_size_mb
FROM dba_data_files ORDER BY tablespace_name
```

### 6. 会话信息 ✅
- SQL:
```sql
SELECT status, COUNT(*) AS cnt FROM v$session WHERE type = 'USER' GROUP BY status
```
- 阈值：活跃会话 > 100 危险，> 50 警告

### 7. 缓冲命中率 ✅
- SQL:
```sql
SELECT ROUND((1 - (phy.value / (log.value + phy.value))) * 100, 2) AS buffer_hit_ratio
FROM v$sysstat log, v$sysstat phy
WHERE log.name = 'session logical reads' AND phy.name = 'physical reads'
```
- 阈值：< 95% 警告，< 90% 危险

### 8. SGA 信息 ✅
- SQL:
```sql
SELECT name, ROUND(value/1024/1024, 0) AS size_mb FROM v$sga
UNION ALL
SELECT 'TOTAL', ROUND(SUM(value)/1024/1024, 0) FROM v$sga
```

### 9. PGA 信息 ✅
- SQL:
```sql
SELECT name, ROUND(value/1024/1024, 0) AS size_mb
FROM v$pgastat WHERE name IN ('total PGA allocated', 'maximum PGA allocated', 'PGA target')
```

### 10. 归档日志 ⚠️ 重点
- 归档模式：
```sql
SELECT log_mode FROM v$database
```
- 归档目标使用率：
```sql
SELECT ROUND(space_used/space_limit*100, 2) AS used_pct,
       ROUND(space_used/1024/1024, 2) AS used_mb,
       ROUND(space_limit/1024/1024, 2) AS limit_mb
FROM v$recovery_file_dest
```
- 阈值：> 80% 警告，> 90% 危险
- 最近归档日志：
```sql
SELECT sequence#, TO_CHAR(first_time,'YYYY-MM-DD HH24:MI') AS time,
       ROUND(blocks*block_size/1024/1024, 2) AS size_mb
FROM v$archived_log WHERE dest_id=1 ORDER BY sequence# DESC
```

### 11. RMAN 备份 ✅
- SQL:
```sql
SELECT session_key, input_type, status,
       TO_CHAR(start_time, 'YYYY-MM-DD HH24:MI') AS start_time,
       ROUND(elapsed_seconds/60, 1) AS duration_min,
       ROUND(output_bytes/1024/1024, 2) AS size_mb
FROM v$rman_backup_job_details ORDER BY start_time DESC
```
- 阈值：最近7天无备份 警告

### 12. ORA- 错误日志 ⚠️ 重点
- SQL:
```sql
SELECT TO_CHAR(originating_timestamp, 'YYYY-MM-DD HH24:MI') AS time,
       message_text FROM v$diag_alert_ext
WHERE message_text LIKE 'ORA-%' ORDER BY originating_timestamp DESC
```
- 阈值：有 ORA-00600/ORA-07445 直接危险

### 13. 资源消耗 SQL ✅
- SQL:
```sql
SELECT sql_id, executions,
       ROUND(elapsed_time/1000000, 2) AS total_sec,
       ROUND(elapsed_time/executions/1000000, 4) AS avg_sec,
       ROUND(buffer_gets/executions) AS avg_buf_gets,
       SUBSTR(sql_text, 1, 150) AS sql_text
FROM v$sql WHERE executions > 0 ORDER BY elapsed_time DESC
```
- 阈值：平均执行时间 > 10秒 警告

### 14. 锁信息 ✅
- SQL:
```sql
SELECT s.sid, s.serial#, s.username, s.status,
       l.type, l.lmode, l.request
FROM v$lock l JOIN v$session s ON l.sid = s.sid
WHERE l.request > 0
```
- 阈值：有阻塞锁直接警告

### 15. 等待事件 ⭐ 新增
- SQL:
```sql
SELECT event, wait_class, total_waits,
       ROUND(time_waited_micro/1000000, 2) AS time_waited_sec
FROM v$system_event WHERE wait_class != 'Idle'
ORDER BY time_waited_micro DESC
```
- 关注：db file sequential read, log file sync, library cache lock

### 16. 硬解析率 ⭐ 新增
- SQL:
```sql
SELECT ROUND(hard.value/parse.value*100, 2) AS hard_parse_pct
FROM v$sysstat hard, v$sysstat parse
WHERE hard.name = 'parse count (hard)' AND parse.name = 'parse count (total)'
```
- 阈值：> 20% 警告，> 10% 关注

### 17. Undo 表空间 ⭐ 新增
- SQL:
```sql
SELECT tablespace_name,
       ROUND(SUM(bytes)/1024/1024, 0) AS size_mb,
       ROUND(SUM(DECODE(status, 'UNEXPIRED', bytes, 0))/1024/1024, 0) AS unexpired_mb,
       ROUND(SUM(DECODE(status, 'EXPIRED', bytes, 0))/1024/1024, 0) AS expired_mb
FROM dba_undo_extents GROUP BY tablespace_name
```

### 18. 临时表空间 ⭐ 新增
- SQL:
```sql
SELECT tablespace_name,
       ROUND(SUM(bytes_used)/1024/1024, 0) AS used_mb,
       ROUND(SUM(bytes_free)/1024/1024, 0) AS free_mb,
       ROUND(SUM(bytes_used)/(SUM(bytes_used)+SUM(bytes_free))*100, 1) AS used_pct
FROM dba_temp_free_space GROUP BY tablespace_name
```

---

## 阈值汇总

| 检查项 | 警告阈值 | 危险阈值 |
|--------|----------|----------|
| 表空间使用率 | > 80% | > 90% |
| 归档日志使用率 | > 80% | > 90% |
| 缓冲命中率 | < 95% | < 90% |
| 活跃会话 | > 50 | > 100 |
| 硬解析率 | > 10% | > 20% |
| 慢SQL平均时间 | > 5秒 | > 10秒 |
| RMAN备份天数 | > 3天 | > 7天 |
| ORA-错误 | 有普通ORA- | 有ORA-00600/07445 |
| Undo表空间 | > 80% | > 90% |
| 临时表空间 | > 80% | > 90% |

## 测试连接

```bash
# 测试 sqlplus 连接
sqlplus -S system/password@172.26.11.50:1521/ORCL << 'EOF'
SELECT instance_name, status, logins FROM v$instance;
EXIT;
EOF
```
