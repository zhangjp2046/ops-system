#!/bin/bash
#=============================================================================
# SNMP测试环境一键部署脚本
# 在Ubuntu真实环境中运行，用于测试运维系统的SNMP监控功能
# 
# 使用方法:
#   chmod +x deploy_snmp_test_env.sh
#   ./deploy_snmp_test_env.sh
#=============================================================================

set -e

echo "========================================"
echo "SNMP测试环境一键部署"
echo "========================================"
echo ""

# 检测是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用sudo运行此脚本:"
    echo "  sudo $0"
    exit 1
fi

# 获取服务器IP
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "服务器IP: $SERVER_IP"
echo ""

#----------------------------------------------------------------------------
# 步骤1: 安装SNMP服务
#----------------------------------------------------------------------------
echo "[1/4] 安装SNMP服务..."
apt-get update -qq
apt-get install -y -qq snmpd snmp snmp-mibs-downloader

#----------------------------------------------------------------------------
# 步骤2: 配置SNMP
#----------------------------------------------------------------------------
echo "[2/4] 配置SNMP服务..."

# 备份原配置
cp /etc/snmp/snmpd.conf /etc/snmp/snmpd.conf.bak 2>/dev/null || true

# 创建测试配置
cat > /etc/snmp/snmpd.conf << 'EOF'
# SNMP v2c配置
rocommunity public
rwcommunity private

# 监听所有接口
agentAddress 161

# 系统信息
syslocation "Test Data Center"
syscontact "admin@test.com"

# 扩展MIB
extend .1.3.6.1.4.1.2021.11.11.0 cpu_idle /bin/cat /proc/loadavg
extend .1.3.6.1.4.1.2021.4.5.0 mem_total /bin/cat /proc/meminfo | head -1 | awk '{print $2}'
extend .1.3.6.1.4.1.2021.4.6.0 mem_avail /bin/cat /proc/meminfo | head -2 | tail -1 | awk '{print $2}'
EOF

#----------------------------------------------------------------------------
# 步骤3: 启动SNMP服务
#----------------------------------------------------------------------------
echo "[3/4] 启动SNMP服务..."

# 停止现有服务
systemctl stop snmpd 2>/dev/null || true

# 启动服务
systemctl start snmpd
systemctl enable snmpd

# 等待服务启动
sleep 2

# 检查服务状态
if systemctl is-active --quiet snmpd; then
    echo "  ✓ SNMP服务运行中"
else
    echo "  ✗ SNMP服务启动失败，查看日志:"
    journalctl -u snmpd -n 10 --no-pager
    exit 1
fi

#----------------------------------------------------------------------------
# 步骤4: 测试SNMP
#----------------------------------------------------------------------------
echo "[4/4] 测试SNMP功能..."

# 测试本地SNMP
echo ""
echo "测试1: 获取系统描述..."
snmpget -v 2c -c public localhost 1.3.6.1.2.1.1.1.0

echo ""
echo "测试2: 获取系统名称..."
snmpget -v 2c -c public localhost 1.3.6.1.2.1.1.5.0

echo ""
echo "测试3: 获取接口数量..."
snmpget -v 2c -c public localhost 1.3.6.1.2.1.2.1.0

echo ""
echo "测试4: 获取接口状态(前5个)..."
snmpwalk -v 2c -c public localhost 1.3.6.1.2.1.2.2.1.8 | head -5

echo ""
echo "测试5: CPU空闲率(UCD-SMI)..."
snmpget -v 2c -c public localhost 1.3.6.1.4.1.2021.11.11.0

#----------------------------------------------------------------------------
# 输出结果
#----------------------------------------------------------------------------
echo ""
echo "========================================"
echo "部署完成!"
echo "========================================"
echo ""
echo "SNMP服务信息:"
echo "  地址: $SERVER_IP:161"
echo "  社区名(只读): public"
echo "  社区名(读写): private"
echo ""
echo "常用测试命令:"
echo "  # 获取系统信息"
echo "  snmpget -v 2c -c public $SERVER_IP 1.3.6.1.2.1.1.1.0"
echo ""
echo "  # 获取接口状态"
echo "  snmpwalk -v 2c -c public $SERVER_IP 1.3.6.1.2.1.2.2.1.8"
echo ""
echo "  # 获取CPU信息"
echo "  snmpwalk -v 2c -c public $SERVER_IP 1.3.6.1.4.1.2021.11"
echo ""
echo "  # 获取内存信息"
echo "  snmpwalk -v 2c -c public $SERVER_IP 1.3.6.1.4.1.2021.4"
echo ""
echo "防火墙设置(如果需要):"
echo "  sudo ufw allow 161/udp"
echo ""
echo "查看服务日志:"
echo "  sudo journalctl -u snmpd -f"
echo ""
