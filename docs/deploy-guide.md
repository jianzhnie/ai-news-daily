# AI News Daily 部署与运维手册

## 环境准备

### 系统依赖

```bash
# Python 3.10+
python3 --version

# Node.js 22+ (RSSHub 需要)
node --version    # v26.0.0+
npm --version     # 11+

# pnpm (RSSHub 包管理器)
npm install -g pnpm
```

### Python 依赖

```bash
pip3 install feedparser httpx pyyaml
# 可选：AI API 调用
pip3 install anthropic openai
```

---

## RSSHub 部署

RSSHub 为部分源（Anthropic、Twitter、YouTube 等）提供 RSS 桥接，需本地运行。

### 首次安装

```bash
# 克隆 RSSHub（约 1-2 分钟）
git clone https://github.com/DIYgod/RSSHub.git --depth 1 RSSHub
cd RSSHub

# 安装依赖（约 1-2 分钟）
pnpm i

# 构建（约 10 秒）
pnpm build

cd ..
```

> `scripts/start-rsshub.sh` 会自动完成克隆、安装和构建。但如果 pnpm 未安装会失败，需先 `npm install -g pnpm`。

### 启动

```bash
# 后台启动（端口 1200）
bash scripts/start-rsshub.sh

# 或手动启动
cd RSSHub && pnpm start --port 1200 &
```

### 健康检查

```bash
# 确认 RSSHub 已就绪
curl -s -o /dev/null -w "%{http_code}" http://localhost:1200/openai/news

# 预期：200（路由可用）或 503（路由有错误，但服务在运行）
# 000 表示 RSSHub 未启动
```

### 重新部署

如果 RSSHub 路由更新或有重大变更：

```bash
cd RSSHub
git pull
pnpm i
pnpm build
cd ..
# 重启 RSSHub
kill $(cat .rsshub.pid) 2>/dev/null
bash scripts/start-rsshub.sh
```

---

## 日报采集

### 基础用法

```bash
# 完整日报（采集 + AI 整理）
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/daily_digest.py

# 看有哪些文章（不调用 AI，快速免费）
python3 scripts/daily_digest.py --dry-run

# 只看 prompt（调试或管道给其他 LLM）
python3 scripts/daily_digest.py --prompt-only
```

### 参数速查

| 参数 | 说明 | 示例 |
|------|------|------|
| `--days N` | 回溯天数 | `--days 3` |
| `--provider` | LLM 提供商 | `--provider openai` |
| `--model` | 指定模型 | `--model gpt-4.1` |
| `--max-articles N` | 文章上限 | `--max-articles 30` |
| `--dry-run` | 仅采集不调用 AI | `--dry-run` |
| `--prompt-only` | 输出 prompt 到 stdout | `--prompt-only` |
| `--output -` | 结果输出到终端 | `--output -` |

### 智能天数选择

| 场景 | `--days` |
|------|:---:|
| 周一到周五 | `1` |
| 周一（涵盖周末） | `3` |
| 周末低流量 | `2` |
| 本周汇总 | `7` |

### 输出结构

```
daily-reports/
├── index.html              # 归档索引（自动更新）
└── YYYY/
    └── MM/
        ├── YYYY-MM-DD.md   # Markdown 日报
        └── YYYY-MM-DD.html # HTML 日报
```

---

## OPML 管理

编辑 `config/sources.yaml` 后需重新生成 OPML，用于 Folo、Feedly 等 RSS 阅读器：

```bash
python3 scripts/generate_opml.py
# 输出: config/ai-feeds.opml
```

---

## 故障排查

### 采集问题

| 现象 | 可能原因 | 排查步骤 |
|------|------|------|
| `0 articles fetched` | 周末 + 天数太短 | 增加 `--days` 到 3 |
| RSSHub 路由 503 | 反爬/上游网站变更 | 见下方 RSSHub 路由排查 |
| `HTTP 404` from feed | 源网站改了 RSS URL | 用 `curl -sL <site>` 查找 `<link type="application/rss+xml">` |
| `brotli` 解码错误 | httpx 已知问题 | 不影响实际数据采集，可忽略 |
| `parse error` / XML 格式错误 | 上游 feed 不符合规范 | 等待上游修复，或改用 RSSHub 路由 |
| `Connection refused` on localhost:1200 | RSSHub 未启动 | `bash scripts/start-rsshub.sh` |
| SSL 错误 | 临时网络问题 | 重试，脚本已内置 3 次指数退避重试 |

### RSSHub 路由排查

```bash
# 测试单个路由
curl -s --max-time 30 http://localhost:1200/<route-path>

# 查看 RSSHub 日志
tail -50 .rsshub.log

# 查看路由源码
ls RSSHub/lib/routes/<namespace>/

# 常见问题：路由返回 503 + HTML 欢迎页
# → 路由存在但抓取失败，通常是反爬拦截
# → 检查路由源码中的 URL 是否仍有效
```

### AI API 问题

| 现象 | 解决 |
|------|------|
| `ANTHROPIC_API_KEY` 未设置 | `export ANTHROPIC_API_KEY=sk-ant-...` |
| `OPENAI_API_KEY` 未设置 | `export OPENAI_API_KEY=sk-...` |
| API rate limit | 等待后重试，或切换 `--provider` |
| API 调用失败 | 脚本自动降级为原始文章列表 |

---

## 接入统计

| 指标 | 数值 |
|------|:---:|
| 总信息源 | 89 |
| 有 RSS | 62 |
| 原生 RSS（不依赖 RSSHub） | 42 |
| 依赖 RSSHub | 20 |
| 无 RSS | 27 |
| 分类 | 11 |

### 分类明细

| 分类 | 源数 | 有 RSS |
|------|:---:|:---:|
| AI 公司官方博客 | 21 | 13 |
| AI 研究机构 | 6 | 6 |
| AI Engineering / 实战 | 9 | 5 |
| AI 深度专栏 / Newsletter | 8 | 5 |
| AI 资讯聚合 | 10 | 8 |
| 独立研究者 / 开发者 | 8 | 7 |
| 开源 AI / GitHub 趋势 | 2 | 0 |
| 社区 / 实时信号源 | 2 | 2 |
| 中文 AI 信息源 | 5 | 1 |
| AI 社交媒体 | 11 | 11 |
| AI 视频频道 | 7 | 7 |

---

## 添加新信息源

1. 编辑 `config/sources.yaml`，按分类添加条目：

```yaml
- name: Example Blog
  url: https://example.com/blog
  rss: https://example.com/feed.xml      # 或 null 如无 RSS
  type: native                            # native | rsshub | none
  category: ai-companies
  note: 简要说明，可选
```

2. 验证 RSS 可用：

```bash
curl -sL --max-time 10 "https://example.com/feed.xml" | head -c 200
```

3. 重新生成 OPML：

```bash
python3 scripts/generate_opml.py
```

4. 测试采集：

```bash
python3 scripts/daily_digest.py --dry-run --days 1
```

5. 同步更新 `docs/ai-source.md` 参考手册。

---

## 例行维护

- **每周**：运行一次 `--dry-run` 检查 RSS 源健康状态
- **每月**：检查 RSSHub 是否有更新 `cd RSSHub && git pull && pnpm i && pnpm build`
- **源 URL 变更时**：先 `curl -sL <site>` 查找 `<link type="application/rss+xml">`，更新 `sources.yaml` 后重新生成 OPML
- **信息源增删**：同步更新 `docs/ai-source.md` 和 `sources.yaml`
