#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国工程机械工业协会 (cncma.org) 新闻爬虫解析器
网站：http://www.cncma.org
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("缺少依赖：requests, beautifulsoup4")
    raise

logger = logging.getLogger(__name__)


class CCEMAParser:
    """中国工程机械工业协会解析器（实际抓取 cncma.org）"""

    def __init__(self):
        self.base_url = "http://www.cncma.org"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.category_urls = [
            "http://www.cncma.org/col/shicdt",
            "http://www.cncma.org/col/hangyxw",
            "http://www.cncma.org/col/zuixtz",
            "http://www.cncma.org/col/xiehhd",
        ]
        self.keywords = [
            '装载机', '轮式装载机', '铲车', '电动', '无人', '智能', '销量', '快报', '市场指数',
            '工程机械', '非道路', '出口', '标准', '景气度', '徐工', '柳工', '临工', '三一', '山工'
        ]

    def _fetch_page(self, url: str, timeout: int = 12) -> Optional[str]:
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except Exception as e:
            logger.warning(f"获取网页失败 {url}: {e}")
            return None

    def _parse_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        patterns = [
            (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),
            (r'(\d{4}/\d{2}/\d{2})', '%Y/%m/%d'),
            (r'(\d{4}年\d{1,2}月\d{1,2}日)', '%Y年%m月%d日'),
        ]
        for pattern, fmt in patterns:
            m = re.search(pattern, text)
            if m:
                try:
                    return datetime.strptime(m.group(1), fmt)
                except ValueError:
                    pass
        if '昨天' in text:
            return datetime.now() - timedelta(days=1)
        if '今天' in text:
            return datetime.now()
        return None

    def _matches_keywords(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.keywords)

    def _normalize_link(self, href: str) -> str:
        if href.startswith('http'):
            return href
        if href.startswith('/'):
            return self.base_url + href
        return self.base_url + '/' + href.lstrip('/')

    def parse_news_list(self, url: str, max_items: int = 30) -> List[Dict]:
        html = self._fetch_page(url)
        if not html:
            return []
        soup = BeautifulSoup(html, 'lxml')
        news_items = []
        seen_links = set()

        for a in soup.find_all('a', href=True):
            title = ' '.join(a.get_text(' ', strip=True).split())
            href = a['href'].strip()
            if not title or len(title) < 6 or len(title) > 120:
                continue
            if 'article/' not in href and not re.search(r'/article/\d+', href):
                continue
            if href in seen_links:
                continue
            seen_links.add(href)
            if not self._matches_keywords(title):
                continue
            link = self._normalize_link(href)
            parent = a.find_parent(['li', 'div', 'dd', 'dl'])
            context = ' '.join(parent.get_text(' ', strip=True).split()) if parent else title
            published = self._parse_date(context) or datetime.now()
            summary = context.replace(title, '').strip()[:140] or '详情点击链接查看'
            news_items.append({
                'title': title,
                'source': '中国工程机械工业协会',
                'published': published,
                'summary': summary,
                'link': link,
                'category': '行业动态'
            })
            if len(news_items) >= max_items:
                break

        logger.info(f"CNCMA 采集完成：{len(news_items)} 条 ({url})")
        return news_items

    def collect(self, max_items: int = 20) -> List[Dict]:
        logger.info("开始采集中国工程机械工业协会（cncma.org）...")
        all_news = []
        seen_titles = set()
        for category_url in self.category_urls:
            for item in self.parse_news_list(category_url, max_items=max_items):
                if item['title'] in seen_titles:
                    continue
                seen_titles.add(item['title'])
                all_news.append(item)
                if len(all_news) >= max_items:
                    return all_news
        logger.info(f"中国工程机械工业协会采集完成：{len(all_news)} 条新闻")
        return all_news


def main():
    logging.basicConfig(level=logging.INFO)
    parser = CCEMAParser()
    news = parser.collect(max_items=10)
    print(f"\n采集到 {len(news)} 条新闻:")
    for item in news[:5]:
        print(f"  - {item['title']} ({item['source']})")


if __name__ == "__main__":
    main()
