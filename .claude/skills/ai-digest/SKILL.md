---
name: ai-digest
description: AI 日报/月报一键生成，零配置。触发词：AI日报、今天有什么AI新闻、AI早报、AI月报、AI周报、今日AI动态、AI digest。自动检查环境→启动RSSHub→采集文章→Claude直接整理输出。
---

## 核心设计

```
--dry-run 采集文章  →  Claude 直接整理  →  保存 Markdown 日报
     ↑                      ↑                      ↑
  不需要 API Key       当前对话即 AI          daily-reports/
```

**不依赖外部 API Key**。Claude Code 本身就是 AI，采集后用当前对话生成日报。

---

## 一键执行流程

### Phase 1: 环境自检（并行）

```bash
# 1.1 Python 依赖
python3 -c "import feedparser, httpx, yaml" 2>&1 || echo "MISSING_DEPS"

# 1.2 RSSHub 状态
curl -s -o /dev/null -w "%{http_code}" http://localhost:1200 2>/dev/null || echo "000"
```

- 若 `MISSING_DEPS` → `pip3 install feedparser httpx pyyaml`
- 若 RSSHub 返回 `000` → 执行 Phase 1b

### Phase 1b: 启动 RSSHub（如需要）

```bash
which pnpm 2>/dev/null || npm install -g pnpm

if [ ! -d "RSSHub" ]; then
    bash scripts/start-rsshub.sh
else
    cd RSSHub && pnpm start --port 1200 >> ../.rsshub.log 2>&1 &
fi
```

等待就绪（最多 60 秒）：
```bash
until curl -s --connect-timeout 1 http://localhost:1200 >/dev/null 2>&1; do sleep 2; done
```

### Phase 2: 参数选择

日报 or 月报由用户自然语言决定：

| 用户说 | `--days` | `--max-articles` |
|------|:---:|:---:|
| "AI日报" / "今天有什么AI新闻" | 自动（周一3/工作日1/周末2） | 60 |
| "AI周报" / "这周的AI新闻" | 7 | 100 |
| "AI月报" / "这个月的AI新闻" | 30 | 200 |
| "最近两天的" | 2 | 60 |
| "精简一点" | 自动 | 20 |

### Phase 3: 采集文章（--dry-run，不需要 API Key）

```bash
python3 scripts/daily_digest.py --dry-run --days <N> --max-articles <M> 2>&1
```

异常处理：

| 现象 | 动作 |
|------|------|
| `0 articles fetched` | 扩大 `--days` 重试 |
| RSSHub 个别源 503 | 忽略，42 个原生 RSS 源继续工作 |
| 个别源超时/SSL 错误 | 脚本内置 3 次重试，最终跳过 |

### Phase 4: Claude 生成报告

采集完成后，Claude 直接对文章列表进行分类、评级、摘要，生成 Markdown 日报：

1. **分类**：按 LLM 模型、Agent/工程、AI 产业、安全对齐、开源工具、社区观点归类
2. **评级**：★★★ 必读 / ★★☆ 推荐 / ★☆☆ 可选
3. **摘要**：★★★ 和 ★★☆ 文章各配 20-40 字中文摘要
4. **链接**：**每篇文章标题必须是可点击的 Markdown 链接** `[标题](url)`，不可出现纯文本标题
5. **今日要闻**：100-150 字概述，关键名词也必须带链接

### Phase 5: 保存并展示

1. 保存至 `daily-reports/YYYY/MM/YYYY-MM-DD.md`（月报：`YYYY-MM-monthly.md`）
2. 向用户展示：今日要闻段落 + 全部 ★★★ 必读文章 + 完整报告路径

---

## 输出格式（强制）

### 表格行格式

```
| ★★★ | 来源名 | [文章标题](https://完整URL) | 20-40字中文摘要 |
```

**禁止**出现不带链接的纯文本标题。每篇文章的标题列必须是 `[title](url)` 格式。

### 今日要闻格式

要闻段落中的关键事件也必须嵌入链接：

```
[NVIDIA 发布 Cosmos 3](https://...) 世界模型，[Anthropic 提交 IPO](https://...) ...
```

### 页脚格式

日报末尾附上 ★☆☆ 文章的链接索引，方便查阅：

```
---
*[来源] [标题1](url1) · [来源] [标题2](url2) · ...*
```

---

## 日报 vs 月报 格式差异

### 日报格式

```
# AI 日报 — YYYY-MM-DD

## 今日要闻 （100-150 字）

## 分类导读
### 🔥 LLM 训练与架构
| ★★★ | 来源 | 标题 | 摘要 |

## 统计
- 总计 N 篇 | ★★★ X 篇 | ★★☆ Y 篇
```

### 月报格式

```
# AI 月报 — YYYY 年 M 月

## 月度概述 （200-300 字）

## 一、主题 A → 九、主题 I
（按趋势聚合，每个主题含表格/要点/引用）

## 值得关注的趋势信号
### 正在发生 / 即将到来

## 数据统计
（来源分布、主题占比）
```

---

## 已知限制

- **Twitter / YouTube** 依赖 RSSHub，路由 503 时自动降级为 42 个原生 RSS 源
- **OpenAI Blog** 有 brotli 解码警告（httpx 已知问题），实际不影响采集
- **Anthropic** 通过 RSSHub 抓取，反爬严格时可能超时
- 月报 `--days 30` 采集时间较长（约 3-5 分钟）

---

## 相关文件

| 文件 | 用途 |
|------|------|
| `config/sources.yaml` | 89 源配置（62 RSS） |
| `scripts/daily_digest.py` | 采集主脚本（仅用 --dry-run 模式） |
| `scripts/start-rsshub.sh` | RSSHub 一键启动 |
| `docs/deploy-guide.md` | 完整部署运维手册 |
| `docs/ai-source.md` | 信息源参考手册 |
| `daily-reports/` | 日报/月报存档目录 |
