#!/usr/bin/env python3
"""AI 每日信息汇总 — 采集 RSS 源，用 Claude / ChatGPT 整理成中文日报。

依赖: pip install anthropic feedparser httpx pyyaml
      (OpenAI 模式额外需要: pip install openai)

用法:
    # Claude 模式
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 scripts/daily_digest.py                    # 处理最近 3 天
    python3 scripts/daily_digest.py --days 1           # 仅最近 24h

    # ChatGPT 模式
    export OPENAI_API_KEY=sk-...
    python3 scripts/daily_digest.py --provider openai

    # 调试 & 管道模式
    python3 scripts/daily_digest.py --dry-run          # 仅采集，不调用 AI
    python3 scripts/daily_digest.py --prompt-only      # 输出 prompt，可管道给任意 LLM
    python3 scripts/daily_digest.py --output -         # 日报输出到 stdout

输出:
    daily-reports/YYYY/MM/YYYY-MM-DD.md    # 日报 Markdown
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

import feedparser
import httpx
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = PROJECT_ROOT / "config" / "sources.yaml"
OUTPUT_DIR = PROJECT_ROOT / "daily-reports"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# ── Data classes ──


@dataclass
class Article:
    title: str
    url: str
    source_name: str
    published: datetime | None = None
    summary: str = ""
    category: str = ""


@dataclass
class DigestConfig:
    days: int = 1
    dry_run: bool = False
    prompt_only: bool = False
    output: str = ""
    model: str = ""
    max_articles: int = 50
    api_key: str = ""
    provider: str = "anthropic"


# ── RSS fetching ──


def load_sources(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return [s for s in config["sources"] if s["rss"]]


def fetch_feed(source: dict, since: datetime) -> list[Article]:
    """Fetch one RSS feed and extract articles newer than `since`."""
    articles: list[Article] = []
    try:
        # Use httpx with browser UA to bypass Cloudflare
        resp = httpx.get(
            source["rss"],
            headers={"User-Agent": UA},
            timeout=15,
            follow_redirects=True,
        )
        if resp.status_code >= 400:
            print(
                f"  [WARN] {source['name']}: HTTP {resp.status_code}",
                file=sys.stderr,
            )
            return articles
        parsed = feedparser.parse(resp.text)
        if parsed.bozo and not parsed.entries:
            if resp.status_code == 200:
                print(
                    f"  [WARN] {source['name']}: parse error ({parsed.bozo_exception})",
                    file=sys.stderr,
                )
            return articles

        for entry in parsed.entries:
            pub = _extract_date(entry)
            if pub and pub < since:
                continue
            if not pub:
                pub = datetime.now(timezone.utc)

            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            summary = ""
            if entry.get("summary"):
                summary = _strip_html(entry.summary)[:300]
            elif entry.get("description"):
                summary = _strip_html(entry.description)[:300]

            articles.append(
                Article(
                    title=title,
                    url=link,
                    source_name=source["name"],
                    published=pub,
                    summary=summary,
                    category=source["category"],
                )
            )
    except Exception as e:
        print(f"  [WARN] {source['name']}: {e}", file=sys.stderr)

    return articles


def _extract_date(entry: dict) -> datetime | None:
    for field in ("published_parsed", "updated_parsed"):
        tp = entry.get(field)
        if tp and len(tp) >= 6:
            try:
                return datetime(*tp[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass
    return None


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def deduplicate(articles: list[Article], threshold: float = 0.85) -> list[Article]:
    """Remove articles with highly similar titles."""
    seen: list[Article] = []
    for a in sorted(articles, key=lambda x: x.published or datetime.min, reverse=True):
        if any(
            SequenceMatcher(None, a.title.lower(), s.title.lower()).ratio() > threshold
            for s in seen
        ):
            continue
        seen.append(a)
    return seen


# ── Claude API ──


def build_prompt(articles: list[Article], days: int) -> str:
    """Build the Claude prompt with all articles to summarize."""
    lines = []
    for i, a in enumerate(articles, 1):
        pub_str = a.published.strftime("%Y-%m-%d") if a.published else "未知"
        lines.append(f"{i}. [{a.source_name}] {a.title}")
        lines.append(f"   链接: {a.url}")
        lines.append(f"   日期: {pub_str}")
        if a.summary:
            lines.append(f"   摘要: {a.summary}")
        lines.append("")

    article_list = "\n".join(lines)

    prompt = f"""你是一位资深的 AI 领域信息分析师。请对以下 {len(articles)} 篇 AI 领域文章进行整理和分类。

## 任务

1. **按主题分类**：将文章归类到以下主题（可自拟子类别）：
   - LLM 训练与架构（新模型发布、训练技术、架构创新）
   - 推理优化与部署（vLLM、SGLang、量化、推理加速）
   - AI Agent 与工具（Agent 框架、工具调用、代码生成）
   - 多模态（图像、视频、音频理解与生成）
   - 开源动态（开源模型、数据集、社区）
   - 安全与对齐（红队测试、安全研究、政策监管）
   - 其他

2. **标注重要程度**：
   - ★★★ 必读 — 重大发布、突破性技术、行业变革
   - ★★☆ 推荐 — 有深度的技术文章、重要更新
   - ★☆☆ 可选 — 一般性新闻、案例分享

3. **生成中文摘要**：对 ★★★ 和 ★★☆ 的文章，各写一句中文摘要（20-40 字）

4. **生成今日 AI 早报**：在报告顶部写一段 100-150 字的今日 AI 要闻概述

## 文章列表

{article_list}

## 输出格式

请严格按以下 Markdown 格式输出：

```markdown
# AI 日报 — {datetime.now(timezone.utc).strftime("%Y-%m-%d")}

## 今日要闻

（100-150 字概述）

## 分类导读

### 🔥 LLM 训练与架构

| 标记 | 来源 | 标题 | 摘要 |
|------|------|------|------|
| ★★★ | OpenAI | GPT-5 发布 | 一句话中文摘要... |

### ⚡ 推理优化与部署

（同上格式）

### 🤖 AI Agent 与工具

...（依此类推，无文章的类别可省略）

## 统计

- 总计文章：{len(articles)} 篇
- ★★★ 必读：X 篇
- ★★☆ 推荐：X 篇
```

只输出上述 Markdown，不要添加其他说明。"""

    return prompt


def call_claude(prompt: str, api_key: str, model: str) -> str:
    """Call Claude API and return the response text."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system="你是一位专业的 AI 领域信息分析师，擅长整理和分类 AI 技术文章，输出格式化的中文 Markdown 报告。",
        messages=[{"role": "user", "content": prompt}],
    )
    # Extract text from response
    result = ""
    for block in message.content:
        if hasattr(block, "text"):
            result += block.text
    return result


def call_openai(prompt: str, api_key: str, model: str) -> str:
    """Call OpenAI API (ChatGPT) and return the response text."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {
                "role": "system",
                "content": "你是一位专业的 AI 领域信息分析师，擅长整理和分类 AI 技术文章，输出格式化的中文 Markdown 报告。",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""


# ── Main pipeline ──


def run(config: DigestConfig) -> str:
    since = datetime.now(timezone.utc) - timedelta(days=config.days)
    sources = load_sources(SOURCES_FILE)
    print(f"Fetching {len(sources)} RSS feeds (since {since.strftime('%Y-%m-%d')})...")

    all_articles: list[Article] = []
    for src in sources:
        articles = fetch_feed(src, since)
        all_articles.extend(articles)
        if articles:
            print(f"  {src['name']}: {len(articles)} articles")

    all_articles = deduplicate(all_articles)
    all_articles = sorted(
        all_articles, key=lambda a: a.published or datetime.min, reverse=True
    )
    all_articles = all_articles[: config.max_articles]

    print(f"\nTotal: {len(all_articles)} articles (deduplicated)")

    if not all_articles:
        print("No new articles found.")
        return ""

    if config.dry_run:
        for a in all_articles:
            print(f"  [{a.source_name}] {a.title}")
            print(f"    {a.url}")
        return ""

    prompt = build_prompt(all_articles, config.days)

    if config.prompt_only:
        print(prompt)
        return ""

    if not config.model:
        config.model = (
            "claude-sonnet-4-6-20250514"
            if config.provider == "anthropic"
            else "gpt-4.1"
        )

    print(f"Calling AI API ({config.model})...")
    if config.provider == "openai":
        markdown = call_openai(prompt, config.api_key, config.model)
    else:
        markdown = call_claude(prompt, config.api_key, config.model)

    return markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="AI daily digest generator")
    parser.add_argument(
        "--days",
        type=int,
        default=3,
        help="Days to look back (default: 3 for weekend coverage)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Fetch only, no AI call")
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Print Claude prompt and exit (pipe to any LLM)",
    )
    parser.add_argument("--output", default="", help="Output path (or - for stdout)")
    parser.add_argument("--max-articles", type=int, default=50)
    parser.add_argument(
        "--provider",
        default="anthropic",
        choices=["anthropic", "openai"],
        help="LLM provider (default: anthropic)",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Model name (default: provider-specific)",
    )
    args = parser.parse_args()

    api_key = os.environ.get(
        "ANTHROPIC_API_KEY" if args.provider == "anthropic" else "OPENAI_API_KEY", ""
    )
    if not api_key and not args.dry_run and not args.prompt_only:
        env_var = (
            "ANTHROPIC_API_KEY" if args.provider == "anthropic" else "OPENAI_API_KEY"
        )
        print(
            f"Error: Set {env_var} environment variable, or use --dry-run / --prompt-only.",
            file=sys.stderr,
        )
        sys.exit(1)

    config = DigestConfig(
        days=args.days,
        dry_run=args.dry_run,
        prompt_only=args.prompt_only,
        output=args.output,
        max_articles=args.max_articles,
        api_key=api_key,
        provider=args.provider,
        model=args.model,
    )

    markdown = run(config)
    if not markdown:
        return

    if args.output == "-":
        print(markdown)
        return

    # Write to daily-reports/YYYY/MM/YYYY-MM-DD.md
    today = datetime.now(timezone.utc)
    out_dir = OUTPUT_DIR / str(today.year) / f"{today.month:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{today.strftime('%Y-%m-%d')}.md"
    out_path.write_text(markdown, encoding="utf-8")
    print(f"\nDigest written to: {out_path}")


if __name__ == "__main__":
    main()
