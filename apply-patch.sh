#!/bin/bash
# ===================================================
# ops-system 一键补丁更新脚本
# 用法:
#   ./apply-patch.sh                # 自动检测中心地址并更新
#   ./apply-patch.sh --check        # 仅检查版本
#   ./apply-patch.sh --url=http://...   # 指定中心端地址
#   ./apply-patch.sh --force        # 强制重新下载
# ===================================================
set -e

BACKEND_DIR="$(cd "$(dirname "$0")/backend" && pwd 2>/dev/null || echo "")"
if [ ! -d "$BACKEND_DIR" ]; then
    echo "[错误] 请在 ops-system 根目录运行此脚本"
    exit 1
fi

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  ops-system 补丁更新工具${NC}"
echo -e "${CYAN}========================================${NC}"

# ---- 检测中心端地址 ----
detect_center_url() {
    local venv="$BACKEND_DIR/venv"
    if [ ! -f "$venv/bin/activate" ]; then
        echo "" >&2
        return
    fi
    local result
    result=$(cd "$BACKEND_DIR" && source "$venv/bin/activate" 2>/dev/null && python -c "
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath('manage.py')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from apps.system.models import SystemSetting
url = SystemSetting.get('push.center_url', '')
if url:
    url = url.rstrip('/') + '/api/collector/patches/'
print(url or '')
" 2>/dev/null)
    echo "$result"
}

CENTER_URL=""
for arg in "$@"; do
    case "$arg" in --url=*) CENTER_URL="${arg#--url=}";; esac
done

if [ -z "$CENTER_URL" ]; then
    CENTER_URL=$(detect_center_url)
fi

if [ -z "$CENTER_URL" ]; then
    echo -e "${RED}[错误] 未检测到中心端地址${NC}"
    echo "  请通过 --url=http://你的centerIP:端口 指定"
    echo "  或在系统设置中配置 push.center_url"
    exit 1
fi

# 补全 API 路径（如果传的是中心根地址）
CENTER_URL="${CENTER_URL%/}"
if ! echo "$CENTER_URL" | grep -q '/patches'; then
    CENTER_URL="$CENTER_URL/api/collector/patches/"
fi
# 确保末尾有 /，Django 路由需要
CENTER_URL="${CENTER_URL%/}/"

# ---- 获取本地版本号 ----
CACHE_DIR="$HOME/.openclaw/patches"
LOCAL_VER=""
VER_FILE="$CACHE_DIR/patch_version.txt"
if [ -f "$VER_FILE" ]; then
    LOCAL_VER=$(cat "$VER_FILE" | tr -d ' \n')
fi

# ---- 检查更新 ----
echo -e "${YELLOW}正在检查更新...${NC}"
CHECK_URL="$CENTER_URL?version=$LOCAL_VER"
echo "  请求: $CHECK_URL"

RESP=$(curl -s "$CHECK_URL" 2>/dev/null) || { echo -e "${RED}[错误] 无法连接到中心端${NC}"; exit 1; }

if ! echo "$RESP" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    echo -e "${RED}[错误] 中心端返回了非预期的响应${NC}"
    echo "  可能是 push.center_url 配置地址不正确"
    echo "  提示: 应指向 ops-center 地址，而非 ops-system 自身"
    echo "  响应内容前100字符: $(echo "$RESP" | head -c 100)"
    exit 1
fi

if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('needs_update') else 1)" 2>/dev/null; then
    LATEST_VER=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['latest_version'])")
    echo -e "${GREEN}发现新版本: $LOCAL_VER → $LATEST_VER${NC}"
    echo ""
    echo "更新内容:"
    echo "$RESP" | python3 -c "
import sys,json
for i,item in enumerate(json.load(sys.stdin).get('changelog',[]),1):
    print(f'  {i}. {item}')
"
else
    echo -e "${GREEN}已是最新版本 (${LOCAL_VER:-未安装})${NC}"
    exit 0
fi

# ---- 检查模式 ----
for arg in "$@"; do
    case "$arg" in --check|-c|check) echo "仅检查模式，不下载"; exit 0;; esac
done

# ---- 确认 ----
echo ""
read -p "是否下载并应用此更新? [y/N]: " confirm
case "$confirm" in [yY]|[yY][eE][sS]) ;; *) echo "已取消"; exit 0;; esac

# ---- 下载 ----
mkdir -p "$CACHE_DIR"
TAR_PATH="$CACHE_DIR/patch_${LATEST_VER}.tar.gz"
echo -e "${YELLOW}正在下载补丁包...${NC}"

DL_URL="$CENTER_URL?version=$LATEST_VER&download=true"
HTTP_CODE=$(curl -s -o "$TAR_PATH" -w "%{http_code}" "$DL_URL" 2>/dev/null)
if [ "$HTTP_CODE" != "200" ]; then
    echo -e "${RED}[错误] 下载失败 (HTTP $HTTP_CODE)${NC}"
    exit 1
fi
echo -e "${GREEN}  下载完成 ($(du -h "$TAR_PATH" | cut -f1))${NC}"

# ---- 备份 ----
# 只备份「即将被覆盖」的文件，且保留原相对目录结构（否则各 app 同名的
# models.py / views.py / urls.py 会互相覆盖）。backend 与 frontend 一起备份。
BACKUP_DIR="$CACHE_DIR/backup_${LOCAL_VER:-before}"
mkdir -p "$BACKUP_DIR"
FRONTEND_DIR="$(cd "$(dirname "$0")/frontend" && pwd 2>/dev/null || echo "")"
echo -e "${YELLOW}备份当前文件到 $BACKUP_DIR ...${NC}"

BK_DONE=0
BK_NEW=0
while IFS= read -r f; do
    rel="${f#files/}"
    case "$rel" in
        backend/*)  src="$BACKEND_DIR/${rel#backend/}" ;;
        frontend/*) if [ -n "$FRONTEND_DIR" ]; then src="$FRONTEND_DIR/${rel#frontend/}"; else continue; fi ;;
        *)          continue ;;
    esac
    if [ -f "$src" ]; then
        dst="$BACKUP_DIR/$rel"
        mkdir -p "$(dirname "$dst")"
        if cp -p "$src" "$dst" 2>/dev/null; then
            BK_DONE=$((BK_DONE+1))
        fi
    else
        BK_NEW=$((BK_NEW+1))
    fi
done < <(tar -tzf "$TAR_PATH" | grep -E '^files/(backend|frontend)/' | grep -v '/$')

if [ "$BK_DONE" -eq 0 ]; then
    echo -e "${RED}  ⚠ 没有任何已有文件被备份（本包可能全是新增文件）${NC}"
else
    echo -e "${GREEN}  ✅ 已备份 $BK_DONE 个文件（保留目录结构）${NC}"
    echo "     位置: $BACKUP_DIR"
    [ "$BK_NEW" -gt 0 ] && echo "     另有 $BK_NEW 个本地不存在（新增文件，无需备份）"
fi

# ---- 应用 ----
echo -e "${YELLOW}正在应用补丁...${NC}"

# 解压到临时目录
TMP_DIR=$(mktemp -d)
tar -xzf "$TAR_PATH" -C "$TMP_DIR"
PATCH_DIR="$TMP_DIR/files"

UPDATED=0
# 更新后端文件
if [ -d "$PATCH_DIR/backend" ]; then
    find "$PATCH_DIR/backend" -type f | while read -r f; do
        rel="${f#$PATCH_DIR/}"
        target="$BACKEND_DIR/${rel#backend/}"
        mkdir -p "$(dirname "$target")"
        cp "$f" "$target"
        echo "  更新: $rel"
        UPDATED=$((UPDATED+1))
    done
fi
# 更新前端文件（如果存在前端目录）
FRONTEND_DIR="$(cd "$(dirname "$0")/frontend" && pwd 2>/dev/null || echo "")"
if [ -n "$FRONTEND_DIR" ] && [ -d "$PATCH_DIR/frontend" ]; then
    find "$PATCH_DIR/frontend" -type f | while read -r f; do
        rel="${f#$PATCH_DIR/}"
        target="$FRONTEND_DIR/${rel#frontend/}"
        mkdir -p "$(dirname "$target")"
        cp "$f" "$target"
        echo "  更新: $rel"
        UPDATED=$((UPDATED+1))
    done
fi
rm -rf "$TMP_DIR"

echo "$LATEST_VER" > "$VER_FILE"

# ---- 清理 Python 缓存 ----
echo -e "${YELLOW}清理 Python 字节码缓存...${NC}"
find "$BACKEND_DIR" -name "*.pyc" -delete 2>/dev/null
find "$BACKEND_DIR" -type d -name "__pycache__" -exec rm -rf {} \; 2>/dev/null
echo -e "${GREEN}  缓存清理完成${NC}"

echo -e "${GREEN}"
echo "========================================"
echo "  ✅ 更新完成！"
echo "  版本: ${LOCAL_VER:-无} → $LATEST_VER"
echo "========================================"
echo -e "${NC}"
echo -e "${YELLOW}⚠ 请重启应用服务使更改生效:${NC}"
echo "   systemctl restart beyondit-backend.service"
echo "   或: supervisorctl restart ops-system"
echo "   或: systemctl restart ops-system"
