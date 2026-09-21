---
type: wiki
tags:
  - openclaw
  - architecture
  - deployment
  - skills
  - memory-system
  - channels
  - security
summary: OpenClaw 开源 AI Agent 系统的一站式参考手册，涵盖架构原理、部署方案、渠道接入、Skills 系统、模型配置、安全与成本，以及生态全景。
---

# OpenClaw 橙皮书 · 从入门到精通

> 一个开源、自托管的 AI Agent 系统，让 AI 从「聊天工具」变成「能自主执行任务的数字员工」。
> 吉祥物是龙虾，中文社区称使用 OpenClaw 为「**养虾**」🦞

---

## 一、认识 OpenClaw

### 什么是 OpenClaw

OpenClaw 是一个基于 [[Gateway-Node-Channel 三层架构]] 的开源 AI Agent 系统。与 ChatGPT 等问答式 AI 不同，OpenClaw 能：
- 连接 20+ 消息渠道（WhatsApp、Telegram、飞书、钉钉、Discord 等）
- 主动执行任务、管理日程、处理邮件
- 操作浏览器、调用各种工具
- 在自己的服务器上完全自托管

| 维度 | ChatGPT | OpenClaw |
|------|---------|----------|
| 交互模式 | 你问它答 | 自主执行任务 |
| 运行环境 | 网页/App | 自托管服务器，接入多平台 |
| 可扩展性 | GPTs 商店 | ClawHub 技能市场（13,700+ Skills） |
| 数据控制 | 数据在 OpenAI | 完全本地，用户拥有所有数据 |
| 模型选择 | 仅 GPT 系列 | Claude / GPT / DeepSeek / Gemini / Ollama 本地模型 |
| 开源 | 否 | MIT License |

### 核心数据 (截至 2026-03-11)

- **GitHub Stars**: 280,000+（全球软件项目第一）
- **Forks**: 53,232+
- **贡献者**: 1,075+
- **ClawHub Skills**: 13,700+
- **内置 Skills**: 55 个
- **支持渠道**: 20+
- **最新版本**: v2026.3.8

### 发展简史

| 时间 | 事件 |
|------|------|
| 2025-11 | **ClawdBot** 诞生，奥地利开发者 [[Peter Steinberger]] 的周末项目 |
| 2026-01 中旬 | 爆发增长，72 小时获 6 万 Stars |
| 2026-01-27 | Anthropic 商标警告 → 改名 **Moltbot** |
| 2026-01-30 | 再次改名 **OpenClaw** |
| 2026-02 初 | 安全危机：[[CVE-2026-25253]] RCE 漏洞 + [[ClawHavoc 供应链攻击]] |
| 2026-02 初 | 谷歌大规模封禁 OpenClaw 用户账号 |
| 2026-02-14 | Peter Steinberger 加入 OpenAI，项目移交开源基金会 |
| 2026-03-03 | Stars 超 250K，超越 React 成为 GitHub 第一 |
| 2026-03-07 | v2026.3.7「史诗级更新」，Stars 达 278,932 |
| 2026-03-08 | 深圳龙岗 AI 局发布 OpenClaw 支持政策 |
| 2026-03-09 | v2026.3.8 安全加固版，工信部 & CNCERT 发布安全风险预警 |

### 创始人故事

[[Peter Steinberger]] 是奥地利 iOS/macOS 开发者。2025 年 11 月的一个周末写了 ClawdBot。到 2026 年 3 月，个人提交 11,684 次 commit，贡献者超 1,075 人。

**加入 OpenAI**（2026-02-14）：Sam Altman 发推欢迎，称其为「genius」。关键承诺：
- 项目转为开源基金会运营，保持独立
- OpenAI 为赞助商之一，不控制项目方向
- Peter 继续投入 OpenClaw 开发

### 为什么这么火

1. **养虾文化**：吉祥物龙虾 →「养虾」→「养虾人」→ 社交货币
2. **Moltbook**：AI Agent 社交平台，32,912 个注册 Agent
3. **热门玩法**：
   - 赚钱型：Polymarket 预测交易、ClawWork 项目
   - 生活助手：邮件、日历、浏览器自动化
   - 社交养成：Moltbook 上 Agent 社交行为观察
   - 企业部署：飞书、钉钉、企业微信、QQ 接入
4. **开源社区狂热**：单日增长 9,000 Stars

> ⚠️ **阴影面**：ClawHub 13,729 个 Skills 中 50%+ 低质量/重复，396 个恶意；API 账单$1,100 的恐怖故事常见；CVE-2026-25253 曾让 13.5 万实例面临风险。

---

## 二、技术架构

### [[Gateway-Node-Channel 三层架构]]

```
Gateway ──WebSocket──→ Node ──→ 设备端执行
    │
    └──→ 20+ 消息渠道 (Channel)
```

| 层级 | 职责 | 关键细节 |
|------|------|----------|
| **Gateway** | 中央控制平面，WebSocket 服务、Session 管理、Agent 调度 | 默认绑定 `ws://127.0.0.1:18789`，每台主机一个实例 |
| **Node** | 设备端执行节点，负责本地操作 | camera、screen recording、system.run 等 |
| **Channel** | 消息渠道接入层 | WhatsApp、Telegram、Discord、Slack、飞书、钉钉等 |

**Loopback-First 设计**：Gateway 默认只绑定 localhost，天然安全。需远程访问时通过 [[Tailscale]] Serve/Funnel 暴露。

### 通信流程

```
用户发消息 → Channel 接收 → Gateway 路由 → Agent 处理 → Node 执行 → 回复用户
```

### [[记忆系统 Memory System]]

四层记忆架构，从不可变内核到实时对话：

| 层级 | 存储位置 | 生命周期 | 说明 |
|------|----------|----------|------|
| **SOUL** | SOUL.md | 永久不可变 | 人格、价值观、核心身份定义 |
| **TOOLS** | Skills + Extensions | 按需加载 | 当前可用工具和技能列表 |
| **USER** | MEMORY.md + 向量数据库 | 持久化 | 用户偏好、决策、历史事实 |
| **Session** | 内存 + sessions.json | 会话级 | 当前对话实时上下文 |

**Daily Logs**：`memory/YYYY-MM-DD.md`，append-only 写入，Session 启动时自动加载。

**Pre-Compaction**：当会话接近 token 限制（默认约 4,000 tokens）时，Agent 静默执行：
1. 检测阈值 → 2. 静默写入 MEMORY.md & Daily Log → 3. 压缩上下文

**向量记忆搜索**：结合 Embedding 向量（语义相似度）与 BM25 关键词（精确匹配），底层使用 SQLite-vec。

---

## 三、部署方案

### 部署方式总览

| 方式 | 适用场景 |
|------|----------|
| **本地安装** | 开发调试、个人使用 |
| **Docker 部署** | 生产环境推荐 |
| **国内云厂商一键部署** | 腾讯云、阿里云等 |

**重要原则**：每台主机只运行一个 Gateway 实例（WhatsApp Web 等渠道需要独占会话）。

### 本地安装

```bash
# 前提条件：Node.js 22+
npm install -g openclaw
openclaw gateway start
```

### Docker 部署

```bash
docker run -d --name openclaw \
  -p 18789:18789 \
  -v ./data:/home/user/.openclaw \
  openclaw/gateway:latest
```

### 国内云厂商

已有 [[openclaw-china 插件套件]]，支持三步 Docker 部署。

---

## 四、渠道接入

### [[Channel 渠道系统]]

OpenClaw 支持 20+ 消息渠道，分为：

**国际平台**：WhatsApp、Telegram、Discord、Slack、Signal、Line 等
**国内平台**：飞书、钉钉、企业微信、QQ、微信公众号/小程序
**远程访问**：通过 [[Tailscale]] Serve/Funnel 安全暴露

---

## 五、Skills 系统

### [[Skills 工作原理]]

Skills 是 OpenClaw 的可扩展能力模块（类比 ChatGPT 的插件）。通过 ClawHub 安装或自建。

### [[ClawHub 技能市场]]

- 13,700+ 可用 Skills（2026-03）
- 安装命令：`openclaw skills install <skill-name>`
- 支持社区提交和审核

> ⚠️ **安全问题**：约 12% 的 Skill 在 [[ClawHavoc 供应链攻击]] 中被确认为恶意。

### 自建 Skill

Skills 以目录形式组织到 `.openclaw/workspace/skills/` 下，包含 `SKILL.md` 描述文件和实现代码。

### Skills 安全

- 安装前检查权限声明
- 使用 [[skill-vetter]] 进行安全审查
- 注意 Skills 能访问的消息渠道和主机资源

---

## 六、模型配置

OpenClaw 支持多种模型提供商：

| 类型 | 提供商 |
|------|--------|
| **国际模型** | Claude、GPT-4o/GPT-5.4、Gemini、Perplexity |
| **国产模型** | DeepSeek、通义千问、文心一言、Kimi 等 |
| **本地模型** | Ollama（qwen 2.5:32b、deepseek-r1:14b 等） |

**推荐方案（国内用户）**：
- 主力：DeepSeek 系列（性价比高）
- 本地：Ollama + qwen2.5:32b（隐私敏感任务）
- 视觉任务：通义千问 VL

---

## 七、安全与成本

### 安全事件

- **[[CVE-2026-25253]]**：RCE 漏洞，CVSS 8.8/10，影响 13.5 万暴露实例
- **[[ClawHavoc 供应链攻击]]**：ClawHub 约 12% Skills 为恶意
- **谷歌封号风波**：大规模封禁 OpenClaw 用户账号

### 成本控制

- 设置 API token 月度预算
- 使用本地模型减少 API 调用
- 监控 Skills 的 token 消耗
- 注意 Skills 可能产生大量 API 调用

---

## 八、生态与社区

### 养虾文化 🦞

中文社区将 OpenClaw 称为「养虾」，用户自称「养虾人」。深圳腾讯云总部曾近千人排队体验安装。

### [[Moltbook]]

AI Agent 社交网络：
- 32,912 个注册 AI Agent
- 2,364 个子社区
- Agent 可以在上面发帖、评论、讨论

### [[Moltbook 竞品对比]]

| 项目 | OpenClaw | Claude Code |
|------|----------|-------------|
| 运行模式 | 7×24 后台 daemon | CLI 命令行工具 |
| 记忆 | 四层持久记忆 | 会话级上下文 |
| 渠道 | 20+ 消息平台 | 终端 |
| 自托管 | 完全自托管 | 需 API 调用 |

### 国内生态

- [[openclaw-china]] 插件套件
- 深圳龙岗 AI 局发布支持政策
- 工信部 & CNCERT 发布安全风险预警

---

## 附录

### 常见问题 (FAQ)

**Q: 需要什么硬件？**
A: 一台 Linux/Mac 服务器即可，Node.js 22+。轻量使用 2 核 4G 足够。

**Q: 可以用 Windows 吗？**
A: 建议 Linux/Mac。Windows 可通过 WSL 或 Docker 运行。

**Q: 免费吗？**
A: OpenClaw 本身免费开源（MIT License）。需要自备模型 API 费用。

### 命令速查

| 命令 | 说明 |
|------|------|
| `openclaw gateway start` | 启动 Gateway |
| `openclaw gateway status` | 查看状态 |
| `openclaw skills install <name>` | 安装 Skill |
| `openclaw skills search <query>` | 搜索 Skill |
| `openclaw node connect <address>` | 连接远程节点 |

### 资源链接

- **GitHub**: https://github.com/openclaw/openclaw
- **官方文档**: https://docs.openclaw.ai
- **ClawHub**: https://clawhub.ai
- **Moltbook**: https://moltbook.ai
- **中文社区**: 关注公众号「花叔」
- **视频教程**: B 站「OpenClaw 从 0 到 1」

---

> **文档版本**: v1.1.0 → v2026.3.8
> **信息来源**: OpenClaw 官方文档 · GitHub 仓库 · 社区调研
> **编写**: 花叔（B站/YouTube：AI进化论-花生 · 公众号：花叔）
