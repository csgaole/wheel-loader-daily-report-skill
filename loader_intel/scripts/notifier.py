#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兼容入口：飞书推送逻辑已统一收敛到 reporter.py。

保留本文件是为了避免旧脚本/旧命令调用时报错，
但实际发送链路不再使用 webhook，而是由 reporter.py
在生成 PDF 后直接通过 OpenClaw 的 Feishu 媒体发送能力完成投递。
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from reporter import ReportGenerator


def main():
    print("ℹ️  notifier.py 已弃用，现统一转交 reporter.py 生成并发送 PDF 到飞书。")
    generator = ReportGenerator()
    generator.generate_report()
    print("✅ 已通过 reporter.py 完成报告生成与 PDF 飞书发送")
    return 0


if __name__ == "__main__":
    sys.exit(main())
