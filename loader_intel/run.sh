#!/bin/bash
# 装载机行业情报日报系统 - 统一入口脚本
# 用法：./run.sh [collect|analyze|report|notify|all]
#
# 重要说明（2026-03-15 起）：
# - 唯一正式的飞书 PDF 发送链路是 scripts/reporter.py
# - ./run.sh report 与 ./run.sh all 都统一走 reporter.py
# - notifier.py / send_pdf_feishu.py 仅保留兼容入口，不再维护第二套独立发送逻辑
# - 若未来需要修改“生成 PDF 并发送到飞书”的行为，请优先修改 reporter.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/run_$(date +%Y%m%d).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

usage() {
    echo "用法：$0 [command]"
    echo ""
    echo "Commands:"
    echo "  collect   - 采集新闻数据"
    echo "  analyze   - 分析采集的数据"
    echo "  report    - 生成日报"
    echo "  notify    - 占位步骤（已并入 report，统一由 reporter.py 发送 PDF）"
    echo "  all       - 执行完整流程（默认，含 PDF 飞书发送）"
    echo "  test      - 发送测试消息到飞书"
    echo ""
    echo "示例:"
    echo "  $0 all          # 执行完整流程（生成并发送 PDF）"
    echo "  $0 collect      # 只采集"
    echo "  $0 test         # 测试飞书推送"
}

run_collect() {
    log "▶️  开始采集新闻..."
    python3 scripts/collector.py 2>&1 | tee -a "$LOG_FILE"
    log "✅ 采集完成"
}

run_analyze() {
    log "▶️  开始分析新闻..."
    python3 scripts/analyzer.py 2>&1 | tee -a "$LOG_FILE"
    log "✅ 分析完成"
}

run_report() {
    log "▶️  开始生成报告并发送 PDF 到飞书..."
    python3 scripts/reporter.py 2>&1 | tee -a "$LOG_FILE"
    local status=$?
    if [ $status -eq 0 ]; then
        log "✅ 报告生成完成（已走 reporter.py PDF 发送链）"
    else
        log "⚠️  报告生成或 PDF 发送失败"
    fi
}

run_notify() {
    log "ℹ️  已跳过独立 notify 步骤：统一由 reporter.py 生成并发送 PDF"
}

run_test() {
    log "▶️  发送测试消息..."
    python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from scripts.notifier import FeishuNotifier
notifier = FeishuNotifier()
if notifier.webhook_url:
    success = notifier.send_test_message()
    sys.exit(0 if success else 1)
else:
    print('未配置 Webhook URL')
    sys.exit(1)
" 2>&1 | tee -a "$LOG_FILE"
}

run_all() {
    log "=========================================="
    log "🚜 装载机行业情报日报系统"
    log "=========================================="
    log "开始时间：$(date '+%Y-%m-%d %H:%M:%S')"
    log ""
    
    run_collect
    run_analyze
    run_report
    run_notify
    
    log ""
    log "=========================================="
    log "✅ 完整流程执行完成"
    log "结束时间：$(date '+%Y-%m-%d %H:%M:%S')"
    log "=========================================="
    log ""
    log "报告位置：/home/legao/.openclaw/workspace/reports/loader/"
    log "日志位置：$LOG_FILE"
}

# 主逻辑
case "${1:-all}" in
    collect)
        run_collect
        ;;
    analyze)
        run_analyze
        ;;
    report)
        run_report
        ;;
    notify)
        run_notify
        ;;
    all)
        run_all
        ;;
    test)
        run_test
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo "未知命令：$1"
        usage
        exit 1
        ;;
esac
