#!/bin/bash

# 运维系统启动脚本

echo "=== 运维管理系统启动脚本 ==="
echo ""

# 设置项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 检查Python虚拟环境
if [ ! -d "venv" ]; then
    echo "[1/4] 创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "[2/4] 激活虚拟环境..."
source venv/bin/activate

# 安装后端依赖
echo "[3/4] 安装后端依赖..."
cd backend
pip install -r requirements.txt -q

# 安装前端依赖
echo "[4/4] 安装前端依赖..."
cd ../frontend
if [ ! -d "node_modules" ]; then
    npm install
fi

echo ""
echo "=== 启动完成 ==="
echo ""
echo "后端运行: cd backend && python manage.py runserver"
echo "前端运行: cd frontend && npm run dev"
echo ""
echo "访问地址:"
echo "  前端: http://localhost:3000"
echo "  后端API: http://localhost:8000/api"
echo "  API文档: http://localhost:8000/swagger/"
echo ""
echo "默认账号: admin / admin123"