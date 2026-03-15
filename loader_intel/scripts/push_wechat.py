#!/usr/bin/env python3
"""
推送到微信/飞书 - 纯文本格式（无 Markdown，无链接）
"""

import json
import requests
import re
from pathlib import Path
from datetime import datetime, timedelta

# 飞书配置
FEISHU_APP_ID = "cli_a920a08534781bcd"
FEISHU_APP_SECRET = "CUqvWHifR9U2FgSJXFD4jb5zxyHYA7PW"
FEISHU_USER_ID = "ou_09f88aa1449ac851663dd6f225a95c3d"


def get_tenant_access_token():
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    response = requests.post(url, json=payload, timeout=10)
    result = response.json()
    if result.get("code") == 0:
        return result.get("tenant_access_token")
    else:
        print(f"❌ 获取 token 失败：{result}")
        return None


def push_text_message(text: str, user_id: str) -> bool:
    """发送文本消息"""
    token = get_tenant_access_token()
    if not token:
        return False
    
    url = "https://open.feishu.cn/open-apis/message/v4/send/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "open_id": user_id,
        "msg_type": "text",
        "content": {"text": text}
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    result = response.json()
    
    if result.get("code") == 0:
        print("✅ 推送成功")
        return True
    else:
        print(f"❌ 推送失败：{result}")
        return False


def clean_for_wechat(text: str) -> str:
    """清理为微信纯文本格式"""
    # 删除链接 [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', '', text)
    
    # 删除加粗 **text** -> text
    text = text.replace('**', '')
    
    # 删除标题 # -> 空
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # 删除列表符号 - -> 空
    text = re.sub(r'^-\s*', '', text, flags=re.MULTILINE)
    
    # 删除分隔线 ---
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    
    # 删除斜体 *text* -> text
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    
    # 删除内联代码 `code`
    text = text.replace('`', '')
    
    # 清理多余空行（保留最多 1 个空行）
    lines = text.split('\n')
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        is_empty = line.strip() == ''
        if is_empty and prev_empty:
            continue
        cleaned_lines.append(line)
        prev_empty = is_empty
    
    return '\n'.join(cleaned_lines)


def push_full_report(report_path: Path, user_id: str) -> bool:
    """推送完整版报告（纯文本，分段发送）"""
    with open(report_path, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    # 清理为纯文本
    clean_content = clean_for_wechat(report_content)
    
    # 微信/飞书消息限制约 4000 字，分段发送
    MAX_LENGTH = 3800
    segments = []
    
    current_segment = ""
    for line in clean_content.split('\n'):
        if len(current_segment) + len(line) + 1 > MAX_LENGTH:
            if current_segment:
                segments.append(current_segment)
            current_segment = line + '\n'
        else:
            current_segment += line + '\n'
    
    if current_segment:
        segments.append(current_segment)
    
    print(f"📊 报告总字数：{len(clean_content)}")
    print(f"📊 分段数：{len(segments)}")
    
    # 分段推送
    for i, segment in enumerate(segments, 1):
        if len(segments) > 1:
            header = f"【装载机行业情报日报】({i}/{len(segments)})\n\n"
        else:
            header = "【装载机行业情报日报】\n\n"
        
        text = header + segment
        print(f"📤 推送第 {i} 段...")
        
        if not push_text_message(text, user_id):
            print(f"❌ 第 {i} 段推送失败")
            return False
        
        if i < len(segments):
            import time
            time.sleep(0.5)
    
    return True


def main():
    """主函数"""
    # 查找最新报告
    report_dir = Path("/home/legao/.openclaw/workspace/reports/loader")
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    report_path = report_dir / f"{today}-loader-report.md"
    if not report_path.exists():
        report_path = report_dir / f"{yesterday}-loader-report.md"
    
    if not report_path.exists():
        print(f"❌ 报告不存在")
        return False
    
    print(f"📄 找到报告：{report_path}")
    print(f"📤 推送到：{FEISHU_USER_ID}")
    
    # 推送纯文本版
    success = push_full_report(report_path, FEISHU_USER_ID)
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
