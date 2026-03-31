#!/bin/bash
#=============================================================================
# SNMP Mock服务器测试脚本
# 验证SNMP Mock服务器是否正常工作
#=============================================================================

set -e

SERVER_IP="${1:-127.0.0.1}"
COMMUNITY="${2:-public}"
PORT="${3:-161}"

echo "========================================"
echo "SNMP Mock服务器测试"
echo "========================================"
echo "目标: $SERVER_IP:$PORT"
echo "社区: $COMMUNITY"
echo ""

# 检查snmpwalk是否存在
if ! command -v snmpwalk &> /dev/null; then
    echo "安装snmpwalk..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq snmp snmp-mibs-downloader 2>/dev/null || true
    fi
fi

FAILED=0

# 测试1: 获取系统描述
echo "[测试1] 获取系统描述 (sysDescr)..."
if snmpget -v 2c -c "$COMMUNITY" -t 5 "$SERVER_IP:$PORT" 1.3.6.1.2.1.1.1.0 2>/dev/null; then
    echo "  ✓ 通过"
else
    echo "  ✗ 失败"
    FAILED=$((FAILED + 1))
fi

# 测试2: 获取系统名称
echo ""
echo "[测试2] 获取系统名称 (sysName)..."
if snmpget -v 2c -c "$COMMUNITY" -t 5 "$SERVER_IP:$PORT" 1.3.6.1.2.1.1.5.0 2>/dev/null; then
    echo "  ✓ 通过"
else
    echo "  ✗ 失败"
    FAILED=$((FAILED + 1))
fi

# 测试3: 获取接口数量
echo ""
echo "[测试3] 获取接口数量 (ifNumber)..."
if snmpget -v 2c -c "$COMMUNITY" -t 5 "$SERVER_IP:$PORT" 1.3.6.1.2.1.2.1.0 2>/dev/null; then
    echo "  ✓ 通过"
else
    echo "  ✗ 失败"
    FAILED=$((FAILED + 1))
fi

# 测试4: 获取接口状态
echo ""
echo "[测试4] 获取接口状态 (ifOperStatus)..."
if snmpwalk -v 2c -c "$COMMUNITY" -t 5 "$SERVER_IP:$PORT" 1.3.6.1.2.1.2.2.1.8 2>/dev/null | head -10; then
    echo "  ✓ 通过"
else
    echo "  ✗ 失败"
    FAILED=$((FAILED + 1))
fi

# 测试5: 获取接口描述
echo ""
echo "[测试5] 获取接口描述 (ifDescr)..."
if snmpwalk -v 2c -c "$COMMUNITY" -t 5 "$SERVER_IP:$PORT" 1.3.6.1.2.1.2.2.1.2 2>/dev/null | head -5; then
    echo "  ✓ 通过"
else
    echo "  ✗ 失败"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo "所有测试通过! ✓"
    echo ""
    echo "现在可以在开发环境中更新资产IP为: $SERVER_IP"
    echo "然后运行SNMP监控任务进行测试。"
else
    echo "有 $FAILED 个测试失败"
    echo ""
    echo "常见问题:"
    echo "1. 检查Mock服务器是否运行"
    echo "2. 检查防火墙是否开放 $PORT/udp"
    echo "3. 检查SNMP服务是否配置正确"
fi
echo "========================================"

exit $FAILED
