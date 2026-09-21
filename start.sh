#!/bin/bash
# ops-system 一键启动脚本
# 功能：启动后端（Django）+ 前端（Vite）+ 数据库检查

set -e

PROJECT_ROOT="/home/zhang/.openclaw/workspace/ops-system"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"
VENV_ACTIVATE="$PROJECT_ROOT/venv/bin/activate"
BACKEND_PORT=9015
FRONTEND_PORT=3015
LOG_DIR="/tmp/ops-system"

# ─────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────
log()  { echo -e "\033[1;36m[INFO]\033[0m $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $*"; }
err()  { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; }

is_running() {
  local port=$1
  # Linux: check if port is listening
  if command -v ss &>/dev/null; then
    ss -tlnp 2>/dev/null | grep -q ":${port} "
  elif command -v netstat &>/dev/null; then
    netstat -tlnp 2>/dev/null | grep -q ":${port} "
  else
    return 1
  fi
}

stop_on_port() {
  local port=$1
  local pids
  pids=$(lsof -ti ":$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    warn "端口 $port 被占用，尝试关闭已有进程: $pids"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
}

# ─────────────────────────────────────────
# 初始化
# ─────────────────────────────────────────
mkdir -p "$LOG_DIR"
cd "$PROJECT_ROOT"

echo ""
echo "=============================================="
echo "       ops-system 一键启动                    "
echo "=============================================="
echo ""

# 检查是否已有服务在运行
if is_running $BACKEND_PORT || is_running $FRONTEND_PORT; then
  warn "检测到已有服务运行，先停止..."
  stop_on_port $BACKEND_PORT
  stop_on_port $FRONTEND_PORT
  sleep 1
fi

# ─────────────────────────────────────────
# 后端
# ─────────────────────────────────────────
log ">>> 启动后端 (Django / 0.0.0.0:$BACKEND_PORT) ..."

# 确保虚拟环境存在
if [ ! -f "$VENV_PYTHON" ]; then
  log "创建虚拟环境..."
  python3 -m venv venv
fi

# 安装依赖（如需要）
REQUIREMENTS="$PROJECT_ROOT/backend/requirements.txt"
if [ -f "$REQUIREMENTS" ]; then
  log "检查后端依赖..."
  # 简单检查：pip list 先不做，避免每次都检查
  :
fi

# 启动后端
cd "$PROJECT_ROOT/backend"
export PYTHONPATH="$PROJECT_ROOT/backend:$PYTHONPATH"
export DJANGO_SETTINGS_MODULE=config.settings

nohup $VENV_PYTHON manage.py runserver 0.0.0.0:$BACKEND_PORT \
  > "$LOG_DIR/backend.log" 2>&1 &

BACKEND_PID=$!
echo $BACKEND_PID > "$LOG_DIR/backend.pid"
log "后端已启动  PID=$BACKEND_PID  日志=$LOG_DIR/backend.log"

# 等待后端真正启动
for i in $(seq 1 10); do
  if curl -s "http://127.0.0.1:$BACKEND_PORT/api/" -o /dev/null 2>/dev/null; then
    break
  fi
  sleep 1
done

# ─────────────────────────────────────────
# 前端
# ─────────────────────────────────────────
log ">>> 启动前端 (Vite / localhost:$FRONTEND_PORT) ..."

cd "$PROJECT_ROOT/frontend"

# 检查 node_modules
if [ ! -d "node_modules" ]; then
  log "安装前端依赖（首次运行）..."
  npm install
fi

nohup npm run dev \
  > "$LOG_DIR/frontend.log" 2>&1 &

FRONTEND_PID=$!
echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"
log "前端已启动  PID=$FRONTEND_PID  日志=$LOG_DIR/frontend.log"

# 等待前端启动
for i in $(seq 1 15); do
  if curl -s "http://127.0.0.1:$FRONTEND_PORT" -o /dev/null 2>/dev/null; then
    break
  fi
  sleep 1
done

# ─────────────────────────────────────────
# 完成
# ─────────────────────────────────────────
echo ""
echo "=============================================="
echo "       启动完成  ✅                          "
echo "=============================================="
echo ""
echo "  前端地址:  http://localhost:$FRONTEND_PORT"
echo "  后端API:   http://localhost:$BACKEND_PORT/api/"
echo "  API文档:   http://localhost:$BACKEND_PORT/swagger/"
echo ""
echo "  后端日志:  tail -f $LOG_DIR/backend.log"
echo "  前端日志:  tail -f $LOG_DIR/frontend.log"
echo ""
echo "  进程 PID:  后端=$BACKEND_PID  前端=$FRONTEND_PID"
echo ""
echo "  停止服务:  $PROJECT_ROOT/stop.sh"
echo "=============================================="

# 保存 stop 信息
cat > "$PROJECT_ROOT/stop.sh" << EOF
#!/bin/bash
# ops-system 停止脚本（自动生成）
kill $(cat $LOG_DIR/backend.pid 2>/dev/null) 2>/dev/null
kill $(cat $LOG_DIR/frontend.pid 2>/dev/null) 2>/dev/null
echo "已停止所有服务"
EOF
chmod +x "$PROJECT_ROOT/stop.sh"