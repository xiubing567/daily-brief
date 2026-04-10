# 📰 daily-brief

> **每日科技/科学/AI 新闻日报** — 自动采集全球重要科技与科学新闻，每天北京时间 09:00 生成中英双语日报并发送到邮箱。
>
> **Daily Tech/Science/AI Brief** — Auto-aggregates global top tech & science news, generates a bilingual (EN/ZH) digest, and emails it every day at 09:00 Beijing time.

---

## ✨ 功能 / Features

| 功能 | 说明 |
|------|------|
| 📡 多源 RSS 采集 | 40+ 高质量来源（Nature, Science, MIT Tech Review, arXiv, NASA, IEEE…）|
| 🔀 重要性排序 | 综合来源权重、类目、关键词、新鲜度打分 |
| 🌐 中英双语 | 标题 + 摘要全部中英双语（可选接入 OpenAI 提升质量）|
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

## 📡 扩展来源与类别

编辑 `config/sources.yml`，按以下格式新增条目：

```yaml
- name: "My Favorite Blog"
  url: "https://example.com/feed.xml"   # RSS feed URL
  category: "AI"                         # 类别（见下表）
  weight: 8                              # 权重 1-10，越高越容易上榜
  enabled: true                          # false 则跳过该来源
```

### 支持的类别 / Supported categories

| 英文 key | 中文显示 |
|----------|----------|
| `AI` | 人工智能 |
| `Robotics` | 机器人 |
| `Space` | 航空航天 |
| `Science` | 基础科学 |
| `Physics` | 物理学 |
| `Biology` | 生命科学 |
| `Medicine` | 医疗健康 |
| `Chemistry` | 化学 |
| `Psychology` | 心理学 |
| `Social Sciences` | 社会科学 |
| `InfoEng` | 信息工程 |
| `Technology` | 科技 |

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
│   ├── sources.yml            # RSS 源列表（来源/类目/权重）
│   └── subscribers.json       # 订阅者邮箱列表
├── scripts/
│   ├── main.py                # 主入口，串联全流程
│   ├── fetch_news.py          # 抓取 RSS + 去重过滤
│   ├── rank.py                # 重要性打分与排序
│   ├── translate.py           # 中英双语翻译与摘要
│   ├── render_report.py       # 生成 HTML + Markdown 报告
│   └── send_email.py          # Gmail SMTP 发信
├── reports/                   # 生成的报告（本地 & CI Artifacts）
├── requirements.txt
└── README.md
```

---

## 📋 命令行参数 / CLI options

```
python scripts/main.py [options]

  --top-n N             每日日报条数（默认 20）
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