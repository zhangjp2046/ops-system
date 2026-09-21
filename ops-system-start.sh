#!/bin/bash
# ops-system 快速启动脚本
# 一键启动前端 + 后端

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "=== ops-system 快速启动 ==="
echo ""

# 查找可用的 Django 环境（优先使用已安装的环境，避免重复安装）
if [ -f "/home/zhang/.openclaw/workspace/fixed-asset-system/src/backend/venv/bin/python" ]; then
    PYTHON_BIN="/home/zhang/.openclaw/workspace/fixed-asset-system/src/backend/venv/bin/python"
    echo "[INFO] 使用已安装的 Python 环境 (fixed-asset-system venv)"
elif [ -f "backend/venv/bin/python" ]; then
    PYTHON_BIN="backend/venv/bin/python"
else
    echo "[1/6] 创建虚拟环境..."
    python3 -m venv backend/venv
    PYTHON_BIN="backend/venv/bin/python"
fi

# 安装前端依赖
echo "[2/6] 安装前端依赖..."
cd "$PROJECT_ROOT/frontend"
if [ ! -d "node_modules" ]; then
    npm install
fi

# 安装后端依赖（如使用自带 venv）
if [ ! -f "/home/zhang/.openclaw/workspace/fixed-asset-system/src/backend/venv/bin/python" ]; then
    echo "[3/6] 安装后端依赖..."
    cd "$PROJECT_ROOT/backend"
    pip install -r requirements.txt -q 2>/dev/null || pip install -r requirements.txt
fi

# 启动后端（设置 PYTHONPATH 确保加载正确的 config）
echo "[4/6] 启动后端 (端口 8002)..."
cd "$PROJECT_ROOT/backend"
export PYTHONPATH="$PROJECT_ROOT/backend:$PYTHONPATH"
export DJANGO_SETTINGS_MODULE=config.settings
nohup $PYTHON_BIN manage.py runserver 0.0.0.0:8002 > /tmp/ops-backend.log 2>&1 &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 启动前端
echo "[5/6] 启动前端 (端口 3000)..."
cd "$PROJECT_ROOT/frontend"
nohup npm run dev > /tmp/ops-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "前端 PID: $FRONTEND_PID"

echo ""
echo "=== 启动完成 ==="
echo ""
echo "  后端: http://localhost:8002/api"
echo "  前端: http://localhost:3000"
echo "  API文档: http://localhost:8002/swagger/"
echo ""
echo "  后端日志: tail -f /tmp/ops-backend.log"
echo "  前端日志: tail -f /tmp/ops-frontend.log"
echo ""
echo "  默认账号: admin / admin123"
echo ""
echo "停止服务:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
