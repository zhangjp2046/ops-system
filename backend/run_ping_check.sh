#!/bin/bash
cd /home/zhang/botcode/ops-system/backend
source venv/bin/activate
python3 ping_check.py >> /tmp/ping_check.log 2>&1
