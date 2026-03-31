#!/bin/bash
# 监控任务执行脚本 - 每分钟运行
cd /home/zhang/botcode/ops-system/backend
source venv/bin/activate
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from apps.monitoring.executors import MonitoringExecutor
results = MonitoringExecutor.execute_all_enabled_tasks()
print(f'执行了 {len(results)} 个监控任务')
"
