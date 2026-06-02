# CLAUDE.md — AI News Aggregator

AI 领域信息自动聚合系统。从 89 个 AI 信息源（62 个有 RSS）自动采集文章，通过 Claude/ChatGPT API 整理生成中文日报。

## Commands

```bash
# AI 日报（默认 Claude，回溯 3 天）
python3 scripts/daily_digest.py

# 仅采集不调用 AI（调试）
python3 scripts/daily_digest.py --dry-run

# 使用 ChatGPT
python3 scripts/daily_digest.py --provider openai

# 回溯 1 天 / 7 天
python3 scripts/daily_digest.py --days 1
python3 scripts/daily_digest.py --days 7

# 输出到终端
python3 scripts/daily_digest.py --output -

# 启动本地 RSSHub
bash scripts/start-rsshub.sh

# 更新 OPML（编辑 sources.yaml 后）
python3 scripts/generate_opml.py
```

## Skills

- `/ai-digest` — AI 日报生成助手。自动检查 RSSHub 状态、选择参数、执行采集并展示结果。支持 `--dry-run` / `--provider openai` / `--days N` 等所有参数覆盖。

## Architecture

```
config/sources.yaml  →  generate_opml.py  →  config/ai-feeds.opml  →  Folo（RSS阅读器）
config/sources.yaml  →  daily_digest.py   →  Claude/ChatGPT API    →  daily-reports/*.md
```

## Key Files

| File | Purpose |
|------|---------|
| `config/sources.yaml` | 89 个 AI 信息源配置（11 个分类） |
| `scripts/daily_digest.py` | 采集 + AI 整理 → 日报 |
| `scripts/generate_opml.py` | 生成 Folo 可导入的 OPML |
| `scripts/start-rsshub.sh` | 启动本地 RSSHub（端口 1200） |
| `docs/ai-source.md` | 信息源参考手册 |
