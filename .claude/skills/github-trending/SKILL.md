---
name: github-trending
description: GitHub Trending 榜单中文深度解读，零配置。触发词：GitHub trending、GitHub 今日热点、GitHub 趋势榜、github 热门项目、github trending 分析、github 排行榜、github 热榜、今日 github。自动抓取→逐项目分析背景/原因/受众→输出带链接的Markdown报告。
---

## 核心设计

```
WebFetch github.com/trending  →  Claude 逐项目深度分析  →  保存 daily-reports/trending/
         ↑                              ↑                          ↑
    零依赖，不需要 RSSHub          当前对话即 AI             Markdown + 链接
```

---

## 执行流程

### Phase 1: 获取 Trending 数据

使用 WebFetch 抓取，prompt 为：

> "List all trending repositories with their name, description, language, stars today, total stars, and URL. Return the full list."

URL 由用户自然语言决定：

| 用户说 | WebFetch URL |
|------|------|
| "GitHub trending" / "今日热点" / "github 热榜" | `https://github.com/trending` |
| "本周 GitHub 趋势" / "这周热榜" | `https://github.com/trending?since=weekly` |
| "本月 GitHub 趋势" / "这个月热榜" | `https://github.com/trending?since=monthly` |
| "Python 热门项目" / "Python trending" | `https://github.com/trending/python` |
| "这周 TypeScript 趋势" | `https://github.com/trending/typescript?since=weekly` |
| "Rust 本周热榜" | `https://github.com/trending/rust?since=weekly` |
| "AI 相关 trending" | 抓取全部 trending，手动筛选 AI/ML/LLM/Agent 相关项目 |

**语言参数**（URL path 全小写）：`python`, `javascript`, `typescript`, `rust`, `go`, `java`, `c%2B%2B`, `c`, `jupyter-notebook`, `swift`, `kotlin`, `html`, `markdown` 等。空 = 全部语言。

### Phase 2: Claude 逐项目深度分析

对每个 trending 项目，从以下维度分析：

| 维度 | 说明 |
|------|------|
| **项目定位** | 1 句话说明做什么、解决什么问题 |
| **走红原因** | 技术突破？填补空白？社区需求爆发？大事件驱动？ |
| **技术阶段** | 早期探索 / 快速增长 / 生态成熟 |
| **与 AI 关联** | 是否与 LLM、Agent、RAG、AI Coding、MCP 等相关 |
| **目标受众** | 谁应该关注这个项目 |
| **评级** | ★★★ 必关注 / ★★☆ 值得了解 / ★☆☆ 看看即可 |

**评级标准：**

| 评级 | 标准 |
|:---:|------|
| ★★★ | 日增 500+ star 或总 star 10 万+，且有明确的技术/产业意义 |
| ★★☆ | 日增 200+ 或总 star 2 万+，细分赛道值得跟踪 |
| ★☆☆ | 常规上榜项目，了解即可 |

**特别标注：**
- 中国团队项目 → 标注
- AI/Agent/LLM 强相关 → 优先深度分析
- 教程/资源类 → 标注学习价值和难度

### Phase 3: 保存报告

```
daily-reports/trending/YYYY-MM-DD-github-trending.md        # 今日
daily-reports/trending/YYYY-MM-DD-github-trending-weekly.md  # 本周
daily-reports/trending/YYYY-MM-DD-github-trending-monthly.md # 本月
```

---

## 输出格式（强制标准）

### 1. 链接要求

**所有项目名称必须是可点击链接** `[owner/repo](https://github.com/owner/repo)`，严禁纯文本。

### 2. 日报模板

```markdown
# GitHub Trending 中文解读 — YYYY-MM-DD

> N 个项目 | 语言范围 | 时间范围

## 今日趋势概览
（100-150 字：上榜主题、社区热点方向、值得注意的信号）

## ★★★ 必关注

### [owner/repo](https://github.com/owner/repo)
- **Star**: N total / **+N today**
- **语言**: Python
- **是什么**：一句话
- **为什么火**：2-3 句中文分析（技术背景 + 市场动态 + 为什么是现在）
- **适合谁**：目标受众

（每个 ★★★ 独立一节）

## ★★☆ 值得了解

| 项目 | Star(今日/总计) | 语言 | 简介 | 解读 |
|------|:---:|:---:|------|------|
| [owner/repo](url) | +N / N | Lang | 一句话 | 为什么值得关注 |

## ★☆☆ 速览

| 项目 | Star | 语言 | 简介 |
|------|:---:|:---:|------|
| [owner/repo](url) | +N | Lang | 一句话 |

## 本期趋势信号

- **信号 1**：说明
- **信号 2**：说明

## 统计

| 指标 | 数值 |
|------|:---:|
| 上榜项目 | N |
| ★★★ / ★★☆ / ★☆☆ | N / N / N |
| AI 相关 | N 个 |
| 中国团队 | N 个 |

---
*数据：[GitHub Trending](https://github.com/trending) | 解读：Claude Code `github-trending` skill*
```

### 3. 周报/月报模板

与日报格式一致，调整标题为"本周/本月趋势概览"，趋势信号改为"本周/本月趋势信号"，增加"连续上榜项目"表格：

```markdown
## 连续上榜项目

| 项目 | 上榜次数 | 总 Star | 趋势 |
|------|:---:|:---:|------|
| [owner/repo](url) | 连续 N 天 | N | ↑ 加速 / → 稳定 |
```

---

## 分析要点速查

对每个项目的解读务必结合：

1. **技术背景**：领域发展阶段（早期/爆发/成熟），竞品情况
2. **社区信号**：star 增速的含义（突发爆发 vs 稳定增长 vs 常青树）
3. **AI 相关性**：是否与当前 AI 热点（Agent、MCP、RAG、AI Coding、TTS 等）相关
4. **工程价值**：能否解决实际生产问题
5. **中文社区**：对中国开发者是否友好（中文文档、国内可用性）

**分析深度优先级**：AI/ML/Agent 项目 > 开发者工具/Infra > 教程资源 > 其他
