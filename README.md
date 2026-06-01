# AI News Aggregator

AI 领域信息自动聚合系统。从 22 个 AI 信息源自动采集文章，AI 整理生成中文日报（Markdown + HTML），支持 RSS 可视化阅读。

- **日报模式**：Claude / ChatGPT 自动整理生成中文日报，输出 Markdown + HTML，自动维护归档索引
- **Folo 模式**：可视化 RSS 阅读，AI 辅助摘要 + 翻译

## 快速开始

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env 填入 ANTHROPIC_API_KEY

# 3. 启动本地 RSSHub（首次运行会自动 clone + build）
bash scripts/start-rsshub.sh

# 4. 生成 AI 日报
python3 scripts/daily_digest.py
```

## 日报输出

每次运行生成 3 个文件：

```
daily-reports/
├── index.html              # 归档索引（所有历史日报）
└── YYYY/
    └── MM/
        ├── YYYY-MM-DD.md   # Markdown 日报
        └── YYYY-MM-DD.html # HTML 日报（浏览器直接打开）
```

用浏览器打开 `daily-reports/index.html` 即可浏览所有历史日报。

## 信息源覆盖

| 分类 | 数量 | 状态 |
|------|:----:|:----:|
| AI 公司官方博客 | 7 | 4 可用 |
| AI News 聚合平台 | 9 | 9 可用 |
| 个人开发者 | 6 | 5 可用 |
| **总计** | **22** | **18 可用** |

详细列表见 `config/sources.yaml` 或 `docs/ai-source.md`。

## 目录结构

```
ai-news-aggregator/
├── config/
│   ├── sources.yaml          # 22 个信息源配置
│   └── ai-feeds.opml         # Folo 导入文件
├── scripts/
│   ├── generate_opml.py      # OPML 生成
│   ├── daily_digest.py       # AI 日报生成
│   └── start-rsshub.sh       # RSSHub 启动
├── docs/
│   ├── ai-news-aggregator-setup.md
│   ├── ai-source.md
│   └── review-report.md      # 产品审查报告
├── RSSHub/                   # 本地 RSSHub 实例（git clone）
├── requirements.txt
└── .env.example
```

## 命令行选项

```bash
# 仅采集文章列表（不调用 AI）
python3 scripts/daily_digest.py --dry-run

# 输出 prompt 文本，可管道给任意 LLM
python3 scripts/daily_digest.py --prompt-only

# 使用 ChatGPT
python3 scripts/daily_digest.py --provider openai

# 指定模型
python3 scripts/daily_digest.py --model claude-opus-4-6-20250514

# 仅处理最近 1 天的文章
python3 scripts/daily_digest.py --days 1
```

## 定时运行

```bash
# 每个工作日早上 8:00 生成日报
0 8 * * 1-5 cd ~/work_dir/ai-news-aggregator && \
  ANTHROPIC_API_KEY=sk-ant-... python3 scripts/daily_digest.py --days 1
```

## 依赖

- Node.js >= 18 + pnpm（运行 RSSHub）
- Python >= 3.9（脚本）
- Folo 桌面版（可视化阅读，可选）
- Anthropic API Key 或 OpenAI API Key（AI 日报）
