#!/usr/bin/env python3
"""AI 每日信息汇总 — 采集 RSS 源，用 Claude / ChatGPT 整理成中文日报。

依赖: pip install -r requirements.txt

用法:
    # Claude 模式（默认）
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
    daily-reports/YYYY/MM/YYYY-MM-DD.md     # Markdown 日报
    daily-reports/YYYY/MM/YYYY-MM-DD.html   # HTML 日报
    daily-reports/index.html                # 归档索引
"""

from __future__ import annotations

import argparse
import html as html_module
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

import feedparser
import httpx
import yaml

# Optional: LLM SDKs
try:
    import anthropic  # noqa: F401
except ImportError:
    anthropic = None  # type: ignore

try:
    from openai import OpenAI  # noqa: F401
except ImportError:
    OpenAI = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = PROJECT_ROOT / "config" / "sources.yaml"
OUTPUT_DIR = PROJECT_ROOT / "daily-reports"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
RETRY_MAX = 3
RETRY_BACKOFF = 2  # seconds, exponential


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
    """Fetch one RSS feed with retry on transient errors."""
    articles: list[Article] = []

    for attempt in range(1, RETRY_MAX + 1):
        try:
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
                return articles  # don't retry client/server errors

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
            return articles  # success

        except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as e:
            if attempt < RETRY_MAX:
                wait = RETRY_BACKOFF ** attempt
                print(
                    f"  [RETRY] {source['name']}: attempt {attempt}/{RETRY_MAX}, "
                    f"waiting {wait}s ({e})",
                    file=sys.stderr,
                )
                time.sleep(wait)
            else:
                print(f"  [WARN] {source['name']}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"  [WARN] {source['name']}: {e}", file=sys.stderr)
            return articles

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


# ── AI prompt ──


def build_prompt(articles: list[Article], days: int) -> str:
    """Build the AI prompt with all articles to summarize."""
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
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
# AI 日报 — {today_str}

## 今日要闻

（100-150 字概述）

## 分类导读

### 🔥 LLM 训练与架构

| 标记 | 来源 | 标题 | 摘要 |
|------|------|------|------|
| ★★★ | OpenAI | GPT-5 发布 | 一句话中文摘要...

（无文章的类别可省略）

## 统计

- 总计文章：{len(articles)} 篇
- ★★★ 必读：X 篇
- ★★☆ 推荐：X 篇
```

只输出上述 Markdown，不要添加其他说明。"""

    return prompt


# ── AI API ──


def call_claude(prompt: str, api_key: str, model: str) -> str:
    """Call Claude API and return the response text."""
    if anthropic is None:
        raise ImportError(
            "anthropic package not installed. Run: pip install anthropic"
        )
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system="你是一位专业的 AI 领域信息分析师，擅长整理和分类 AI 技术文章，输出格式化的中文 Markdown 报告。",
        messages=[{"role": "user", "content": prompt}],
    )
    result = ""
    for block in message.content:
        if hasattr(block, "text"):
            result += block.text
    return result


def call_openai(prompt: str, api_key: str, model: str) -> str:
    """Call OpenAI API (ChatGPT) and return the response text."""
    if OpenAI is None:
        raise ImportError("openai package not installed. Run: pip install openai")
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


# ── Output helpers ──


def _html_page(title: str, body_html: str) -> str:
    """Wrap body content in a minimal, readable HTML page."""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_module.escape(title)}</title>
<style>
  body {{
    max-width: 800px; margin: 0 auto; padding: 2rem 1rem;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.7; color: #1a1a1a; background: #fff;
  }}
  h1 {{ font-size: 1.6rem; border-bottom: 2px solid #e5e5e5; padding-bottom: .5rem; }}
  h2 {{ font-size: 1.25rem; margin-top: 2rem; }}
  h3 {{ font-size: 1.05rem; margin-top: 1.5rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: .75rem 0; font-size: .9rem; }}
  th, td {{ border: 1px solid #ddd; padding: .5rem .6rem; text-align: left; }}
  th {{ background: #f5f5f5; font-weight: 600; }}
  a {{ color: #2563eb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .back {{ margin-top: 2rem; font-size: .9rem; }}
</style>
</head>
<body>
{body_html}
<p class="back"><a href="../../index.html">← 归档索引</a></p>
</body>
</html>"""


def _md_to_html(md_text: str) -> str:
    """Minimal Markdown-to-HTML converter for the daily digest format.

    Handles the subset used in AI日报: headings, tables, bold, links, paragraphs.
    """
    lines = md_text.split("\n")
    out: list[str] = []
    in_table = False
    in_thead = False

    for line in lines:
        stripped = line.strip()

        # Table
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            if all(c.startswith("---") or c.startswith(":--") for c in cells if c):
                # separator row, skip
                continue
            if not in_table:
                out.append("<table>")
                in_table = True
                in_thead = True

            tag = "th" if in_thead else "td"
            row = "".join(f"<{tag}>{html_module.escape(c)}</{tag}>" for c in cells)
            out.append(f"<tr>{row}</tr>")

            if in_thead:
                in_thead = False
            continue
        elif in_table:
            out.append("</table>")
            in_table = False
            in_thead = False

        # Headings
        if stripped.startswith("# ") and not stripped.startswith("## "):
            out.append(f"<h1>{_inline_md(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            out.append(f"<h2>{_inline_md(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            out.append(f"<h3>{_inline_md(stripped[4:])}</h3>")
        elif stripped == "":
            continue
        else:
            out.append(f"<p>{_inline_md(stripped)}</p>")

    if in_table:
        out.append("</table>")

    return "\n".join(out)


def _inline_md(text: str) -> str:
    """Convert inline markdown (bold, links) to HTML."""
    # Bold: **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Link: [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{html_module.escape(m.group(2))}">{html_module.escape(m.group(1))}</a>',
        text,
    )
    return text


def write_output(markdown: str, out_path: Path) -> None:
    """Write Markdown, HTML, and update the archive index."""
    # 1. Markdown file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"Markdown: {out_path}")

    # 2. HTML file
    html_path = out_path.with_suffix(".html")
    today_str = out_path.stem  # YYYY-MM-DD
    title = f"AI 日报 — {today_str}"
    body = _md_to_html(markdown)
    html_path.write_text(_html_page(title, body), encoding="utf-8")
    print(f"HTML:     {html_path}")

    # 3. Archive index
    _update_index(OUTPUT_DIR)


def _update_index(reports_dir: Path) -> None:
    """Rebuild daily-reports/index.html listing all past digests."""
    # Collect all report dirs (YYYY/MM/DD.md)
    entries: list[tuple[str, str]] = []  # (date_str, rel_path)
    for md_file in sorted(reports_dir.rglob("*.md"), reverse=True):
        rel = md_file.relative_to(reports_dir)
        date_str = md_file.stem  # YYYY-MM-DD
        entries.append((date_str, str(rel)))

    if not entries:
        return

    rows = ""
    for date_str, rel_path in entries:
        html_rel = rel_path.replace(".md", ".html")
        rows += f"<tr><td>{date_str}</td><td><a href=\"{html_rel}\">HTML</a> · <a href=\"{rel_path}\">Markdown</a></td></tr>\n"

    index_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 日报 归档</title>
<style>
  body {{
    max-width: 800px; margin: 0 auto; padding: 2rem 1rem;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.7; color: #1a1a1a;
  }}
  h1 {{ font-size: 1.6rem; border-bottom: 2px solid #e5e5e5; padding-bottom: .5rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
  th, td {{ border: 1px solid #ddd; padding: .5rem .8rem; text-align: left; }}
  th {{ background: #f5f5f5; }}
  a {{ color: #2563eb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .count {{ color: #666; font-size: .9rem; margin-bottom: 1rem; }}
</style>
</head>
<body>
<h1>AI 日报 归档</h1>
<p class="count">共 {len(entries)} 期</p>
<table>
<tr><th>日期</th><th>链接</th></tr>
{rows}
</table>
</body>
</html>"""

    index_path = reports_dir / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    print(f"Index:    {index_path}")


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
    try:
        if config.provider == "openai":
            markdown = call_openai(prompt, config.api_key, config.model)
        else:
            markdown = call_claude(prompt, config.api_key, config.model)
    except Exception as e:
        print(f"\n[ERROR] AI API call failed: {e}", file=sys.stderr)
        print("Saving raw article list as fallback...", file=sys.stderr)
        markdown = _fallback_digest(all_articles)

    return markdown


def _fallback_digest(articles: list[Article]) -> str:
    """Generate a simple digest when the AI API is unavailable."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# AI 日报 — {today_str}",
        "",
        "> AI 摘要暂不可用，以下是今日采集的文章列表。",
        "",
        "| 来源 | 标题 |",
        "|------|------|",
    ]
    for a in articles:
        lines.append(f"| {a.source_name} | [{a.title}]({a.url}) |")
    lines.extend([
        "",
        f"---",
        f"共 {len(articles)} 篇文章，来自 {len(set(a.source_name for a in articles))} 个来源。",
    ])
    return "\n".join(lines)


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
        help="Print AI prompt and exit (pipe to any LLM)",
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

    # Write to daily-reports/YYYY/MM/YYYY-MM-DD.md (and .html, and update index)
    today = datetime.now(timezone.utc)
    out_dir = OUTPUT_DIR / str(today.year) / f"{today.month:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{today.strftime('%Y-%m-%d')}.md"
    write_output(markdown, out_path)


if __name__ == "__main__":
    main()
