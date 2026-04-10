# 📰 daily-brief

> **每日科技/科学/AI 新闻日报** — 自动采集全球重要科技与科学新闻，每天北京时间 09:00 生成中英双语日报并发送到邮箱。
>
> **Daily Tech/Science/AI Brief** — Auto-aggregates global top tech & science news, generates a bilingual (EN/ZH) digest grouped by category, and emails it every day at 09:00 Beijing time.

---

## ✨ 功能 / Features

| 功能 | 说明 |
|------|------|
| 📡 多源 RSS 采集 | 60+ 来源：新闻门户、Reddit 论坛、YouTube 频道、学术期刊、arXiv 论文 |
| 🔀 新闻优先排序 | 来源类型权重：新闻 > 论坛 > 视频 > 博客 > 论文，避免论文霸榜 |
| 🗂️ 类目配额选取 | 核心类目（AI/科技/科学/医学/航天/机器人）各取 2 条，其余各取 1 条，补齐至 30 条 |
| 🌐 中英双语 | 标题 + 摘要全部中英双语（可选接入 OpenAI 提升质量）|
| 📊 类目分组展示 | 邮件/报告按类目分 section 展示，附类型标签（新闻/论坛/视频/博客/论文）|
| 📧 邮件发送 | Gmail SMTP 群发，支持多收件人订阅者列表 |
| 🗂️ 归档 | 每次运行同时保存 HTML + Markdown 报告（GitHub Actions Artifacts）|
| ⏰ 定时执行 | GitHub Actions cron，北京时间每天 09:00 自动触发 |
| 🖱️ 手动触发 | 支持 `workflow_dispatch`，可随时手动运行 |

---

## 🚀 快速开始 / Quick Start

### 本地运行 / Run locally

```bash
# 1. Clone & install
git clone https://github.com/xiubing567/daily-brief.git
cd daily-brief
pip install -r requirements.txt

# 2. (可选) 设置环境变量 / (Optional) Set env vars
export GMAIL_USERNAME="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
export OPENAI_API_KEY="sk-..."   # optional, enables better translation

# 3. 试运行（不发邮件）/ Dry run (no email)
python scripts/main.py --dry-run

# 4. 正式运行（发邮件）/ Full run (send email)
python scripts/main.py
```

生成的报告保存在 `reports/YYYY-MM-DD.{html,md}`。

---

## 🔑 配置 GitHub Secrets

进入仓库 **Settings → Secrets and variables → Actions → New repository secret**，添加：

| Secret 名称 | 说明 |
|-------------|------|
| `GMAIL_USERNAME` | 发件人 Gmail 地址，例如 `you@gmail.com` |
| `GMAIL_APP_PASSWORD` | Gmail [应用专用密码](https://myaccount.google.com/apppasswords)（需开启 2FA）|
| `OPENAI_API_KEY` | （可选）OpenAI API Key，启用后使用 GPT-4o-mini 翻译和摘要，质量更高 |

> ⚠️ **不要**把密码/密钥直接写进代码或 YAML 文件！务必通过 Secrets 传入。

---

## 👥 添加 / 移除订阅者

编辑 `config/subscribers.json`：

```json
{
  "subscribers": [
    "xiubing1111@gmail.com",
    "another@example.com"
  ]
}
```

直接 Push 即可生效，无需修改任何脚本。

---

## 📡 新闻来源类型 / Source types

`config/sources.yml` 中每个来源包含 `type` 字段，用于"新闻优先"排序：

| type | 说明 | 示例 | 权重 |
|------|------|------|------|
| `news` | 新闻门户/杂志/机构发布 | MIT Tech Review, Nature, NASA, WHO | 最高 |
| `forum` | 论坛/社区讨论 | Reddit (r/science, r/MachineLearning…) | 次高 |
| `video` | 视频讨论 | YouTube (NASA, Kurzgesagt, Veritasium…) | 中等 |
| `blog` | 官方/研究博客 | OpenAI Blog, DeepMind Blog | 中低 |
| `paper` | 学术论文 | arXiv cs.AI, arXiv Physics… | 最低 |

> **论文（arXiv）统一归为 `Papers` 类目**，降低权重，避免霸榜。每次日报中论文通常只占少数席位。

### X / Twitter（可选插件，默认关闭）

X 来源在 `config/sources.yml` 中设有 `enabled: false`。由于 X 官方 API 访问限制，默认不启用。
如需启用，可在 `sources.yml` 中将对应条目的 `enabled` 改为 `true`，前提是有可用的
Nitter RSS 代理实例或其他无需付费 API 的抓取方式。

---

## 🗂️ 类目配额策略 / Category quota strategy

日报不再使用全局 Top-N（容易导致某个类目霸榜），而是采用"类目配额 + 补齐"策略：

| 类别 | 类型 | 每日配额 |
|------|------|--------|
| AI、科技、基础科学、医学、航天、机器人 | 核心类 | 优先各取 **2 条** |
| 物理、化学、生物、心理、社科、信息工程、论文 | 其余类 | 优先各取 **1 条** |
| — | 全局补齐 | 不足 30 条时用高分文章补满 |

逻辑实现在 `scripts/selector.py`，可通过修改 `CORE_QUOTA` / `OTHER_QUOTA` / `DEFAULT_TOTAL` 调整。

---

## 📡 扩展来源与类别

编辑 `config/sources.yml`，按以下格式新增条目：

```yaml
- name: "My Favorite Blog"
  url: "https://example.com/feed.xml"   # RSS feed URL
  category: "AI"                         # 类别（见下表）
  weight: 8                              # 权重 1-10，越高越容易上榜
  type: "news"                           # 来源类型：news/forum/video/blog/paper
  enabled: true                          # false 则跳过该来源
```

### 支持的类别 / Supported categories

| 英文 key | 中文显示 | 说明 |
|----------|----------|------|
| `AI` | 人工智能 | 核心类 |
| `Robotics` | 机器人 | 核心类 |
| `Space` | 航空航天 | 核心类 |
| `Science` | 基础科学 | 核心类 |
| `Physics` | 物理学 | |
| `Biology` | 生命科学 | |
| `Medicine` | 医疗健康 | 核心类 |
| `Chemistry` | 化学 | |
| `Psychology` | 心理学 | |
| `Social Sciences` | 社会科学 | |
| `InfoEng` | 信息工程 | |
| `Technology` | 科技 | 核心类 |
| `Papers` | 学术论文 | arXiv 等论文专属类目 |

> 如需新增类别，在 `scripts/render_report.py` 的 `CATEGORY_ZH` 字典中添加映射，
> 并在 `scripts/rank.py` 的 `CATEGORY_WEIGHTS` 中添加权重即可。

---

## 🏗️ 项目结构 / Project structure

```
daily-brief/
├── .github/
│   └── workflows/
│       └── daily.yml          # GitHub Actions 定时任务
├── config/
│   ├── sources.yml            # RSS 源列表（来源/类目/权重/类型）
│   └── subscribers.json       # 订阅者邮箱列表
├── scripts/
│   ├── main.py                # 主入口，串联全流程
│   ├── fetch_news.py          # 抓取 RSS + 去重过滤
│   ├── rank.py                # 重要性打分与排序（含来源类型权重）
│   ├── selector.py            # 类目配额选取策略
│   ├── translate.py           # 中英双语翻译与摘要
│   ├── render_report.py       # 生成 HTML + Markdown 报告（按类目分组）
│   └── send_email.py          # Gmail SMTP 发信
├── reports/                   # 生成的报告（本地 & CI Artifacts）
├── requirements.txt
└── README.md
```

---

## 📋 命令行参数 / CLI options

```
python scripts/main.py [options]

  --top-n N             每日日报条数（默认 30）
  --lookback-hours H    抓取最近 H 小时的新闻（默认 36）
  --config PATH         来源配置文件（默认 config/sources.yml）
  --subscribers PATH    订阅者文件（默认 config/subscribers.json）
  --output-dir DIR      报告输出目录（默认 reports）
  --dry-run             只生成报告，不发邮件
```

---

## ❓ 常见问题 / FAQ

**Q: 翻译质量不好？**
A: 设置 `OPENAI_API_KEY` 后，系统会使用 GPT-4o-mini 生成高质量中英摘要，翻译质量显著提升。未设置时使用 Google Translate（免费但质量一般）。

**Q: 某个 RSS 源抓取失败？**
A: 失败的源会被跳过并在日志中打印警告；其他源正常运行，不影响整体流程。

**Q: 如何临时禁用某个来源？**
A: 在 `config/sources.yml` 对应条目中添加 `enabled: false`。

**Q: 邮件发不出去？**
A: 确认已开启 Gmail 两步验证并使用"应用专用密码"，而非账号密码。

**Q: 如何调整类目配额？**
A: 编辑 `scripts/selector.py` 中的 `CORE_QUOTA`、`OTHER_QUOTA`、`DEFAULT_TOTAL` 常量。

**Q: 如何启用 X/Twitter 来源？**
A: 在 `config/sources.yml` 中找到 X 相关条目，将 `enabled: false` 改为 `enabled: true`，并确保 URL 指向一个可用的 Nitter RSS 代理实例。