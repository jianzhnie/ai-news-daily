# AI 信息聚合系统 — 完整指南

基于 RSSHub + Folo + Claude API 的 AI 领域信息聚合方案。覆盖 22 个信息源，提供两种使用模式：

- **模式一（Folo）**：可视化 RSS 阅读器，AI 辅助摘要 + 翻译
- **模式二（daily_digest）**：命令行一键生成 AI 整理的中文日报

---

## 目录

1. [信息源清单](#信息源清单)
2. [架构设计](#架构设计)
3. [环境与依赖](#环境与依赖)
4. [快速开始](#快速开始)
5. [模式一：Folo 可视化阅读](#模式一folo-可视化阅读)
6. [模式二：AI 日报自动生成](#模式二ai-日报自动生成)
7. [定时运行](#定时运行)
8. [文件清单](#文件清单)
9. [踩坑记录](#踩坑记录)

---

## 信息源清单

共 22 个信息源，分 3 类。经逐一验证：

| # | 源 | RSS 地址 | 状态 | 采集方式 |
|---|-----|----------|:----:|----------|
| 1 | OpenAI Blog | `https://openai.com/news/rss.xml` | ✅ | 原生 RSS（需浏览器 UA）|
| 2 | Anthropic Blog | `http://localhost:1200/anthropic/news` | ✅ | 本地 RSSHub |
| 3 | DeepMind | `http://localhost:1200/deepmind/blog` | ✅ | 本地 RSSHub |
| 4 | HuggingFace Blog | `https://huggingface.co/blog/feed.xml` | ✅ | 原生 RSS |
| 5 | Salesforce AI Research | — | ❌ | 无 RSS 输出 |
| 6 | vLLM Blog | — | ❌ | Next.js SPA，无 RSS |
| 7 | SGLang / LMSYS | — | ❌ | Next.js SPA，无 RSS |
| 8 | MarkTechPost | `https://www.marktechpost.com/feed/` | ✅ | 原生 RSS |
| 9 | MIT AI News | `https://news.mit.edu/rss/topic/artificial-intelligence2` | ✅ | 原生 RSS |
| 10 | Towards Data Science | `https://towardsdatascience.com/feed` | ✅ | 原生 RSS |
| 11 | Analytics Vidhya | `https://www.analyticsvidhya.com/feed/` | ✅ | 原生 RSS |
| 12 | AI Parabellum | `https://aiparabellum.com/feed/` | ✅ | 原生 RSS |
| 13 | Cameron Wolfe | `https://cameronrwolfe.substack.com/feed` | ✅ | Substack RSS |
| 14 | Raschka Magazine | `https://magazine.sebastianraschka.com/feed` | ✅ | Substack RSS |
| 15 | Interconnects | `https://www.interconnects.ai/feed` | ✅ | Substack RSS |
| 16 | Latent Space | `https://www.latent.space/feed` | ✅ | Substack RSS |
| 17 | Sebastian Raschka | `https://sebastianraschka.com/rss_feed.xml` | ✅ | 原生 RSS（需浏览器 UA）|
| 18 | Hamel Husain | `https://hamel.dev/index.xml` | ✅ | 原生 RSS |
| 19 | Philipp Schmid | — | ❌ | Next.js SPA，无 RSS |
| 20 | Gary Marcus | `https://garymarcus.substack.com/feed` | ✅ | Substack RSS |
| 21 | Gwern | `https://gwern.substack.com/feed` | ✅ | Substack RSS |
| 22 | Max Woolf | `https://minimaxir.com/index.xml` | ✅ | 原生 RSS |

**统计**：18/22 可用（82%），4 个暂无 RSS 需手动关注。

---

## 架构设计

```
                         prompt2.md
                             │
                             ▼
                    config/sources.yaml
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     scripts/generate    RSSHub        scripts/daily
     _opml.py            (本地)        _digest.py
              │              │              │
              ▼              │              │
     config/ai-feeds        │              │
     .opml                  │              │
              │              │              │
   ┌──────────┼──────────────┘              │
   ▼          ▼                             ▼
┌──────┐  ┌──────┐                  ┌──────────────┐
│ Folo │  │15 原生│                  │  Claude API  │
│桌面版│  │  RSS  │                  │  或 ChatGPT  │
└──────┘  └──────┘                  └──────────────┘
   │          │                             │
   ▼          ▼                             ▼
AI 摘要    直连获取                    daily-reports/
日报翻译   无需代理                    2026/05/31.md
```

**两条路径**：
- **路径 A（Folo）**：RSSHub 提供 3 个公司博客的路由 + 15 个原生 RSS 直连 → Folo 统一阅读和 AI 摘要
- **路径 B（daily_digest）**：Python 脚本采集所有 RSS → 去重排序 → 调用 Claude/ChatGPT API → 输出 Markdown 日报

**为什么需要本地 RSSHub？**

OpenAI、Anthropic、DeepMind 的网站有 Cloudflare 反爬保护。公共 RSSHub 实例（rsshub.app 等）使用共享出口 IP，被限流后返回 0 条文章。本地运行的 RSSHub 不受此限制。

---

## 环境与依赖

### 必需

| 组件 | 版本要求 | 用途 |
|------|----------|------|
| Node.js + pnpm | Node >= 18, pnpm >= 10 | 运行 RSSHub |
| Python | >= 3.9 | OPML 生成 + AI 日报脚本 |
| Folo 桌面版 | 最新 | RSS 阅读器（模式一）|

### Python 依赖

```bash
pip install anthropic feedparser httpx pyyaml
# ChatGPT 模式额外需要
pip install openai
```

### 可选

| 组件 | 用途 |
|------|------|
| RSSHub Radar 浏览器扩展 | 浏览网页时自动发现 RSS 源 |
| Anthropic API Key | 模式二用 Claude 生成日报 |
| OpenAI API Key | 模式二用 ChatGPT 生成日报 |

---

## 快速开始

### 第一步：克隆并安装 RSSHub

```bash
cd ~/work_dir/ai-news-aggregator

# 克隆 RSSHub（仅首次）
git clone https://github.com/DIYgod/RSSHub.git --depth 1
cd RSSHub && pnpm i && pnpm build && cd ..
```

### 第二步：启动 RSSHub

```bash
bash scripts/start-rsshub.sh
# 输出: RSSHub is ready!

# 验证
curl -s http://localhost:1200/openai/news | grep -c '<item>'
# 应输出 1 或更多
```

停止：`kill $(cat .rsshub.pid) && rm -f .rsshub.pid`

### 第三步：选择使用模式

- **想看文章、手动浏览** → [模式一：Folo 可视化阅读](#模式一folo-可视化阅读)
- **想要 AI 整理的日报** → [模式二：AI 日报自动生成](#模式二ai-日报自动生成)
- **两个都要** → 都配好，互补使用

---

## 模式一：Folo 可视化阅读

### 安装 Folo

```bash
brew install --cask folo     # macOS 桌面版
```

> **必须使用桌面版**。Web 版 (app.folo.is) 的服务器端无法访问 localhost 的 RSSHub。

### 导入订阅源

1. 打开 Folo，左侧栏 **"+"** → **"导入"** → **"导入 OPML 到 Folo"**
2. 选择 `config/ai-feeds.opml`
3. 自动按 3 个文件夹组织：

```
📁 AI 公司官方博客      (7 sources)
📁 AI News 聚合平台     (9 sources)
📁 个人开发者           (6 sources)
```

### 配置 AI 功能

1. **设置 → AI 助手** → 启用 AI 摘要
2. **设置 → AI 助手** → 翻译语言设为 **简体中文**
3. 可选：Pro 版 BYOK 用自己的 API Key

### 更新订阅源

```bash
# 1. 编辑 config/sources.yaml 增删源
# 2. 重新生成 OPML
python3 scripts/generate_opml.py
# 3. 在 Folo 中重新导入（已有源不会重复）
```

### 添加新源示例

```yaml
# 编辑 config/sources.yaml
- name: 新博客名称
  url: https://example.com/blog
  rss: https://example.com/feed.xml    # 或 null（无 RSS）
  type: native                          # native | rsshub | none
  category: ai-companies               # ai-companies | news-aggregators | individual-devs
```

---

## 模式二：AI 日报自动生成

### 工作原理

```
18 个 RSS 源 ──▶ 采集最近 N 天文章 ──▶ 标题去重 ──▶ Claude/ChatGPT API ──▶ 结构化日报
                                                                   │
                                                    按主题分类 + 重要度标注 + 中文摘要
```

### 基本用法

```bash
# Claude 模式（默认）
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/daily_digest.py

# ChatGPT 模式
export OPENAI_API_KEY=sk-...
python3 scripts/daily_digest.py --provider openai
```

### 命令行选项

| 选项 | 说明 |
|------|------|
| `--days N` | 回溯 N 天，默认 3（覆盖周末）|
| `--dry-run` | 仅采集文章列表，不调用 AI |
| `--prompt-only` | 输出 prompt 文本，可管道给任意 LLM |
| `--output -` | 日报输出到 stdout 而非文件 |
| `--max-articles N` | 最多发送 N 篇文章给 AI，默认 50 |
| `--provider openai` | 使用 ChatGPT 代替 Claude |

### 日报输出示例

```markdown
# AI 日报 — 2026-05-31

## 今日要闻

Anthropic 发布 Opus 4.8 模型并推出 Dynamic Workflows 功能。StepFun 发布 198B MoE
多模态模型 Step 3.7 Flash，面向编程 Agent 和搜索场景。NVIDIA 发布 X-Token 跨分词器
知识蒸馏方案，在 Llama-3.2-1B 上超越 GOLD 方法。Hermes Agent 发布 MCP 工具搜索...

## 分类导读

### 🔥 LLM 训练与架构

| 标记 | 来源 | 标题 | 摘要 |
|------|------|------|------|
| ★★★ | Anthropic | Opus 4.8 发布 | 新一代旗舰模型，推理能力大幅提升，新增 Dynamic Workflows |
| ★★☆ | StepFun | Step 3.7 Flash | 198B MoE 多模态模型，面向编程 Agent 和搜索工作流 |

### ⚡ 推理优化与部署

| 标记 | 来源 | 标题 | 摘要 |
|------|------|------|------|
| ★★☆ | NVIDIA | X-Token 跨分词器知识蒸馏 | 投影引导式方案，在 Llama-3.2-1B 上超越 GOLD 方法 |

### 🤖 AI Agent 与工具

| 标记 | 来源 | 标题 | 摘要 |
|------|------|------|------|
| ★★★ | Hermes | MCP Tool Search | 将 Opus 4 的 Tool Search 准确率从 49% 提升至 74% |

...

## 统计

- 总计文章：35 篇
- ★★★ 必读：4 篇
- ★★☆ 推荐：12 篇
- ★☆☆ 可选：19 篇
```

### Claude 整理的内容包括

1. **今日要闻**（100-150 字全局概述）
2. **按主题分类**：LLM 训练与架构 / 推理优化与部署 / AI Agent 与工具 / 多模态 / 开源动态 / 安全与对齐
3. **重要程度标注**：★★★ 必读 / ★★☆ 推荐 / ★☆☆ 可选
4. **中文摘要**：重点文章各一句 20-40 字中文摘要
5. **统计汇总**：各类别文章数量

### 调试技巧

```bash
# 看看能采集到多少文章
python3 scripts/daily_digest.py --dry-run

# 把 prompt 复制出来手动调优
python3 scripts/daily_digest.py --prompt-only | pbcopy

# 周末用更长的时间窗口
python3 scripts/daily_digest.py --days 3
```

---

## 定时运行

### crontab（推荐）

```bash
# 每个工作日早上 8:00 生成日报
0 8 * * 1-5 cd ~/work_dir/ai-news-aggregator && \
  ANTHROPIC_API_KEY=sk-ant-... python3 scripts/daily_digest.py --days 1
```

### Claude Code schedule

```
/schedule "每个工作日早上 8 点，运行 python3 scripts/daily_digest.py 生成 AI 日报"
```

### launchd（macOS 后台守护 RSSHub）

```xml
<!-- ~/Library/LaunchAgents/com.rsshub.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rsshub</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/yourname/work_dir/ai-news-aggregator/scripts/start-rsshub.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.rsshub.plist
```

---

## 文件清单

```
ai-news-aggregator/
├── config/
│   ├── sources.yaml              # 22 个信息源配置（名称、URL、RSS 地址、分类）
│   └── ai-feeds.opml             # 可导入 Folo 的 OPML 文件（3 个分类文件夹）
├── scripts/
│   ├── generate_opml.py          # 读取 sources.yaml 生成 OPML
│   ├── start-rsshub.sh           # 启动本地 RSSHub（需先 git clone + pnpm build）
│   └── daily_digest.py           # AI 日报生成器（采集 + Claude/ChatGPT 整理）
├── docs/
│   ├── ai-news-aggregator-setup.md   # 本文档
│   └── ai-news-aggregator-design.md  # 早期方案设计（调研参考）
├── RSSHub/                       # 本地 RSSHub 实例（git clone）
├── .rsshub.pid                   # RSSHub 进程 PID（自动生成）
└── .rsshub.log                   # RSSHub 日志（自动生成）
```

### 各脚本依赖关系

```
sources.yaml ──▶ generate_opml.py ──▶ ai-feeds.opml ──▶ Folo 导入

sources.yaml ──▶ daily_digest.py ──▶ Claude/ChatGPT API ──▶ daily-reports/*.md
                       │
                       ├── httpx (HTTP 客户端，绕过 Cloudflare)
                       ├── feedparser (RSS/Atom 解析)
                       └── anthropic / openai (LLM API)
```

---

## 踩坑记录

### 1. 公共 RSSHub 实例不可用

**现象**：rsshub.app、rsshub.rssforever.com 等公共实例的 OpenAI/Anthropic/DeepMind 路由全部返回 0 条。
**原因**：Cloudflare 对公共实例的共享 IP 做了限流。官方 README 也写明 "intended for testing purposes only"。
**解决**：本地自托管 RSSHub，使用 `scripts/start-rsshub.sh` 一键启动。

### 2. OpenAI 其实有原生 RSS

**发现**：`https://openai.com/news/rss.xml` 是有效的 RSS 源（978 条目），但需要浏览器 UA 才能访问。
**影响**：原本以为必须通过 RSSHub，实际上可以直接订阅。`config/sources.yaml` 已配置为使用原生 RSS。

### 3. Anthropic 和 DeepMind 没有原生 RSS

**发现**：两个公司网站都是 Next.js SPA，没有 RSS 输出端点。只能通过 RSSHub 路由获取。
**配置**：`config/sources.yaml` 中使用 `http://localhost:1200/anthropic/news` 和 `/deepmind/blog`。

### 4. Folo 必须用桌面版

**原因**：Web 版 (app.folo.is) 通过服务器端抓取 RSS，无法访问用户本机的 `localhost:1200`。
**解决**：安装 Folo 桌面版 (`brew install --cask folo`)，它直接从本机发起请求。

### 5. 部分站点反爬严格

**Sebastian Raschka 博客** (`sebastianraschka.com`) 返回 HTTP 406 拒绝 feedparser 默认 UA。
**解决**：`daily_digest.py` 使用 `httpx` + 浏览器 UA 发起请求，绕过基础反爬。

### 6. 周末内容稀少

**现象**：科技公司博客周末几乎不更新，24h 窗口可能只有几篇文章。
**解决**：`daily_digest.py` 默认回溯 3 天，工作日可改为 `--days 1`。

### 7. 4 个源暂无 RSS

Salesforce AI Research、vLLM、SGLang/LMSYS、Philipp Schmid 都是 Next.js SPA 且无 RSS 端点。目前只能手动访问。未来可通过 RSSHub 的 HTML transform 路由或社区贡献路由来解决。
