---
name: ai-digest
description: AI 日报/周报/月报一键生成，零配置。触发词：AI日报、今天有什么AI新闻、AI早报、AI月报、AI周报、本周AI新闻、本月AI总结、今日AI动态、AI digest。自动检查环境→启动RSSHub→采集文章→Claude整理→输出带链接的Markdown报告。
---

## 核心设计

```
--dry-run 采集  →  Claude 分类/评级/摘要  →  保存 daily-reports/
     ↑                    ↑                        ↑
 不需要 API Key      当前对话即 AI           Markdown + 链接
```

---

## 执行流程

### Phase 1: 环境自检

```bash
# 并行检查（从项目根目录执行）
python3 -c "import feedparser, httpx, yaml" 2>&1 || echo "MISSING_DEPS"
curl -s -o /dev/null -w "%{http_code}" http://localhost:1200 2>/dev/null || echo "000"
```

| 检查结果 | 动作 |
|------|------|
| `MISSING_DEPS` | `pip3 install feedparser httpx pyyaml`，失败则提示用户手动安装 |
| RSSHub `000` | 执行 Phase 1b |
| RSSHub `200` | 跳过 Phase 1b |

### Phase 1b: 启动 RSSHub

```bash
which pnpm 2>/dev/null || npm install -g pnpm

if [ ! -d "RSSHub" ]; then
    bash scripts/start-rsshub.sh   # 自动 clone + install + build + start
else
    cd RSSHub && pnpm start --port 1200 >> ../.rsshub.log 2>&1 & cd ..
fi

# 等待就绪（最多 60s）
until curl -s --connect-timeout 1 http://localhost:1200 >/dev/null 2>&1; do sleep 2; done
```

> 注意：`cd RSSHub` 后必须 `cd ..` 回到项目根目录。后续所有命令使用绝对路径执行。

### Phase 2: 参数选择

| 用户说 | 类型 | `--days` | `--max-articles` |
|------|:---:|:---:|:---:|
| "AI日报" / "今天有什么AI新闻" | 日报 | 周一3 / 工作日1 / 周末2 | 60 |
| "AI周报" / "这周的AI新闻" / "本周AI总结" | 周报 | 7 | 100 |
| "AI月报" / "这个月的AI新闻" / "本月AI总结" | 月报 | 30 | 200 |
| "最近两天" / "昨天和今天" | 日报 | 2 | 60 |
| "精简一点" / "只要重点" | 日报 | 自动 | 20 |

### Phase 3: 采集文章

```bash
python3 /Users/robin/work_dir/AI-News-Daily/scripts/daily_digest.py --dry-run --days <N> --max-articles <M> 2>&1
```

> 始终使用绝对路径，避免 CWD 问题。

**异常处理：**

| 现象 | 动作 |
|------|------|
| `0 articles fetched` | 扩大 `--days` 重试一次 |
| RSSHub 源 503 | 忽略，42 个原生 RSS 源继续 |
| 单源超时/SSL | 脚本内置 3 次指数退避重试，最终跳过 |

### Phase 4: Claude 生成报告

采集完成后，Claude 对文章列表进行：

1. **分类**：按实际内容归类，至少包含以下维度——
   - LLM 模型与架构（新模型、训练技术、架构创新）
   - Agent 与 AI Engineering（Agent 框架、MCP、RAG、AI Coding）
   - AI 产业与商业（融资、IPO、产品发布、行业动态）
   - AI 安全与对齐（安全漏洞、红队测试、政策监管）
   - 开源与工具（开源项目、开发者工具、Infra）
   - 多模态与机器人（视频/音频/图像、具身智能、物理 AI）
2. **评级**：★★★ 必读 / ★★☆ 推荐 / ★☆☆ 可选
3. **摘要**：★★★ 和 ★★☆ 文章各配 20-40 字中文摘要
4. **链接**：**所有文章标题必须是可点击链接** `[标题](url)`，严禁纯文本标题
5. **要闻**：日报 100-150 字 / 周报 150-200 字 / 月报 200-300 字概述，关键名词嵌入链接

### Phase 5: 保存并展示

1. 保存至对应目录（日报/周报共享 `YYYY/MM/`，月报 `YYYY/MM/YYYY-MM-monthly.md`）
2. 向用户展示：概览段落 + 全部 ★★★ 必读 + 完整路径
3. 如有 `daily-reports/index.html` 归档逻辑，同步更新

---

## 输出格式（强制标准）

### 1. 表格行

```
| ★★★ | 来源名 | [文章标题](https://完整URL) | 20-40字中文摘要 |
```

**禁止**出现不带 `[text](url)` 的纯文本标题。这是硬性要求。

### 2. 要闻段落

关键事件嵌入链接：`[NVIDIA 发布 Cosmos 3](https://...) 世界模型，[Anthropic 提交 IPO](https://...)`

### 3. 页脚索引

日报末尾列出 ★☆☆ 文章链接，方便查阅：

```
---
*[来源] [标题](url) · [来源] [标题](url) · ...*
```

### 4. 日报模板

```markdown
# AI 日报 — YYYY-MM-DD

## 今日要闻
（100-150 字，关键名词带链接）

## 分类导读
### 🔥 主题一
| ★★★ | 来源 | [标题](url) | 摘要 |
### ⚡ 主题二
...

## 统计
- 总计 N 篇 | ★★★ X 篇 | ★★☆ Y 篇 | ★☆☆ Z 篇
- 来源：N 个 RSS 源

---
*[来源] [标题](url) · ...*
```

### 5. 周报模板

```markdown
# AI 周报 — YYYY-MM-DD ~ YYYY-MM-DD

## 本周要闻
（150-200 字，关键名词带链接）

## 分类导读
（同日报表格格式）

## 本周趋势
- 趋势信号1
- 趋势信号2

## 统计
（同日报）
```

### 6. 月报模板

```markdown
# AI 月报 — YYYY 年 M 月

> 统计周期 | 来源数 | 文章数

## 月度概述
（200-300 字，关键名词带链接）

## 一、主题 A → N、主题 N
（每主题含：概述段落 + 关键事件表格（含链接）+ 引用/数据点）

## 趋势信号
### 正在发生
### 即将到来

## 数据统计
| 指标 | 数值 |
| 来源 TOP5 | ... |
| 主题分布 | ... |

---
> 下月重点关注：...
```

---

## 已知限制

- Twitter/YouTube 依赖 RSSHub，503 时自动降级
- OpenAI Blog brotli 警告可忽略（httpx 已知问题）
- Anthropic 通过 RSSHub 抓取，反爬严格时可能超时
- 月报采集约 3-5 分钟，期间不要中断
