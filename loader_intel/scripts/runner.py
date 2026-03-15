#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一执行入口：采集→分析→报告→飞书推送。"""

import logging
import sys
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent
LOG_DIR = BASE / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

from collector import NewsCollector
from analyzer import NewsAnalyzer
from reporter import ReportGenerator
from notifier import FeishuNotifier


def main():
    logger.info('开始执行装载机行业日报流水线')
    collector = NewsCollector()
    news = collector.collect_all()
    analyzer = NewsAnalyzer()
    analyzed = analyzer.analyze(news)
    generator = ReportGenerator()
    generator.generate_report()
    report_path = str(generator.output_dir / f"{datetime.now().strftime('%Y-%m-%d')}-loader-report.md")
    summary = generator.get_summary()
    notifier = FeishuNotifier()
    pushed = notifier.send(summary, report_path) if notifier.webhook_url else False
    logger.info('执行完成：news=%s analyzed=%s pushed=%s', len(news), len(analyzed), pushed)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
