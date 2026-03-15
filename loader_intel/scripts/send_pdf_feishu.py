#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兼容入口：send_pdf_feishu.py 已弃用。

历史上这里维护过一套独立的飞书直连发送逻辑，容易与 reporter.py
中的已验证发送链重复、分叉。现在统一保留 reporter.py 作为唯一发送实现。

用法保持兼容：
    python3 send_pdf_feishu.py <pdf路径>

当前行为：
- 校验 PDF 是否存在
- 提示该脚本已弃用
- 返回成功，不再单独维护第二套飞书发送代码
"""

import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("用法：send_pdf_feishu.py <pdf 文件路径>")
        return 1

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"❌ 文件不存在：{pdf_path}")
        return 1

    print("ℹ️  send_pdf_feishu.py 已弃用。")
    print("ℹ️  当前唯一维护的飞书 PDF 发送链路是 reporter.py。")
    print(f"ℹ️  已校验 PDF 存在：{pdf_path}")
    print("✅ 未执行独立发送；请使用 python3 scripts/reporter.py 或 ./run.sh report")
    return 0


if __name__ == "__main__":
    sys.exit(main())
