# AI News Aggregator

AI 领域信息自动聚合系统。从 22 个 AI 信息源自动采集文章，支持两种使用模式：

- **Folo 模式**：可视化 RSS 阅读，AI 辅助摘要 + 翻译
- **日报模式**：Claude / ChatGPT 自动整理生成中文日报

## 快速开始

```bash
# 1. 安装 Python 依赖
pip install anthropic feedparser httpx pyyaml

# 2. 启动本地 RSSHub（首次运行会自动 clone + build）
bash scripts/start-rsshub.sh

# 3. 导入 OPML 到 Folo 桌面版（可视化阅读）
#    文件: config/ai-feeds.opml

# 4. 或直接生成 AI 日报
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/daily_digest.py
```

## 信息源覆盖

| 分类 | 数量 | 状态 |
|------|:----:|:----:|
| AI 公司官方博客 | 7 | 4 可用 |
| AI News 聚合平台 | 9 | 9 可用 |
| 个人开发者 | 6 | 5 可用 |
| **总计** | **22** | **18 可用** |

详细列表见 [完整文档](docs/ai-news-aggregator-setup.md) 或 `config/sources.yaml`。

## 目录结构

```
ai-news-aggregator/
├── config/
│   ├── sources.yaml          # 信息源配置
│   └── ai-feeds.opml         # Folo 导入文件
├── scripts/
│   ├── generate_opml.py      # OPML 生成
│   ├── daily_digest.py       # AI 日报生成
│   └── start-rsshub.sh       # RSSHub 启动
├── docs/
│   └── ai-news-aggregator-setup.md
└── prompts/
    └── prompt2.md            # 原始信息源列表
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
- Folo 桌面版（可视化阅读）
- Anthropic API Key 或 OpenAI API Key（AI 日报）
