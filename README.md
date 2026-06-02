# AI News Daily

AI 领域信息自动聚合系统。从 **89 个 AI 信息源**（62 个有 RSS）自动采集，AI 整理生成中文日报/周报/月报。

## 两种使用方式

### 方式一：Claude Code 内一键生成（推荐，零配置）

在 Claude Code 中说一句话即可：

```
AI日报
AI周报
AI月报
今天有什么AI新闻
```

Claude 自动完成：环境检查 → 启动 RSSHub → 采集文章 → 分类评级(★★★) → 输出带链接的 Markdown 日报。

**不需要任何 API Key**，因为 Claude 本身就是 AI。

### 方式二：脚本独立运行

```bash
# 安装依赖
pip3 install feedparser httpx pyyaml

# 启动 RSSHub
bash scripts/start-rsshub.sh

# 生成日报（需要 Anthropic API Key）
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/daily_digest.py

# 或使用 ChatGPT
export OPENAI_API_KEY=sk-...
python3 scripts/daily_digest.py --provider openai
```

## 输出示例

日报保存至 `daily-reports/YYYY/MM/YYYY-MM-DD.md`，每篇文章标题均为可点击链接：

```markdown
# AI 日报 — 2026-06-02

## 今日要闻
Anthropic 正式向 SEC 提交 IPO 申请... [MiniMax 发布 M3 模型](https://venturebeat.com/...)

## 分类导读
### 🔥 LLM 训练与架构
| ★★★ | VentureBeat AI | [MiniMax-M3 debuts...](https://venturebeat.com/...) | 中文摘要 |
```

## 日报 vs 周报 vs 月报

| 类型 | 触发词 | 采集范围 | 格式 |
|------|------|:---:|------|
| 日报 | "AI日报" | 1-3 天 | 要闻 + 分类表格 + 统计 |
| 周报 | "AI周报" | 7 天 | 周度要闻 + 分类 + 趋势 |
| 月报 | "AI月报" | 30 天 | 十大主题深度分析 + 趋势信号 |

## 信息源覆盖

| 分类 | 源数 | 有 RSS |
|------|:---:|:---:|
| AI 公司官方博客 | 21 | 13 |
| AI 研究机构 | 6 | 6 |
| AI Engineering / Agent / LLM 实战 | 9 | 5 |
| AI 深度专栏 / Newsletter | 8 | 5 |
| AI 资讯聚合 | 10 | 8 |
| 独立研究者 / 开发者 | 8 | 7 |
| 开源 AI / GitHub 趋势 | 2 | 0 |
| 社区 / 实时信号源 | 2 | 2 |
| 中文 AI 信息源 | 5 | 1 |
| AI 社交媒体 | 11 | 11 |
| AI 视频频道 | 7 | 7 |
| **总计** | **89** | **62** |

详细列表见 [docs/ai-source.md](docs/ai-source.md)。

## 项目结构

```
AI-News-Daily/
├── config/
│   ├── sources.yaml              # 89 个信息源配置（11 分类）
│   └── ai-feeds.opml             # Folo/Feedly 可导入的 OPML
├── scripts/
│   ├── daily_digest.py           # 采集 + AI 整理主脚本
│   ├── generate_opml.py          # OPML 生成
│   └── start-rsshub.sh           # RSSHub 一键启动
├── docs/
│   ├── ai-source.md              # 信息源参考手册（80+ 源详解）
│   └── deploy-guide.md           # 部署与运维手册
├── daily-reports/                # 日报/周报/月报存档
│   └── index.html                # 归档索引（自动更新）
├── .claude/
│   └── skills/ai-digest/         # Claude Code 技能定义
│       └── SKILL.md
├── RSSHub/                       # 本地 RSSHub 实例（git clone）
└── CLAUDE.md                     # Claude Code 项目指令
```

## 命令行参考

```bash
# 仅采集不调用 AI（调试/快速预览）
python3 scripts/daily_digest.py --dry-run

# 指定回溯天数
python3 scripts/daily_digest.py --days 1
python3 scripts/daily_digest.py --days 7

# 输出到终端
python3 scripts/daily_digest.py --output -

# 指定 LLM 提供商和模型
python3 scripts/daily_digest.py --provider openai --model gpt-4.1

# 限制文章数（精简报告）
python3 scripts/daily_digest.py --max-articles 30

# 更新 OPML（编辑 sources.yaml 后）
python3 scripts/generate_opml.py
```

## 环境要求

| 组件 | 用途 | 必需? |
|------|------|:---:|
| Python 3.10+ | 脚本运行 | 是 |
| Node.js 22+ + pnpm | RSSHub（Twitter/YouTube 等 20 个源） | 可选 |
| Anthropic/OpenAI API Key | 脚本独立运行模式 | 可选 |

> Claude Code 模式下不需要 API Key，也无需 Node.js（RSSHub 只在需要 Twitter/YouTube 源时才启动）。

## 定时运行

```bash
# 每个工作日早上 8:00 生成日报（需 API Key）
0 8 * * 1-5 cd ~/work_dir/AI-News-Daily && \
  ANTHROPIC_API_KEY=sk-ant-... python3 scripts/daily_digest.py --days 1
```

## 文档

- [信息源参考手册](docs/ai-source.md) — 90+ 源分类详解与黄金组合推荐
- [部署与运维手册](docs/deploy-guide.md) — 环境搭建、故障排查、添加新源
