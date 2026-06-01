# AI News Aggregator — 产品深度审查报告

> 审查日期：2026-06-01
> 审查范围：全项目（8 个源文件，22 个信息源配置）

---

## 1. 产品定位与核心价值

**一句话定义**：每天早上，自动从 22 个 AI 信息源采集文章，由 Claude/ChatGPT 整理成一份带主题分类和重要度标注的中文日报。

**目标用户**：需要高效跟进 AI 领域动态的工程师/研究员（很可能是你自己）。

**核心路径**：
```
crontab 触发 → 采集 18 个 RSS → 去重 → AI 整理 → 输出 Markdown 日报
```

---

## 2. 当前状态评估

### 2.1 做得好的部分

| 维度 | 评价 |
|------|------|
| 信息源覆盖 | 22 个来源，精心筛选，覆盖公司/媒体/个人三大类，AI 生态全貌 |
| RSS 验证 | 18/22（82%）已验证可用，逐一标注状态和采集方式 |
| 双模式设计 | Folo 可视化 + AI 日报，覆盖浏览和推送两种需求 |
| 反爬方案 | 本地 RSSHub 绕过 Cloudflare，httpx + 浏览器 UA 绕过基础反爬 |
| 踩坑记录 | 7 条实战经验，对后来者很有价值 |
| 文档完整度 | setup.md 覆盖了从安装到定时运行的全流程 |

### 2.2 存在问题的部分

| 维度 | 问题 | 严重度 |
|------|------|--------|
| 可靠性 | 无 RSS 重试机制，单次网络抖动丢文章 | 🔴 高 |
| 可靠性 | 无跨运行去重，同一天跑两次产生重复日报 | 🔴 高 |
| 可维护性 | 无 `requirements.txt`，依赖散落在 docstring 里 | 🟡 中 |
| 可维护性 | `import anthropic` / `from openai import OpenAI` 仍在函数内部 | 🟡 中 |
| 产品体验 | 日报是纯 Markdown 文件，无可视化浏览/归档索引 | 🟡 中 |
| 产品体验 | 无历史日报列表，查看过往只能手动翻目录 | 🟡 中 |
| 信息覆盖 | 4 个源（Salesforce、vLLM、SGLang、Phil Schmid）无 RSS，无替代方案 | 🟢 低 |
| 安全性 | API Key 直接写在 crontab 示例中 | 🟡 中 |

---

## 3. 架构分析

### 3.1 当前架构

```
sources.yaml ─┬── generate_opml.py ──► ai-feeds.opml ──► Folo（手动阅读）
              │
              └── daily_digest.py ──► Claude/ChatGPT ──► daily-reports/YYYY/MM/DD.md
```

### 3.2 架构缺陷

**A. 无状态设计**：`daily_digest.py` 每次运行都是"全新"的 —— 没有记住上次采集了哪些文章，没有缓存。这导致：
- 重复运行产生重复内容
- 源临时故障 → 文章永久丢失（没有重试队列）
- 无法做"过去 24 小时"与"上次运行至今"的增量采集

**B. 输出单一**：只有 Markdown 文件。缺乏：
- HTML 渲染版本（在浏览器中阅读体验更好）
- 归档索引页（`daily-reports/index.html`）
- 搜索能力

**C. 缺少反馈闭环**：用户读完日报后无法标记"感兴趣/不感兴趣"，系统无法学习偏好。

### 3.3 建议的目标架构

```
crontab 触发
     │
     ▼
daily_digest.py
     │
     ├── 1. 加载 sources.yaml
     ├── 2. 采集 18 个 RSS（带重试 + 缓存）
     ├── 3. 与 SQLite 对比，过滤已见文章
     ├── 4. 去重 + 排序
     ├── 5. 调用 Claude/ChatGPT 整理
     ├── 6. 写入：
     │   ├── daily-reports/YYYY/MM/DD.md     # Markdown
     │   ├── daily-reports/YYYY/MM/DD.html    # HTML（可浏览器打开）
     │   └── daily-reports/index.html          # 归档索引（更新）
     └── 7. 标记已发送文章到 SQLite
```

---

## 4. 代码质量 Review

### 4.1 `daily_digest.py`（417 行）

| 项目 | 评分 | 说明 |
|------|:----:|------|
| 整体结构 | B+ | 函数拆分清晰，dataclass 使用得当 |
| 错误处理 | C | 采集异常只 warn 不重试；API 调用无异常捕获 |
| 类型注解 | B+ | 大部分有类型注解，少数地方缺 |
| 配置管理 | B | 环境变量 + CLI args，但没有 config file 支持 |
| 可测试性 | C | 无测试文件，所有逻辑混在 run() 里 |

**具体问题**：
- `call_claude()` 内 `import anthropic`（应放文件顶部）
- `call_openai()` 内 `from openai import OpenAI`（同上）
- 无重试逻辑（`fetch_feed` 失败直接返回空列表）
- 无 API 调用异常处理
- `build_prompt` 中的日期使用 `datetime.now()` 硬编码 —— 实际日报日期应该是今天

### 4.2 `generate_opml.py`（92 行）

| 项目 | 评分 | 说明 |
|------|:----:|------|
| 整体结构 | A- | 简洁、单一职责 |
| 代码质量 | B+ | 清晰但缺少错误处理 |

### 4.3 `start-rsshub.sh`（56 行）

| 项目 | 评分 | 说明 |
|------|:----:|------|
| 健壮性 | B+ | set -euo pipefail，健康检查，重复启动检测 |
| 可维护性 | B | 逻辑清晰，注释偏少 |

---

## 5. 改进方案（按优先级）

### P0 — 必须修复（影响核心功能可靠性）

1. **添加 `requirements.txt`** — 统一依赖管理
2. **添加 RSS 获取重试** — 3 次重试 + 指数退避
3. **添加 API 调用异常处理** — Claude/ChatGPT 失败时保存原始文章列表
4. **修复 import 位置** — `anthropic` 和 `openai` 移到文件顶部
5. **添加 `.env.example`** — 明确需要的环境变量

### P1 — 应该修复（影响产品体验）

6. **生成 HTML 版日报** — 同目录下输出 `.html` 文件
7. **生成归档索引页** — `daily-reports/index.html` 列出所有历史日报
8. **添加 `--config` 选项** — 支持通过 yaml 配置 API key 等

### P2 — 可以后续迭代

9. **SQLite 持久化** — 跟踪已见文章，支持增量采集
10. **为 4 个缺失源添加 RSSHub HTML 路由**
11. **添加 `--serve` 模式** — 启动本地 HTTP 服务器浏览归档
12. **添加测试**

---

## 6. 实施计划（本次迭代）

本轮实施 P0 全部 + P1 中的 HTML 生成和归档索引：

1. 添加 `requirements.txt` + `.env.example`
2. 重构 `daily_digest.py`：重试逻辑、API 异常处理、import 整理
3. 添加 HTML 日报生成
4. 添加归档索引页自动更新
5. 端到端验证：`--dry-run` → `--prompt-only` → 完整运行
