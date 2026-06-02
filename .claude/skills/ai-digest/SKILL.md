---
name: ai-digest
description: Use when the user asks for AI daily news (日报/digest/今天有什么AI新闻/AI日报), wants to run the AI digest script, or troubleshoot the AI news aggregator pipeline. Generates a categorized Chinese AI news digest from 62 RSS sources using Claude/ChatGPT.
---

## Overview

Generates a structured Chinese AI news digest from 62 RSS sources by:
1. Fetching articles from all configured sources via HTTpx
2. Deduplicating with 85% title similarity threshold
3. Calling the Claude or ChatGPT API to categorize, summarize, and rate articles
4. Saving the result as Markdown + HTML to `daily-reports/YYYY/MM/YYYY-MM-DD.{md,html}`

## Pre-flight Checklist

Before running the digest, verify these in order:

### 1. Check RSSHub is running (only needed for rsshub-type sources)

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:1200/openai/news 2>/dev/null || echo "RSSHub not running"
```

If HTTP code != 200, offer to start RSSHub: `bash scripts/start-rsshub.sh`
Wait for the startup message "RSSHub is ready!" before proceeding.

### 2. Check API key is set

```bash
echo "${ANTHROPIC_API_KEY:0:15}..." 2>/dev/null || echo "ANTHROPIC_API_KEY not set"
```

If not set, tell the user to export it first. For OpenAI mode, check `OPENAI_API_KEY`.

## Execution

Run from the project root (`/Users/jianzhengnie/work_dir/ai-news-aggregator`):

### Basic usage (smart defaults)

```bash
python3 scripts/daily_digest.py
```

### Smart day selection

The `--days` parameter controls how far back to look. Choose based on context:

| Situation | `--days` |
|---|---|
| Monday (to cover weekend) | `3` |
| Tuesday–Friday (workday) | `1` |
| Saturday–Sunday (low volume) | `2` |
| User explicitly requests N days | whatever user says |
| User says "this week" | `7` |

### Common variations

```bash
# See what's available without calling AI (fast, free)
python3 scripts/daily_digest.py --dry-run

# Use ChatGPT instead of Claude
python3 scripts/daily_digest.py --provider openai

# Specific model
python3 scripts/daily_digest.py --provider anthropic --model claude-sonnet-4-6-20250514

# Limit to 30 articles in the prompt (tighter report)
python3 scripts/daily_digest.py --max-articles 30

# Output to stdout instead of a file
python3 scripts/daily_digest.py --output -

# Just print the AI prompt (debugging, or pipe to another LLM)
python3 scripts/daily_digest.py --prompt-only
```

### When user specifies parameters

Map user language to flags naturally:

| User says | Use these flags |
|---|---|
| "只需要最近一天的" | `--days 1` |
| "这周的AI新闻" | `--days 7` |
| "先看看有多少文章" | `--dry-run` |
| "用ChatGPT生成" | `--provider openai` |
| "用GPT-5生成" | `--provider openai --model gpt-5` |
| "输出到终端就行" | `--output -` |
| "精简一点" | `--max-articles 20` |

## Post-run Actions

### On success

1. Report the output file path (e.g. `daily-reports/2026/06/01/2026-06-01.md`)
2. Optionally read the report and summarize key headlines to the user (3-5 top stories with ★★★ ratings)
3. Mention the HTML version for browser viewing

### On failure

Diagnose and report based on the error:

| Error pattern | Diagnosis | Fix |
|---|---|---|
| `Connection refused` / `Could not resolve host` on localhost:1200 | RSSHub not running | `bash scripts/start-rsshub.sh` |
| `HTTP 403` / `HTTP 406` from a source | Anti-bot protection blocked this source | Skip this source; the script retries 3 times automatically |
| `0 articles fetched` | Weekend + short `--days` | Increase `--days` to 3 |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` error | API key missing | Tell user to export the key |
| `API error` / `Rate limit` | API service issue | Wait and retry, or fall back to `--provider` switch |
| YAML parse error in sources.yaml | Broken config | Check `config/sources.yaml` syntax |

### Fallback on AI API failure

The script automatically generates a simple article list (no AI summaries) if the API call fails. Tell the user this happened and they can check the raw output.

## Output Format

The generated report uses this structure (Markdown):

```
# AI 日报 — YYYY-MM-DD

## 今日要闻
(100-150 word overview)

## 分类导读

### 🔥 LLM 训练与架构
| ★★★ | Source | Title | Summary (Chinese) |

### ⚡ 推理优化与部署
...

## 统计
- Total: N articles
- ★★★ Must read: N
- ★★☆ Recommended: N
- ★☆☆ Optional: N
```

## Project-specific Notes

- **62 of 89 sources have RSS** — the script auto-filters to only those with non-null `rss` in `config/sources.yaml`
- **20 RSSHub-dependent sources** (Anthropic, DeepMind, Twitter feeds, YouTube channels) go through local RSSHub at `localhost:1200`
- **Reports saved to** `daily-reports/YYYY/MM/` with both `.md` and `.html` versions
- **Archive index** at `daily-reports/index.html` is auto-regenerated on each run
- **Deduplication uses 85% title similarity** via Python `SequenceMatcher`
- **Retry logic**: 3 attempts with exponential backoff (2^1, 2^2, 2^3 seconds) per feed
- **Browser UA spoofing**: Uses Chrome macOS UA to bypass basic Cloudflare protection
