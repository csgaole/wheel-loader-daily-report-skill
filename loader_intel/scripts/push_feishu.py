#!/usr/bin/env python3
"""
推送到飞书 - 将装载机日报推送到飞书群
"""

import json
import requests
from pathlib import Path
from datetime import datetime

# 飞书配置
FEISHU_APP_ID = "cli_a920a08534781bcd"
FEISHU_APP_SECRET = "CUqvWHifR9U2FgSJXFD4jb5zxyHYA7PW"

# 需要配置：飞书群 webhook 或 机器人
# 方式 1: 群机器人 webhook（推荐，简单）
FEISHU_WEBHOOK = ""  # 在此填入飞书群机器人 webhook URL

# 方式 2: 使用飞书 API 发送（需要 tenant_access_token）
# 需要额外配置：接收消息的用户 ID 或 群聊 ID


def get_tenant_access_token():
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    response = requests.post(url, json=payload)
    result = response.json()
    if result.get("code") == 0:
        return result.get("tenant_access_token")
    else:
        print(f"获取 token 失败：{result}")
        return None


def push_by_webhook(report_path: str, webhook_url: str) -> bool:
    """通过群机器人 webhook 推送"""
    with open(report_path, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    # 截取前 2000 字（飞书消息长度限制）
    if len(report_content) > 2000:
        preview = report_content[:2000] + "\n\n...（内容过长，请查看完整报告）"
    else:
        preview = report_content
    
    payload = {
        "msg_type": "text",
        "content": {
            "text": f"🚜 装载机行业情报日报\n\n{preview}"
        }
    }
    
    response = requests.post(webhook_url, json=payload)
    result = response.json()
    
    if result.get("code") == 0 or result.get("StatusCode") == 0:
        print("✅ 推送成功")
        return True
    else:
        print(f"❌ 推送失败：{result}")
        return False


def push_by_api(report_path: str, chat_id: str, is_group: bool = True) -> bool:
    """通过飞书 API 推送消息"""
    token = get_tenant_access_token()
    if not token:
        return False
    
    with open(report_path, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    # 构建富文本消息
    content = {
        "text": f"🚜 装载机行业情报日报\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{report_content[:3000]}"
    }
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps(content)
    }
    
    if is_group:
        payload["receive_id"] = chat_id
    else:
        payload["receive_id"] = chat_id
    
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    
    if result.get("code") == 0:
        print("✅ 推送成功")
        return True
    else:
        print(f"❌ 推送失败：{result}")
        return False


def main():
    """主函数"""
    # 查找最新报告
    report_dir = Path("/home/legao/.openclaw/workspace/reports/loader")
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = report_dir / f"{today}-loader-report.md"
    
    if not report_path.exists():
        print(f"❌ 报告不存在：{report_path}")
        return False
    
    print(f"📄 找到报告：{report_path}")
    
    # 优先使用 webhook 方式
    if FEISHU_WEBHOOK:
        print("📤 通过 webhook 推送...")
        return push_by_webhook(str(report_path), FEISHU_WEBHOOK)
    else:
        print("⚠️  未配置 webhook URL")
        print("请在脚本中配置 FEISHU_WEBHOOK，或使用飞书 API 方式")
        
        # 或者使用 API 方式（需要配置 chat_id）
        # chat_id = "oc_XXX"  # 飞书群聊 ID 或 用户 ID
        # return push_by_api(str(report_path), chat_id, is_group=True)
    
    return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
