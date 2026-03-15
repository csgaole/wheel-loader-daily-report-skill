---
name: loader-intel-daily-report
description: 装载机行业情报日报生成与推送 Skill。支持生成 Markdown/PDF 报告并推送到飞书。
---

# loader-intel-daily-report

装载机行业情报日报自动化 Skill，集成数据采集、分析、报告生成和飞书推送功能。

## 功能

- **生成日报** - 自动采集装载机行业新闻并生成报告
- **PDF 导出** - 将 Markdown 报告转换为 PDF 格式
- **飞书推送** - 自动发送报告到飞书机器人
- **定时任务** - 支持每日自动执行

## 使用

```bash
# 生成今日日报
loader-daily-report generate

# 生成指定日期日报
loader-daily-report generate --date 2026-03-11

# 生成并发送 PDF 到飞书
loader-daily-report generate --pdf --send

# 查看配置
loader-daily-report config

# 配置飞书推送
loader-daily-report config --feishu-webhook "https://..."
```

## 报告输出

- Markdown: `~/.openclaw/workspace/reports/loader/YYYY-MM-DD-loader-report.md`
- PDF: `~/.openclaw/workspace/reports/loader/YYYY-MM-DD-loader-report.pdf`
- 飞书实际发送文件：`~/.openclaw/workspace/reports/loader/装载机行业情报日报_YYYY-MM-DD.pdf`

## 当前发送链路（重要）

当前系统的**唯一正式飞书发送实现**是 `loader_intel/scripts/reporter.py`：

```text
collector.py -> analyzer.py -> reporter.py
                                  -> 生成 Markdown/PDF
                                  -> 复制中文文件名 PDF
                                  -> 直接发送到飞书
```

说明：
- `./run.sh report` 与 `./run.sh all` 都统一走 `reporter.py`
- `notifier.py` 现为兼容入口，内部会转交 `reporter.py`
- `send_pdf_feishu.py` 现为弃用兼容入口，不再维护第二套独立发送逻辑
- 因此，后续若要修改飞书 PDF 发送行为，请优先修改 `reporter.py`

## 依赖

- Python 3.10+
- pandoc (PDF 生成)
- wkhtmltopdf (PDF 生成)

## 文件结构

```
loader-daily-report-skill/
├── SKILL.md
├── scripts/
│   └── loader-daily-report      # 主脚本
└── config/
    └── feishu.yaml              # 飞书配置
```
