#!/bin/bash
# SNMP连通性测试脚本
# 在真实Linux服务器上运行

set -e

TARGET_HOST="${1:-127.0.0.1}"
COMMUNITY="${2:-public}"
PORT="${3:-161}"

echo "=========================================="
echo "SNMP连通性测试"
echo "=========================================="
echo "目标: $TARGET_HOST:$PORT"
echo "社区: $COMMUNITY"
echo ""

# 检查snmpwalk是否存在
if ! command -v snmpwalk &> /dev/null; then
    echo "snmpwalk未安装，尝试安装..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y -qq snmp snmpd
    elif command -v yum &> /dev/null; then
        sudo yum install -y net-snmp-utils
    fi
fi

echo "1. 测试UDP端口连通性..."
if timeout 3 nc -zvu $TARGET_HOST $PORT 2>&1; then
    echo "   ✓ 端口可达"
else
    echo "   ✗ 端口不可达，尝试直接发送SNMP包..."
fi

echo ""
echo "2. SNMP GET测试 (sysDescr)..."
snmpget -v 2c -c $COMMUNITY -t 3 -r 1 $TARGET_HOST:$PORT 1.3.6.1.2.1.1.1.0 2>&1 && echo "   ✓ GET成功" || echo "   ✗ GET失败"

echo ""
echo "3. SNMP GET测试 (sysName)..."
snmpget -v 2c -c $COMMUNITY -t 3 -r 1 $TARGET_HOST:$PORT 1.3.6.1.2.1.1.5.0 2>&1 && echo "   ✓ GET成功" || echo "   ✗ GET失败"

echo ""
echo "4. SNMP WALK测试 (接口状态)..."
snmpwalk -v 2c -c $COMMUNITY -t 5 -r 1 $TARGET_HOST:$PORT 1.3.6.1.2.1.2.2.1.8 2>&1 | head -10 && echo "   ✓ WALK成功" || echo "   ✗ WALK失败"

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
