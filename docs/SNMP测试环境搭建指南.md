# SNMP测试环境搭建指南

## 概述

本文档说明如何在Ubuntu真实环境中搭建SNMP测试环境，用于开发和测试运维系统的SNMP监控功能。

---

## 快速开始（推荐）

### 步骤1：上传脚本到Ubuntu服务器

```bash
# 在开发环境执行
scp -r scripts/* ubuntu@your-server:/tmp/

# 或者复制到项目目录
scp -r scripts/ ubuntu@your-server:/opt/ops-system/
```

### 步骤2：在Ubuntu上运行一键部署

```bash
# SSH登录到Ubuntu服务器
ssh ubuntu@your-server

# 进入脚本目录
cd /opt/ops-system/scripts

# 设置执行权限
chmod +x deploy_snmp_test_env.sh

# 运行部署脚本
sudo ./deploy_snmp_test_env.sh
```

### 步骤3：验证SNMP服务

```bash
# 在Ubuntu服务器上执行
snmpwalk -v 2c -c public localhost 1.3.6.1.2.1.1
```

---

## 方案一：使用系统SNMP服务（推荐）

### 安装和配置

```bash
# 安装SNMP
sudo apt-get update
sudo apt-get install -y snmpd snmp

# 配置
sudo cp /etc/snmp/snmpd.conf /etc/snmp/snmpd.conf.bak
sudo bash -c 'cat > /etc/snmp/snmpd.conf << EOF
rocommunity public
rwcommunity private
agentAddress 161
syslocation "Test DataCenter"
syscontact admin@test.com
EOF'

# 启动服务
sudo systemctl restart snmpd
sudo systemctl enable snmpd

# 验证
snmpget -v 2c -c public localhost 1.3.6.1.2.1.1.1.0
```

### 防火墙设置

```bash
# 开放UDP 161端口
sudo ufw allow 161/udp

# 或者使用firewalld
sudo firewall-cmd --permanent --add-port=161/udp
sudo firewall-cmd --reload
```

---

## 方案二：使用Python Mock服务器（无需安装SNMP）

如果无法安装SNMP服务，使用Python Mock服务器：

```bash
# 进入目录
cd /opt/ops-system/scripts

# 运行Mock服务器
sudo python3 simple_snmp_mock.py

# 后台运行
sudo python3 simple_snmp_mock.py &
sudo nohup python3 simple_snmp_mock.py > /var/log/snmp_mock.log 2>&1 &
```

### 测试Mock服务器

```bash
# 先安装snmpwalk
sudo apt-get install -y snmp

# 运行测试脚本
chmod +x test_snmp_mock.sh
./test_snmp_mock.sh localhost public
```

---

## 在开发环境中测试

### 1. 更新资产IP

在开发环境的数据库中更新网络设备的IP：

```bash
cd /home/zhang/botcode/ops-system/backend
source venv/bin/activate
python manage.py shell << 'EOF'
from apps.assets.models import Asset

# 更新网络设备的IP地址
asset = Asset.objects.filter(asset_code='NET-001').first()
if asset:
    # 假设Ubuntu服务器IP是 192.168.1.100
    asset.location = '192.168.1.100'
    asset.save()
    print(f"已更新 {asset.asset_name} 的IP为: {asset.location}")
EOF
```

### 2. 执行SNMP监控任务

```bash
cd /home/zhang/botcode/ops-system/backend
source venv/bin/activate
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.monitoring.executors import MonitoringExecutor
from apps.monitoring.models import MonitoringTask

task = MonitoringTask.objects.get(task_type='snmp', asset__asset_code='NET-001')
print(f'执行任务: {task.name}')
result = MonitoringExecutor.execute_task(task.id)
print(f'结果: {result.status}')
print(f'可用率: {result.uptime}%')
"
```

---

## 常用SNMP OID参考

| OID | 名称 | 说明 | 示例值 |
|-----|------|------|--------|
| 1.3.6.1.2.1.1.1.0 | sysDescr | 系统描述 | "Ubuntu 22.04" |
| 1.3.6.1.2.1.1.3.0 | sysUpTime | 运行时间 | Timeticks |
| 1.3.6.1.2.1.1.5.0 | sysName | 主机名 | "server-01" |
| 1.3.6.1.2.1.1.6.0 | sysLocation | 位置 | "DataCenter-A" |
| 1.3.6.1.2.1.2.1.0 | ifNumber | 接口数量 | 24 |
| 1.3.6.1.2.1.2.2.1.8.X | ifStatus | 接口状态 | 1(up)/2(down) |
| 1.3.6.1.2.1.2.2.1.2.X | ifDescr | 接口描述 | "GigabitEthernet1/0/1" |
| 1.3.6.1.2.1.2.2.1.5.X | ifSpeed | 接口速度 | 1000000000 |
| 1.3.6.1.4.1.2021.11.11.0 | cpuUsage | CPU使用率 | 15 (%) |
| 1.3.6.1.4.1.2021.4.5.0 | memTotal | 内存总量 | 32814592 (KB) |
| 1.3.6.1.4.1.2021.4.6.0 | memAvail | 可用内存 | 16000000 (KB) |

---

## 故障排查

### 问题1：端口被占用

```
Error: Address already in use
```

解决方案：
```bash
# 查找占用进程
sudo netstat -ulnp | grep 161

# 停止现有SNMP服务
sudo systemctl stop snmpd

# 或杀死进程
sudo kill <PID>
```

### 问题2：防火墙阻止

```
Timeout: No Response from localhost:161
```

解决方案：
```bash
# 开放端口
sudo ufw allow 161/udp

# 或关闭防火墙测试
sudo ufw disable
```

### 问题3：权限不足

```
Permission denied
```

解决方案：
```bash
# 使用sudo运行
sudo python3 simple_snmp_mock.py

# 或给脚本执行权限
chmod +x simple_snmp_mock.py
```

---

## 验证测试结果

部署完成后，在开发环境中检查：

```python
# 查看监控结果
result = MonitoringResult.objects.filter(task__task_type='snmp').latest('start_time')
print(f"状态: {result.status}")
print(f"可用率: {result.uptime}%")
print(f"原始数据: {result.raw_data}")
```

---

## 清理环境

```bash
# 停止SNMP服务
sudo systemctl stop snmpd

# 卸载SNMP
sudo apt-get remove --purge -y snmpd snmp

# 关闭防火墙端口
sudo ufw delete allow 161/udp
```
