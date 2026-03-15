# 装载机行业情报日报系统

自动采集、分析、生成装载机行业日报，并将 **PDF 文件直接发送到飞书**。

---

## 当前真实链路（2026-03-15 起）

系统现在统一使用 **一条发送链**：

```text
collector.py
  -> analyzer.py
  -> reporter.py
       -> 生成 Markdown
       -> 生成 PDF
       -> 复制中文文件名 PDF
       -> 通过 OpenClaw 直接发送到飞书
```

### 关键结论
- **唯一正式发送实现：`scripts/reporter.py`**
- `./run.sh report` 和 `./run.sh all` 都走这条链
- 不再依赖 `config/feishu.yaml` 里的 webhook 才能发 PDF

---

## 目录结构

```text
loader_intel/
├── config/                  # 配置文件
│   ├── keywords.yaml        # 搜索关键词配置
│   ├── companies.yaml       # 厂商配置
│   ├── sources.yaml         # 数据源配置（参考）
│   └── feishu.yaml          # 历史 webhook 配置（当前非主发送链）
├── data/                    # 原始/分析后数据
├── logs/                    # 运行日志
├── scripts/
│   ├── collector.py         # 信息采集
│   ├── analyzer.py          # 内容分析
│   ├── reporter.py          # 报告生成 + PDF 发送（唯一正式发送链）
│   ├── notifier.py          # 兼容入口：内部转交 reporter.py
│   ├── send_pdf_feishu.py   # 弃用兼容入口：仅提示，不再独立发送
│   └── parsers/             # 各站点解析器
├── run.sh                   # 统一入口脚本
├── requirements.txt         # Python 依赖
└── README.md
```

---

## 当前数据源

### 中文
- 中国工程机械工业协会：`cncma.org`
- 铁甲工程机械网：`cehome.com`
- 第一工程机械网：`d1cm.com`

### 英文
- World Construction Network RSS

说明：
- 历史上配置里曾出现 `ccema.org.cn`，但那并不是目标工程机械协会站点。
- 现已修正为实际使用 `cncma.org`。

---

## 快速开始

```bash
cd /home/legao/.openclaw/workspace/loader_intel

# 完整流程：采集 -> 分析 -> 生成 -> 发送 PDF 到飞书
./run.sh all

# 只生成并发送 PDF
./run.sh report

# 只采集
./run.sh collect

# 只分析
./run.sh analyze
```

查看报告输出：

```bash
ls -lt /home/legao/.openclaw/workspace/reports/loader/
```

---

## 输出文件

报告默认输出到：

- Markdown：`/home/legao/.openclaw/workspace/reports/loader/YYYY-MM-DD-loader-report.md`
- HTML：`/home/legao/.openclaw/workspace/reports/loader/YYYY-MM-DD-loader-report.html`
- PDF：`/home/legao/.openclaw/workspace/reports/loader/YYYY-MM-DD-loader-report.pdf`
- 中文文件名 PDF：`/home/legao/.openclaw/workspace/reports/loader/装载机行业情报日报_YYYY-MM-DD.pdf`

其中真正发送到飞书的是：

- **中文文件名 PDF**

---

## 关于飞书发送

### 当前主链
`reporter.py` 内部会在生成 PDF 后执行飞书发送。

### 为什么不用 webhook 当主链
历史上存在两套飞书逻辑：

1. `notifier.py`
   - 依赖 `config/feishu.yaml` 中的 webhook
   - 容易出现“报告生成了，但 webhook 没配导致没发出去”

2. `reporter.py`
   - 直接生成 PDF 后发送
   - 已验证可用

为避免分叉和误判，现已统一到 **`reporter.py`**。

---

## 兼容入口说明

### `scripts/notifier.py`
**状态：兼容入口，已弃用原 webhook 主逻辑**

当前行为：
- 不再维护独立发送实现
- 调用后会直接转交 `reporter.py`

用途：
- 避免旧命令/旧脚本调用时报错

### `scripts/send_pdf_feishu.py`
**状态：弃用兼容入口**

当前行为：
- 只校验 PDF 文件是否存在
- 明确提示该脚本已弃用
- 不再维护第二套飞书发送代码

用途：
- 防止历史脚本直接炸掉
- 同时避免再次形成重复发送链

---

## 常见问题

### 1. 为什么 run.sh all 以前看起来“推送成功”但飞书没收到？
因为旧版 `run.sh` 的 `notify` 步骤走的是 `notifier.py`，而它依赖 webhook。若 webhook 未配置，就会跳过发送。

### 2. 现在 run.sh all 发的是哪条链？
现在统一发的是：
- `reporter.py` -> 生成 PDF -> 发送到飞书

### 3. 如果今天重复采集，为什么可能出现 0 条？
因为有去重缓存 `seen_hashes.json`。同一天重复跑采集时，可能被判定为已见内容。

---

## 建议维护原则

以后如果要改飞书发送逻辑，请遵守：

- **只改 `reporter.py` 这一处正式实现**
- 不要再新增第二套独立飞书发送代码
- `notifier.py` / `send_pdf_feishu.py` 仅保留兼容层职责

这样可以避免：
- 配置分裂
- 日志误导
- “生成成功但没发出去”的错觉

---

## 运行日志

日志位置：

```bash
/home/legao/.openclaw/workspace/loader_intel/logs/
```

建议排查顺序：
1. 看 `run.sh` 日志
2. 看 `reporter.py` 是否生成 PDF
3. 看是否出现 `✅ PDF 已发送到飞书`
