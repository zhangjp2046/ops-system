#!/bin/bash
# ===================================================
# ops-system 知识包一键升级脚本
# 用法:
#   ./sync-knowledge.sh          # 检查并更新
#   ./sync-knowledge.sh --force  # 强制重新下载
#   ./sync-knowledge.sh --check  # 仅检查版本
#   ./sync-knowledge.sh --status # 查看本地知识包状态
# ===================================================

set -e

# 项目路径（自动检测脚本所在目录）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"
CACHE_DIR="$HOME/.openclaw/knowledge"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  ops-system 知识包同步工具${NC}"
echo -e "${CYAN}========================================${NC}"

# 检查后端目录
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}[错误] 后端目录不存在: $BACKEND_DIR${NC}"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}[错误] 虚拟环境不存在: $VENV_DIR${NC}"
    echo -e "${YELLOW}请先创建虚拟环境: python3 -m venv $VENV_DIR${NC}"
    exit 1
fi

# 检查本地缓存
show_status() {
    echo ""
    echo -e "${CYAN}--- 本地知识包状态 ---${NC}"
    if [ -f "$CACHE_DIR/knowledge_version.txt" ]; then
        local_ver=$(cat "$CACHE_DIR/knowledge_version.txt")
        echo -e "  本地版本: ${GREEN}v$local_ver${NC}"
    else
        echo -e "  本地版本: ${YELLOW}未缓存${NC}"
    fi

    if [ -f "$CACHE_DIR/knowledge_pack.json" ]; then
        pack_size=$(stat -c%s "$CACHE_DIR/knowledge_pack.json" 2>/dev/null || echo 0)
        if [ "$pack_size" -gt 0 ]; then
            echo -e "  知识包大小: $(numfmt --to=iec $pack_size 2>/dev/null || echo "$pack_size bytes")"
        fi
    fi

    # 展示缓存文件
    echo -e "  缓存目录: $CACHE_DIR"
    ls -la "$CACHE_DIR/"*.json "$CACHE_DIR/"*.txt 2>/dev/null | awk '{print "    " $NF " (" $5 " bytes)"}' || echo -e "    ${YELLOW}(空)${NC}"
    echo ""
}

# ==================== 执行命令 ====================

MODE="${1:-update}"

case "$MODE" in
    --check|-c|check)
        show_status
        echo -e "${CYAN}--- 检查远程版本 ---${NC}"
        cd "$BACKEND_DIR"
        source "$VENV_DIR/bin/activate"
        python manage.py sync_knowledge --check-only
        ;;

    --force|-f|force)
        show_status
        echo -e "${CYAN}--- 强制下载并更新 ---${NC}"
        cd "$BACKEND_DIR"
        source "$VENV_DIR/bin/activate"
        python manage.py sync_knowledge --force
        ;;

    --status|-s|status)
        show_status
        ;;

    *)
        # 默认: 检查并更新
        show_status
        echo -e "${CYAN}--- 检查并更新 ---${NC}"
        cd "$BACKEND_DIR"
        source "$VENV_DIR/bin/activate"
        python manage.py sync_knowledge
        ;;
esac

# 显示最终状态
echo ""
echo -e "${CYAN}--- 同步完成 ---${NC}"
if [ -f "$CACHE_DIR/knowledge_version.txt" ]; then
    final_ver=$(cat "$CACHE_DIR/knowledge_version.txt")
    echo -e "  当前版本: ${GREEN}v$final_ver${NC}"
else
    echo -e "  当前版本: ${YELLOW}未缓存${NC}"
fi

echo -e "${CYAN}========================================${NC}"
