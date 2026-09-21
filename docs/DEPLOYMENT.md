# ops-system 部署指南

> ops-system 通用运维管理系统 — 完整部署手册
>
> **用户部署路径：** `$HOME/ops-system`（可按需修改）
>
> **当前开发路径：** `/home/zhang/.openclaw/workspace/ops-system`

---

## 目录

1. [环境要求](#1-环境要求)
2. [快速开始](#2-快速开始)
3. [分步安装](#3-分步安装)
4. [数据库配置](#4-数据库配置)
5. [Gunicorn 生产部署](#5-gunicorn-生产部署)
6. [前端构建与部署](#6-前端构建与部署)
7. [Nginx 反向代理](#7-nginx-反向代理)
8. [Systemd 服务](#8-systemd-服务)
9. [数据迁移](#9-数据迁移)
10. [推送配置（对接 ops-center）](#10-推送配置对接-ops-center)
11. [插件安装](#11-插件安装)
12. [配置说明](#12-配置说明)
13. [启动与停止](#13-启动与停止)
14. [常见问题](#14-常见问题)
15. [附录：目录结构](#15-附录目录结构)

---

## 1. 环境要求

| 组件 | 版本要求 | 说明 |
|------|---------|------|
| Python | ≥ 3.12 | 后端运行环境 |
| Node.js | ≥ 18.x | 前端构建与开发 |
| npm | ≥ 9.x | Node 包管理器 |
| MySQL | 8.0 | 数据库（Docker 或 原生安装） |
| Nginx | ≥ 1.18 | 生产环境反向代理（可选） |
| 操作系统 | Ubuntu 22.04 / Debian 12 | 推荐，其他 Linux 发行版亦可 |

硬件建议：

- **最低配置：** 2 vCPU / 4GB RAM / 20GB 磁盘
- **推荐配置：** 4 vCPU / 8GB RAM / 50GB 磁盘（SSD 更佳）

---

## 2. 快速开始

### 2.1 一键部署脚本

在目标机器上创建并运行以下脚本（适用于异地部署）：

```bash
#!/bin/bash
# 保存为: $HOME/ops-system-deploy.sh
# 运行: chmod +x $HOME/ops-system-deploy.sh && ./$HOME/ops-system-deploy.sh

set -e

PROJECT_ROOT="$HOME/ops-system"
MYSQL_ROOT_PWD="root123"

echo "=== ops-system 一键部署 ==="
echo "安装路径: $PROJECT_ROOT"

# ===== 1. 安装系统依赖 =====
echo "[1/7] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3.12 python3.12-venv python3-pip \
    nodejs npm \
    nginx \
    git curl

# ===== 2. Docker + MySQL =====
echo "[2/7] 部署 Docker MySQL..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sudo bash
fi
sudo docker rm -f mysql-ops 2>/dev/null || true
sudo docker run -d \
    --name mysql-ops \
    --restart always \
    -e MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PWD}" \
    -e MYSQL_DATABASE=ops_system \
    -p 127.0.0.1:3306:3306 \
    mysql:8.0 \
    --character-set-server=utf8mb4 \
    --collation-server=utf8mb4_unicode_ci

echo "等待 MySQL 启动（约 30 秒）..."
sleep 30

# ===== 3. 创建数据库 =====
echo "[3/7] 初始化数据库..."
sudo docker exec -i mysql-ps mysql -uroot -p${MYSQL_ROOT_PWD} <<'EOF'
CREATE DATABASE IF NOT EXISTS ops_center CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SHOW DATABASES;
EOF

# ===== 4. Python 虚拟环境 =====
echo "[4/7] 配置 Python 虚拟环境..."
cd "$PROJECT_ROOT/backend"
if [ ! -d "venv" ]; then
    python3.12 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install gunicorn mysqlclient -q  # 生产部署必需

# 数据库迁移 + 初始化
python manage.py migrate
python manage.py collectstatic --noinput

# ===== 5. 前端构建 =====
echo "[5/7] 构建前端..."
cd "$PROJECT_ROOT/frontend"
npm install
npm run build

# ===== 6. Systemd 服务 =====
echo "[6/7] 配置 Systemd 服务..."
CURRENT_USER=$(whoami)

sudo tee /etc/systemd/system/ops-system-backend.service > /dev/null <<SERVICEEOF
[Unit]
Description=ops-system Backend (Django + Gunicorn)
After=network docker.service
Wants=docker.service

[Service]
Type=simple
User=${CURRENT_USER}
Group=${CURRENT_USER}
WorkingDirectory=${PROJECT_ROOT}/backend
Environment="PATH=${PROJECT_ROOT}/backend/venv/bin"
Environment="PYTHONPATH=${PROJECT_ROOT}/backend"
Environment="DJANGO_SETTINGS_MODULE=config.settings"
ExecStart=${PROJECT_ROOT}/backend/venv/bin/gunicorn config.wsgi:application -b 0.0.0.0:8002 --workers 2 --access-logfile /tmp/ops-gunicorn-access.log --error-logfile /tmp/ops-gunicorn-error.log
Restart=always
RestartSec=5
StandardOutput=append:/tmp/ops-backend.log
StandardError=append:/tmp/ops-backend.log

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo tee /etc/systemd/system/ops-system-frontend.service > /dev/null <<SERVICEEOF
[Unit]
Description=ops-system Frontend Build Watcher (Vite)
After=network

[Service]
Type=simple
User=${CURRENT_USER}
Group=${CURRENT_USER}
WorkingDirectory=${PROJECT_ROOT}/frontend
Environment="PATH=/usr/bin"
ExecStart=/usr/bin/npm run dev -- --port 3099
Restart=always
RestartSec=5
StandardOutput=append:/tmp/ops-frontend.log
StandardError=append:/tmp/ops-frontend.log
Environment="NODE_OPTIONS=--max-old-space-size=4096"

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable ops-system-backend ops-system-frontend

# ===== 7. Nginx 配置 =====
echo "[7/7] 配置 Nginx..."
sudo tee /etc/nginx/sites-available/ops-system > /dev/null <<NGINXEOF
upstream ops_backend {
    server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name _;

    # 前端静态文件
    root ${PROJECT_ROOT}/frontend/dist;
    index index.html;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # 前端 SPA 路由
    location / {
        try_files \$uri \$uri/ /index.html;
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }

    # 前端静态资源（带缓存）
    location /assets/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API 代理到 gunicorn
    location /api/ {
        proxy_pass http://ops_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Admin 后台代理
    location /admin/ {
        proxy_pass http://ops_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # 静态文件代理（Django collectstatic）
    location /static/ {
        proxy_pass http://ops_backend;
        proxy_set_header Host \$host;
    }

    # Media 文件代理
    location /media/ {
        proxy_pass http://ops_backend;
        proxy_set_header Host \$host;
    }

    # 禁止隐藏文件
    location ~ /\\. {
        deny all;
    }

    access_log /var/log/nginx/ops-system_access.log;
    error_log  /var/log/nginx/ops-system_error.log;
}
NGINXEOF

sudo ln -sf /etc/nginx/sites-available/ops-system /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl enable nginx

# ===== 启动服务 =====
echo "启动服务..."
sudo systemctl start ops-system-backend
sleep 3
sudo systemctl start ops-system-frontend

sleep 3

echo ""
echo "=== 部署完成 ==="
echo ""
echo "安装路径 : $PROJECT_ROOT"
echo "MySQL    : $(sudo docker ps --filter name=mysql-ops --format '{{.Status}}')"
echo "后端     : $(sudo systemctl is-active ops-system-backend) (gunicorn :8002)"
echo "前端     : $(sudo systemctl is-active ops-system-frontend)"
echo "Nginx    : $(sudo systemctl is-active nginx)"
echo ""
echo "访问地址:"
echo "  Nginx : http://<server-ip>"
echo "  后端  : http://localhost:8002/api/"
echo "  Admin : http://localhost:8002/admin/"
echo ""
echo "管理命令:"
echo "  sudo systemctl status ops-system-backend"
echo "  sudo systemctl status ops-system-frontend"
echo "  sudo journalctl -u ops-system-backend -f"
echo ""
echo "默认账号: admin / admin123"
```

### 2.2 部署步骤（异地）

```bash
# 1. 将项目复制到目标机器
scp -r /home/zhang/.openclaw/workspace/ops-system user@target-host:~/

# 2. 在目标机器执行一键脚本
ssh user@target-host
cd $HOME/ops-system
chmod +x ops-system-deploy.sh
./ops-system-deploy.sh
```

---

## 3. 分步安装

### 3.1 安装系统依赖

```bash
# Python 3.12
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip

# Node.js 18（使用 NodeSource）
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Nginx（生产环境必需）
sudo apt-get install -y nginx

# 编译依赖（mysqlclient 等）
sudo apt-get install -y build-essential pkg-config default-libmysqlclient-dev

# 验证
python3 --version   # 3.12.x
node --version      # v18.x
nginx -v            # 1.18+
```

### 3.2 数据库部署（二选一）

**选项 A：Docker MySQL（推荐）**

参见 [4.1 Docker MySQL 部署](#41-docker-mysql-部署)

**选项 B：原生 MySQL 安装**

参见 [4.2 原生 MySQL 安装](#42-原生-mysql-安装)

### 3.3 创建数据库

```sql
CREATE DATABASE IF NOT EXISTS ops_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS ops_center CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3.4 配置 Python 虚拟环境

```bash
cd $HOME/ops-system/backend

# 创建虚拟环境
python3.12 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 生产额外依赖
pip install gunicorn mysqlclient

# 验证
python -c "import django; print(django.__version__)"  # 4.2.x
```

### 3.5 数据库迁移与初始化

```bash
cd $HOME/ops-system/backend
source venv/bin/activate

# 数据库迁移
python manage.py migrate

# 静态文件收集（供 Nginx 代理）
python manage.py collectstatic --noinput

# 创建超级管理员
python manage.py createsuperuser
# 默认: admin / admin123
```

### 3.6 安装前端依赖

```bash
cd $HOME/ops-system/frontend

npm install

# 开发模式
npm run dev -- --port 3099

# 生产构建
npm run build
# 产物输出到 frontend/dist/
```

### 3.7 验证

```bash
cd $HOME/ops-system/backend
source venv/bin/activate

# Django 检查
python manage.py check

# 测试启动（确认配置无误后 Ctrl+C 停止）
python manage.py runserver 0.0.0.0:8002
```

---

## 4. 数据库配置

### 4.1 Docker MySQL 部署（推荐）

生产环境建议使用 Docker 运行 MySQL，便于版本管理和数据持久化。

```bash
# 启动 MySQL 8.0 容器
sudo docker run -d \
    --name mysql-ops \
    --restart always \
    -e MYSQL_ROOT_PASSWORD=root123 \
    -e MYSQL_DATABASE=ops_system \
    -p 127.0.0.1:3306:3306 \
    -v mysql-ops-data:/var/lib/mysql \
    mysql:8.0 \
    --character-set-server=utf8mb4 \
    --collation-server=utf8mb4_unicode_ci

# 等待启动（约 20-30 秒）
sleep 30

# 验证连接
sudo docker exec mysql-ops mysql -uroot -proot123 -e "SELECT VERSION();"

# 创建额外数据库
sudo docker exec -i mysql-ops mysql -uroot -proot123 <<'EOF'
CREATE DATABASE IF NOT EXISTS ops_center CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF
```

**常用 Docker MySQL 管理命令：**

```bash
# 启动/停止
sudo docker start mysql-ops
sudo docker stop mysql-ops

# 进入容器
sudo docker exec -it mysql-ops mysql -uroot -proot123

# 备份数据库
sudo docker exec mysql-ops mysqldump -uroot -proot123 --single-transaction ops_system > $HOME/ops_system_dump.sql

# 导入数据库
sudo docker exec -i mysql-ops mysql -uroot -proot123 ops_system < $HOME/ops_system_dump.sql

# 查看日志
sudo docker logs mysql-ops

# 数据持久化位置
sudo docker volume inspect mysql-ops-data
```

### 4.2 原生 MySQL 安装

如不使用 Docker，可直接安装原生 MySQL：

```bash
# 安装
sudo apt-get install -y mysql-server mysql-client

# 启动服务
sudo service mysql start
sudo systemctl enable mysql

# 设置 root 密码（MySQL 8.0 默认 auth_socket，需切换为密码认证）
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root123';"
sudo mysql -e "FLUSH PRIVILEGES;"

# 创建数据库
mysql -uroot -proot123 <<'EOF'
CREATE DATABASE IF NOT EXISTS ops_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS ops_center CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF

# 验证
mysql -uroot -proot123 -e "SELECT VERSION();"
```

### 4.3 数据库配置（settings.py）

`backend/config/settings.py` 中的数据库配置：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'ops_system',
        'USER': 'root',
        'PASSWORD': 'root123',
        'HOST': '127.0.0.1',  # Docker MySQL 使用 127.0.0.1，原生用 localhost
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        }
    }
}
```

> **注意：** Docker MySQL 使用 `127.0.0.1` 而非 `localhost`，因 Docker 容器通过 TCP 暴露端口。

---

## 5. Gunicorn 生产部署

生产环境使用 **Gunicorn** 替代 Django 开发服务器（`runserver`）。

### 5.1 安装 Gunicorn

```bash
pip install gunicorn
```

### 5.2 基本启动命令

```bash
cd $HOME/ops-system/backend
source venv/bin/activate

# 2 个 worker，绑定 8002 端口
gunicorn config.wsgi:application \
    -b 0.0.0.0:8002 \
    --workers 2 \
    --access-logfile /tmp/ops-gunicorn-access.log \
    --error-logfile /tmp/ops-gunicorn-error.log
```

### 5.3 生产优化配置

创建 `gunicorn.conf.py` 配置文件：

```python
# backend/gunicorn.conf.py
"""Gunicorn 生产配置文件"""

bind = '0.0.0.0:8002'
workers = 2  # 建议：2 * CPU核心数 + 1
worker_class = 'sync'  # 同步模式
timeout = 120  # 超时秒数
graceful_timeout = 30
keepalive = 5

# 日志
accesslog = '/tmp/ops-gunicorn-access.log'
errorlog = '/tmp/ops-gunicorn-error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 进程
pidfile = '/tmp/ops-gunicorn.pid'
daemon = False  # Systemd 管理时使用前台模式

# 用户
user = 'zhang'
group = 'zhang'

# SSL（如需直接暴露 HTTPS，否则由 Nginx 处理）
# keyfile = '/etc/ssl/private/ops-system.key'
# certfile = '/etc/ssl/certs/ops-system.crt'
```

使用配置文件启动：

```bash
gunicorn -c backend/gunicorn.conf.py config.wsgi:application
```

### 5.4 验证 Gunicorn

```bash
# 检查进程
ps aux | grep gunicorn

# 测试 API
curl -s http://localhost:8002/api/ | head -20

# 查看日志
tail -f /tmp/ops-gunicorn-access.log
tail -f /tmp/ops-gunicorn-error.log
```

---

## 6. 前端构建与部署

### 6.1 开发模式

```bash
cd $HOME/ops-system/frontend
npm install

# 开发服务器（端口 3099，API 自动代理到 8002）
npm run dev -- --port 3099
```

开发模式下的 Vite 配置（`frontend/vite.config.js`）：

```javascript
server: {
    port: 3099,
    proxy: {
        '/api': {
            target: 'http://localhost:8002',
            changeOrigin: true,
        }
    }
}
```

### 6.2 生产构建

```bash
cd $HOME/ops-system/frontend
npm install

# 生产构建
NODE_OPTIONS="--max-old-space-size=4096" npm run build
```

构建产物输出到 `frontend/dist/`，目录结构：

```
frontend/dist/
├── index.html           # SPA 入口
├── assets/              # 静态资源（带 hash）
│   ├── index-xxxx.js
│   ├── index-xxxx.css
│   └── vendor-xxxx.js
└── favicon.ico
```

### 6.3 生产部署方式

**方式 A：Nginx 直接托管（推荐）**

将 `frontend/dist/` 目录作为 Nginx 的 `root`，由 Nginx 直接提供静态文件服务（参见 [7. Nginx 反向代理](#7-nginx-反向代理)）。

**方式 B：后端托管静态文件**

```bash
# 将前端构建产物复制到 Django 静态目录
cp -r frontend/dist/* backend/static/
python manage.py collectstatic --noinput
```

> 推荐方式 A（Nginx 直接托管），性能更优，减少不必要的 Python 开销。

---

## 7. Nginx 反向代理

### 7.1 生产级 Nginx 配置

```nginx
# /etc/nginx/sites-available/ops-system
upstream ops_backend {
    server 127.0.0.1:8002;  # Gunicorn
}

server {
    listen 80;
    server_name your-domain-or-ip;  # ← 替换为实际域名或 IP

    # 前端静态文件（生产构建产物）
    root /home/zhang/ops-system/frontend/dist;
    index index.html;

    # ===== Gzip 压缩 =====
    gzip on;
    gzip_min_length 1000;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_comp_level 6;
    gzip_vary on;

    # ===== 前端 SPA 路由 =====
    location / {
        try_files $uri $uri/ /index.html;
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }

    # ===== 前端静态资源（带 hash，长期缓存） =====
    location /assets/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # ===== API 代理到 Gunicorn =====
    location /api/ {
        proxy_pass http://ops_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # ===== Admin 后台 =====
    location /admin/ {
        proxy_pass http://ops_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ===== Swagger / API 文档 =====
    location /swagger/ {
        proxy_pass http://ops_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # ===== Django 静态文件 =====
    location /static/ {
        proxy_pass http://ops_backend;
        proxy_set_header Host $host;
    }

    # ===== Media 文件 =====
    location /media/ {
        proxy_pass http://ops_backend;
        proxy_set_header Host $host;
    }

    # ===== 安全 =====
    location ~ /\. {
        deny all;
    }

    # ===== 日志 =====
    access_log /var/log/nginx/ops-system_access.log;
    error_log  /var/log/nginx/ops-system_error.log;
}
```

### 7.2 启用配置

```bash
# 确保配置存在
sudo ln -sf /etc/nginx/sites-available/ops-system /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default  # 移除默认站点

# 测试配置
sudo nginx -t

# 重载
sudo systemctl reload nginx
```

### 7.3 HTTPS 配置（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 申请证书（自动修改 Nginx 配置）
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# 测试续期
sudo certbot renew --dry-run
```

---

## 8. Systemd 服务

### 8.1 后端服务（Gunicorn）

```ini
# /etc/systemd/system/ops-system-backend.service
[Unit]
Description=ops-system Backend (Django + Gunicorn)
After=network docker.service
Wants=docker.service  # 如使用 Docker MySQL

[Service]
Type=simple
User=zhang                    # ← 替换为实际部署用户
Group=zhang
WorkingDirectory=/home/zhang/ops-system/backend   # ← 按需修改
Environment="PATH=/home/zhang/ops-system/backend/venv/bin"
Environment="PYTHONPATH=/home/zhang/ops-system/backend"
Environment="DJANGO_SETTINGS_MODULE=config.settings"
ExecStart=/home/zhang/ops-system/backend/venv/bin/gunicorn config.wsgi:application -b 0.0.0.0:8002 --workers 2 --access-logfile /tmp/ops-gunicorn-access.log --error-logfile /tmp/ops-gunicorn-error.log
Restart=always
RestartSec=5
StandardOutput=append:/tmp/ops-backend.log
StandardError=append:/tmp/ops-backend.log

[Install]
WantedBy=multi-user.target
```

### 8.2 开发/调试模式（runserver）

如不准备使用 gunicorn，可用 Django 开发服务器：

```ini
# /etc/systemd/system/ops-system-backend-dev.service
[Unit]
Description=ops-system Backend (Django runserver)
After=network docker.service
Wants=docker.service

[Service]
Type=simple
User=zhang
WorkingDirectory=/home/zhang/ops-system/backend
Environment="PATH=/home/zhang/ops-system/backend/venv/bin"
Environment="PYTHONPATH=/home/zhang/ops-system/backend"
ExecStart=/home/zhang/ops-system/backend/venv/bin/python manage.py runserver 0.0.0.0:8002
Restart=always
RestartSec=5
StandardOutput=append:/tmp/ops-backend.log
StandardError=append:/tmp/ops-backend.log

[Install]
WantedBy=multi-user.target
```

### 8.3 前端服务（Vite 开发模式）

```ini
# /etc/systemd/system/ops-system-frontend.service
[Unit]
Description=ops-system Frontend (Vite Dev Server)
After=network

[Service]
Type=simple
User=zhang
WorkingDirectory=/home/zhang/ops-system/frontend
Environment="PATH=/usr/bin"
Environment="NODE_OPTIONS=--max-old-space-size=4096"
ExecStart=/usr/bin/npm run dev -- --port 3099
Restart=always
RestartSec=5
StandardOutput=append:/tmp/ops-frontend.log
StandardError=append:/tmp/ops-frontend.log

[Install]
WantedBy=multi-user.target
```

> **生产环境注意：** 如果使用 Nginx 托管前端静态文件（`frontend/dist/`），前端服务（Vite dev server）**不需要**启动。仅开发或调试时需要。

### 8.4 服务管理

```bash
# 重新加载配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable ops-system-backend
sudo systemctl enable ops-system-frontend  # 仅开发模式

# 启动
sudo systemctl start ops-system-backend

# 停止
sudo systemctl stop ops-system-backend

# 重启
sudo systemctl restart ops-system-backend

# 状态
sudo systemctl status ops-system-backend

# 日志
sudo journalctl -u ops-system-backend -f
# 或直接查看日志文件
tail -f /tmp/ops-backend.log
tail -f /tmp/ops-gunicorn-error.log
```

---

## 9. 数据迁移

> 将当前机器的 `ops_system` 和 `ops_center` 数据库迁移到目标机器。

### 9.1 导出（当前机器）

**Docker MySQL 环境：**

```bash
# 导出 ops_system
sudo docker exec mysql-ops mysqldump -uroot -proot123 \
    --single-transaction --routines --triggers --events \
    ops_system > $HOME/ops_system_dump.sql

# 导出 ops_center
sudo docker exec mysql-ops mysqldump -uroot -proot123 \
    --single-transaction --routines --triggers --events \
    ops_center > $HOME/ops_center_dump.sql

echo "导出完成: $(wc -l < $HOME/ops_system_dump.sql) 行"
```

**原生 MySQL 环境：**

```bash
mysqldump -uroot -proot123 --single-transaction \
    --routines --triggers --events \
    ops_system > $HOME/ops_system_dump.sql

mysqldump -uroot -proot123 --single-transaction \
    --routines --triggers --events \
    ops_center > $HOME/ops_center_dump.sql
```

### 9.2 传输到目标机器

```bash
scp $HOME/ops_system_dump.sql user@target-host:~/
scp $HOME/ops_center_dump.sql user@target-host:~/
```

### 9.3 导入（目标机器）

**Docker MySQL 环境：**

```bash
# 确保数据库已创建
sudo docker exec -i mysql-ops mysql -uroot -proot123 <<'EOF'
CREATE DATABASE IF NOT EXISTS ops_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS ops_center CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF

# 导入
sudo docker exec -i mysql-ops mysql -uroot -proot123 ops_system < $HOME/ops_system_dump.sql
sudo docker exec -i mysql-ops mysql -uroot -proot123 ops_center < $HOME/ops_center_dump.sql

# 验证
sudo docker exec mysql-ops mysql -uroot -proot123 ops_system -e "SHOW TABLES;"
```

**原生 MySQL 环境：**

```bash
mysql -uroot -proot123 ops_system < $HOME/ops_system_dump.sql
mysql -uroot -proot123 ops_center < $HOME/ops_center_dump.sql
```

### 9.4 清理临时文件

```bash
rm -f $HOME/ops_system_dump.sql $HOME/ops_center_dump.sql
```

### 9.5 保留的数据

| 数据类型 | 数据库 | 说明 |
|---------|--------|------|
| 资产数据 | ops_system | 服务器、网络设备等 |
| 资产类型字典 | ops_system | asset_types, asset_fields |
| 客户字典 | ops_system | customers |
| 监控数据 | ops_system | monitoring_datapoints |
| 巡检记录 | ops_system | inspection_records, inspection_results |
| 告警配置 | ops_system | alert_rules, alert_thresholds |
| 定时任务 | ops_system | scheduler_v2_plan 等 |
| 技能库 | ops_system | skills |
| 推送日志 | ops_system | push_logs |
| 租户字典 | ops_center | tenants, notification_channels |

### 9.6 迁移后处理

```bash
# 进入项目目录
cd $HOME/ops-system/backend
source venv/bin/activate

# 运行迁移（确保表结构与代码一致）
python manage.py migrate

# 清理缓存（如有）
python manage.py clear_cache  # 自定义命令，如存在
```

---

## 10. 推送配置（对接 ops-center）

ops-system（租户端）通过 API 将心跳、告警、巡检结果、资产状态推送到 ops-center（中心端）。

### 10.1 推送机制概述

推送服务由 `backend/apps/dashboard/push_service.py` 实现，支持以下推送类型：

| 推送类型 | 端点 | 说明 | 触发方式 |
|---------|------|------|---------|
| 心跳 | `/api/receive/heartbeat/` | 定时上报在线状态 | 后台线程（每 5 分钟） |
| 告警 | `/api/receive/alerts/` | 推送 Ping 离线 / 巡检异常告警 | Ping 检测 / 巡检完成后自动推送 |
| 巡检结果 | `/api/receive/inspections/` | 推送巡检报告 | 巡检任务完成后 |
| 资产状态 | `/api/receive/asset-status/` | 推送 Ping 在线/离线状态 | Ping 检测完成后 |
| 监控数据 | `/api/receive/monitoring-data/` | 推送异常监控指标 | 监控数据记录时 |
| 测试结果 | `/api/receive/monitor-tests/` | 推送采集测试结果 | 手动测试完成后 |

### 10.2 推送配置

推送配置存储在数据库 `system_settings` 表中，可通过 Django Admin 或系统设置页面配置：

| 配置键 | 说明 | 默认值 |
|--------|------|--------|
| `push.enabled` | 是否启用推送 | `false` |
| `push.center_url` | ops-center 的访问地址 | `""` |
| `push.api_key` | API 密钥（中心端生成） | `""` |
| `push.timeout` | 请求超时时间（秒） | `10` |
| `push.push_alerts` | 是否推送告警 | `true` |
| `push.push_inspections` | 是否推送巡检结果 | `true` |
| `push.push_asset_status` | 是否推送资产在线状态 | `true` |

### 10.3 配置步骤

**方式 A：通过 Django Admin 配置**

1. 访问 `http://<server>:8002/admin/`
2. 登录后进入「System settings」
3. 添加/修改以下配置项：

| Key | Value |
|-----|-------|
| `push.enabled` | `true` |
| `push.center_url` | `http://10.0.0.100:3003`（替换为实际 center 地址） |
| `push.api_key` | `your-api-key-here` |
| `push.timeout` | `10` |

**方式 B：通过数据库直接配置**

```sql
INSERT INTO system_settings (key, value, description) VALUES
('push.enabled', 'true', '是否启用数据推送'),
('push.center_url', 'http://10.0.0.100:3003', 'ops-center 平台地址'),
('push.api_key', 'your-api-key-here', 'API 密钥'),
('push.timeout', '10', '请求超时时间(秒)'),
('push.push_alerts', 'true', '是否推送告警'),
('push.push_inspections', 'true', '是否推送巡检结果'),
('push.push_asset_status', 'true', '是否推送资产状态')
ON DUPLICATE KEY UPDATE value = VALUES(value);
```

### 10.4 API-Key 认证机制

ops-system 向 ops-center 推送数据时使用 API-Key 认证：

```python
headers = {
    'Content-Type': 'application/json',
    'X-API-Key': api_key,  # 从 system_settings 读取
}
```

API-Key 由 ops-center 生成并分发，在 ops-system 的推送配置中填写。

### 10.5 测试推送连接

```bash
# 通过 Django shell 测试
cd $HOME/ops-system/backend
source venv/bin/activate
python manage.py shell -c "
from apps.dashboard.push_service import test_push
print(test_push())
"
```

预期输出：
```json
{'success': True, 'message': '连接成功: 某租户', 'data': {...}}
```

### 10.6 重试失败推送

推送失败时会自动重试（指数退避：1min → 5min → 15min → 1h → 4h，最多 5 次）。

手动重试：

```bash
cd $HOME/ops-system/backend
source venv/bin/activate

# 重试所有失败的推送
python manage.py shell -c "
from apps.dashboard.push_service import retry_failed
retry_failed()
"

# 重试指定类型的失败推送
python manage.py shell -c "
from apps.dashboard.push_service import retry_failed
retry_failed(push_type='alert', limit=20)
"

# 重试单条记录
python manage.py shell -c "
from apps.dashboard.push_service import retry_failed
retry_failed(log_id=123)
"
```

### 10.7 推送日志

推送记录存储在 `push_logs` 表中，可在 Django Admin 中查看：

| 字段 | 说明 |
|------|------|
| push_type | 推送类型（alert / inspection / asset_status / heartbeat / monitoring_data） |
| status | 状态（success / failed / retrying） |
| endpoint | 推送端点 |
| records_count | 推送记录数 |
| error_message | 错误信息 |
| retry_count | 已重试次数 |
| next_retry_at | 下次重试时间 |

---

## 11. 插件安装

ops-system 支持客户自定义资产类型的插件系统。

### 11.1 插件目录结构

```
plugins/
└── hospital_assets/       # 医院资产插件（示例）
    ├── plugin.json        # 插件元数据 + 资产 Schema
    └── __init__.py        # 插件实现
```

### 11.2 安装插件

将插件目录复制到 `plugins/` 目录下：

```bash
# 示例：安装 hospital_assets 插件
cp -r /path/to/hospital_assets $HOME/ops-system/plugins/
```

### 11.3 插件注册

插件通过 Django Admin 或系统设置注册到客户配置中：

```python
# 在 customers 模块中注册插件
PLUGIN_REGISTRY = {
    'hospital.assets': {
        'name': '医院资产插件',
        'path': 'plugins.hospital_assets',
        'factory': 'create_plugin',
    }
}
```

### 11.4 为客户启用插件

1. 进入 Django Admin → Customers → 选择目标客户
2. 在「Plugins」字段中添加插件 ID（如 `hospital.assets`）
3. 保存后，该客户即可使用插件定义的资产类型和监控模板

### 11.5 插件 Schema 说明

`plugin.json` 包含以下 Schema 定义：

- **config_schema**：客户配置项的 JSON Schema
- **assets_schema**：资产类型的字段定义（类型、必填、验证规则等）
- **monitoring_schema**：监控检查项的配置
- **alert_schema**：告警规则的条件定义

---

## 12. 配置说明

### 12.1 Django Settings

`backend/config/settings.py` 关键配置：

```python
# --- 核心配置 ---
SECRET_KEY = 'django...tion'         # ⚠️ 生产环境必须修改！
DEBUG = False                         # 生产环境关闭
ALLOWED_HOSTS = ['*']                 # 生产环境应限制为具体域名

# --- 数据库 ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'ops_system',
        'USER': 'root',
        'PASSWORD': 'root123',
        'HOST': '127.0.0.1',         # Docker MySQL 用 127.0.0.1
        'PORT': '3306',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

# --- Session 隔离 ---
SESSION_COOKIE_NAME = 'ops_sessionid'
CSRF_COOKIE_NAME = 'ops_csrftoken'

# --- 时区 ---
TIME_ZONE = 'Asia/Shanghai'
LANGUAGE_CODE = 'zh-hans'
USE_TZ = True

# --- 静态文件 ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- CORS（生产应限制） ---
CORS_ALLOW_ALL_ORIGINS = False       # 生产关闭
CORS_ALLOWED_ORIGINS = [
    'http://your-domain.com',
]
```

### 12.2 生产必须修改的配置

| 配置项 | 开发值 | 生产建议 |
|--------|--------|---------|
| `DEBUG` | `True` | `False` |
| `SECRET_KEY` | `'django...tion'` | 生成随机密钥 |
| `ALLOWED_HOSTS` | `['*']` | `['your-domain.com']` |
| `CORS_ALLOW_ALL_ORIGINS` | `True` | `False` |

生成新的 `SECRET_KEY`：

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 12.3 路径变量说明

| 变量 | 当前值 | 说明 |
|------|--------|------|
| `$HOME` | `/home/zhang` | 部署用户 home 目录 |
| `$PROJECT_ROOT` | `$HOME/ops-system` | 项目根目录 |
| 数据库数据卷 | `mysql-ops-data` | Docker volume 名 |
| Gunicorn 访问日志 | `/tmp/ops-gunicorn-access.log` | HTTP 请求日志 |
| Gunicorn 错误日志 | `/tmp/ops-gunicorn-error.log` | 应用错误日志 |
| 后端日志 | `/tmp/ops-backend.log` | Systemd stdout 日志 |
| 前端日志 | `/tmp/ops-frontend.log` | Vite stdout 日志 |
| Nginx 访问日志 | `/var/log/nginx/ops-system_access.log` | HTTP 访问日志 |
| Nginx 错误日志 | `/var/log/nginx/ops-system_error.log` | Nginx 错误日志 |

---

## 13. 启动与停止

### 13.1 生产模式（推荐）

```bash
# 启动所有服务
sudo systemctl start docker            # 如使用 Docker MySQL
sudo systemctl start ops-system-backend
sudo systemctl start nginx

# 查看状态
sudo systemctl status ops-system-backend
sudo systemctl status nginx

# 停止
sudo systemctl stop ops-system-backend

# 重启
sudo systemctl restart ops-system-backend
```

### 13.2 开发 / 调试模式

```bash
# 后端
cd $HOME/ops-system/backend
source venv/bin/activate
python manage.py runserver 0.0.0.0:8002

# 前端（新终端）
cd $HOME/ops-system/frontend
npm run dev -- --port 3099
```

### 13.3 快速启动脚本

```bash
cd $HOME/ops-system
./ops-system-start.sh
```

### 13.4 端口一览

| 服务 | 端口 | 说明 |
|------|------|------|
| Gunicorn (后端) | 8002 | API 服务，仅本地监听 |
| Vite (前端) | 3099 | 开发服务器 |
| Nginx | 80 | 生产入口（代理前端+后端） |
| MySQL | 3306 | 仅本地监听 (127.0.0.1) |

---

## 14. 常见问题

### Q1: `pip install mysqlclient` 失败

```bash
# 缺少编译依赖
sudo apt-get install -y build-essential pkg-config default-libmysqlclient-dev
pip install mysqlclient
```

### Q2: MySQL 连接 `Access denied`

```bash
# 原生 MySQL：切换为密码认证
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root123';"
sudo mysql -e "FLUSH PRIVILEGES;"

# Docker MySQL：检查密码是否正确
sudo docker exec mysql-ops mysql -uroot -proot123 -e "SELECT 1;"
```

### Q3: Docker MySQL 端口冲突

```bash
# 检查端口占用
ss -tlnp | grep 3306

# 如果 3306 被其他 MySQL 占用，停止冲突进程
sudo service mysql stop

# 重启 Docker MySQL
sudo docker restart mysql-ops
```

### Q4: Django 启动报 `Table already exists`

```bash
# 迁移时使用 --fake-initial
python manage.py migrate --fake-initial

# 或手动 fake 指定 app
python manage.py migrate assets --fake
```

### Q5: MySQL 连接超时 `(2003, ...)`

```bash
# 检查 MySQL 是否运行
sudo docker ps | grep mysql-ops

# 检查端口
ss -tlnp | grep 3306

# 日志诊断
sudo docker logs mysql-ops --tail 30
```

### Q6: 前端构建内存不足

```bash
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build
```

### Q7: Gunicorn 启动后无法访问

```bash
# 检查进程
ps aux | grep gunicorn

# 检查端口
ss -tlnp | grep 8002

# 检查日志
tail -f /tmp/ops-gunicorn-error.log

# 常见原因：8080 port 被占用、venv 未激活、PYTHONPATH 设置错误
```

### Q8: Nginx 502 Bad Gateway

```bash
# Gunicorn 未启动
sudo systemctl start ops-system-backend

# 检查 upstream 端口
ss -tlnp | grep 8002

# 查看 nginx 错误日志
tail -f /var/log/nginx/ops-system_error.log
```

### Q9: 推送连接失败

```bash
# 检查配置
python manage.py shell -c "
from apps.dashboard.push_service import get_config
print(get_config())
"

# 测试连接
python manage.py shell -c "
from apps.dashboard.push_service import test_push
print(test_push())
"

# 检查网络
curl -I http://<center-url>/api/receive/health/ -H "X-API-Key: <your-key>"
```

### Q10: 推送日志显示重试次数过多

```bash
# 检查中心端地址是否可达
ping <center-host>

# 重置失败推送（清空重试计数重新推送）
python manage.py shell -c "
from apps.dashboard.models import PushLog
PushLog.objects.filter(status='failed').update(retry_count=0, next_retry_at=None)
"
```

### Q11: Systemd 服务启动失败

```bash
# 查看详细错误
sudo journalctl -u ops-system-backend -n 50 --no-pager

# 常见原因
# - venv 路径错误（检查 WorkingDirectory 和 ExecStart）
# - 环境变量未设置（PYTHONPATH, DJANGO_SETTINGS_MODULE）
# - 权限问题（User/Group 配置不正确）
# - MySQL 未就绪（添加 After= 和 Wants= 依赖）
```

### Q12: Migration 合并冲突

```bash
# 查看迁移文件
ls backend/*/migrations/

# 合并迁移
python manage.py makemigrations --merge

# 或手动解决冲突后
python manage.py migrate
```

---

## 15. 附录：目录结构

```
$HOME/ops-system/
├── backend/
│   ├── apps/
│   │   ├── assets/          # 资产管理
│   │   ├── alerts/          # 告警管理
│   │   ├── customers/       # 客户管理（多租户+插件）
│   │   ├── dashboard/       # 驾驶舱 + 推送服务
│   │   ├── discovery/       # 自动发现
│   │   ├── inspection/      # 巡检管理
│   │   ├── lab_inventory/   # 实验室库存
│   │   ├── monitoring/      # 监控中心
│   │   ├── scheduler_v2/    # 定时任务调度
│   │   ├── skills/          # 技能模块
│   │   ├── system/          # 系统设置
│   │   ├── users/           # 用户管理
│   │   └── workorder/       # 工单管理
│   ├── config/
│   │   ├── settings.py      # Django 配置
│   │   ├── wsgi.py          # WSGI 入口
│   │   └── urls.py          # URL 路由
│   ├── venv/                # Python 虚拟环境
│   ├── manage.py
│   ├── requirements.txt
│   └── gunicorn.conf.py     # Gunicorn 配置（可选）
├── frontend/
│   ├── src/
│   │   ├── api/             # API 调用
│   │   ├── views/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── router/          # 路由配置
│   │   ├── stores/          # Pinia 状态管理
│   │   └── utils/           # 工具函数
│   ├── dist/                # 生产构建产物
│   ├── vite.config.js
│   └── package.json
├── plugins/                 # 客户插件目录
│   └── hospital_assets/     # 医院资产插件（示例）
│       ├── plugin.json
│       └── __init__.py
├── docs/
│   └── DEPLOYMENT.md        # 本文档
└── README.md
```

---

## 附录：完整部署命令清单

```bash
# ===== 目标机器一条命令部署（Docker MySQL + Gunicorn + Nginx） =====

PROJECT_ROOT="$HOME/ops-system"
MYSQL_ROOT_PWD="root123"

# 1. 系统依赖
sudo apt-get update -qq && \
sudo apt-get install -y -qq python3.12 python3.12-venv python3-pip nodejs npm nginx git curl build-essential pkg-config default-libmysqlclient-dev

# 2. Docker MySQL
curl -fsSL https://get.docker.com | sudo bash && \
sudo docker run -d --name mysql-ops --restart always \
    -e MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PWD} -e MYSQL_DATABASE=ops_system \
    -p 127.0.0.1:3306:3306 \
    mysql:8.0 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci && \
sleep 30 && \
sudo docker exec -i mysql-ops mysql -uroot -p${MYSQL_ROOT_PWD} -e "CREATE DATABASE IF NOT EXISTS ops_center CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 3. Python 环境
cd $PROJECT_ROOT/backend && \
python3.12 -m venv venv && \
source venv/bin/activate && \
pip install --upgrade pip -q && \
pip install -r requirements.txt -q && \
pip install gunicorn mysqlclient -q && \
python manage.py migrate && \
python manage.py collectstatic --noinput

# 4. 前端构建
cd $PROJECT_ROOT/frontend && \
npm install && \
NODE_OPTIONS="--max-old-space-size=4096" npm run build

# 5. 安装 systemd 服务
# （参见 8. Systemd 服务 章节配置）

# 6. 配置 Nginx
# （参见 7. Nginx 反向代理 章节配置）

echo "部署完成！"
```
