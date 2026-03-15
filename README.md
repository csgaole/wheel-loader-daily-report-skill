# wheel-loader-daily-report-skill

OpenClaw 的装载机行业情报日报项目与 Skill 封装。

这个仓库包含两部分：

- `loader_intel/`：装载机行业情报采集、分析、Markdown/PDF 报告生成、飞书发送
- `skills/loader-daily-report-skill/`：供 OpenClaw 调用的 Skill 包装层

## 功能概览

- 多源行业资讯采集
- 中文行业站点解析
- 英文 RSS / 新闻源补充
- 自动生成 Markdown 日报
- 自动导出 PDF
- 自动发送 PDF 到飞书
- 支持定时任务运行

## 当前数据源

### 中文
- 中国工程机械工业协会（`cncma.org`）
- 铁甲工程机械网（`cehome.com`）
- 第一工程机械网（`d1cm.com`）

### 英文
- World Construction Network RSS

## 当前报告发送链路

当前唯一正式发送链路为：

```text
collector.py
  -> analyzer.py
  -> reporter.py
       -> 生成 Markdown
       -> 生成 PDF
       -> 复制中文文件名 PDF
       -> 发送到飞书
```

说明：
- `reporter.py` 是唯一正式 PDF 发送实现
- `run.sh report` 与 `run.sh all` 都统一走 `reporter.py`
- `notifier.py` 为兼容入口，不再维护独立 webhook 主链
- `send_pdf_feishu.py` 为弃用兼容入口

## 仓库结构

```text
.
├── loader_intel/
│   ├── config/
│   ├── scripts/
│   ├── data/
│   ├── logs/
│   ├── run.sh
│   └── README.md
└── skills/
    └── loader-daily-report-skill/
        ├── SKILL.md
        ├── scripts/
        └── config/
```

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/csgaole/wheel-loader-daily-report-skill.git
cd wheel-loader-daily-report-skill
```

### 2. 安装依赖

进入项目目录：

```bash
cd loader_intel
pip install -r requirements.txt
```

如果需要生成 PDF，请确保系统安装：

- `pandoc`
- `wkhtmltopdf`（如果当前实现依赖它）

### 3. 配置 OpenClaw / 飞书环境

本项目的 PDF 发送链路依赖 OpenClaw 本机环境与已配置的飞书通道。

如果你只是本地测试报告生成，可先只跑：

```bash
./run.sh collect
./run.sh analyze
./run.sh report
```

### 4. 执行完整流程

```bash
./run.sh all
```

### 5. 查看输出

生成文件通常位于：

```text
~/.openclaw/workspace/reports/loader/
```

包括：

- `YYYY-MM-DD-loader-report.md`
- `YYYY-MM-DD-loader-report.pdf`
- `装载机行业情报日报_YYYY-MM-DD.pdf`

## 在 OpenClaw 中使用 Skill

Skill 位于：

```text
skills/loader-daily-report-skill/
```

核心说明见：

- `skills/loader-daily-report-skill/SKILL.md`
- `loader_intel/README.md`

## 适用场景

- 每日装载机行业情报汇总
- 工程机械企业竞品跟踪
- 电动化 / 无人化 / 智能化装载机动态跟踪
- 飞书日报自动推送

## 维护说明

推荐只修改以下正式入口：

- 采集：`loader_intel/scripts/collector.py`
- 分析：`loader_intel/scripts/analyzer.py`
- 发送：`loader_intel/scripts/reporter.py`
- 统一入口：`loader_intel/run.sh`

运行态文件（如 `data/seen_hashes.json`、raw/analyzed 数据、reports）已通过 `.gitignore` 排除，不应提交到仓库。

## License

MIT
