#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
铁甲工程机械网 (cehome.com) 新闻爬虫解析器
网站：https://www.cehome.com
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("缺少依赖：requests, beautifulsoup4")
    raise

logger = logging.getLogger(__name__)


class CEHomeParser:
    """铁甲工程机械网解析器"""

    def __init__(self):
        self.base_url = "https://www.cehome.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False
        self.category_urls = [
            "https://www.cehome.com/news/",
            "https://www.cehome.com/news/qiye/",
            "https://www.cehome.com/news/hangye/",
            "https://www.cehome.com/news/xinpin/",
        ]
        self.keywords = [
            '装载机', '轮式装载机', '电动装载机', '滑移装载机', '铲车', '工程机械',
            '英轩', '柳工', '徐工', '三一', '临工', '山工', '卡特', '小松', '沃尔沃'
        ]

    def _fetch_page(self, url: str, timeout: int = 12) -> Optional[str]:
        try:
            response = self.session.get(url, timeout=timeout, verify=False)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except Exception as e:
            logger.warning(f"获取网页失败 {url}: {e}")
            return None

    def _parse_date_from_url(self, url: str) -> Optional[datetime]:
        m = re.search(r'/news/(\d{4})(\d{2})(\d{2})/', url)
        if m:
            try:
                return datetime.strptime(''.join(m.groups()), '%Y%m%d')
            except ValueError:
                return None
        return None

    def _matches_keywords(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.keywords)

    def _fetch_detail_summary(self, link: str, timeout: int = 6) -> Optional[str]:
        try:
            html = self._fetch_page(link, timeout=timeout)
            if not html:
                return None
            soup = BeautifulSoup(html, 'lxml')
            content = soup.select_one('.article-content') or soup.select_one('.newsContent') or soup.select_one('.content') or soup.select_one('article')
            if not content:
                return None
            paragraphs = []
            for p in content.select('p')[:5]:
                text = ' '.join(p.get_text(' ', strip=True).split())
                if len(text) >= 20:
                    paragraphs.append(text)
            if paragraphs:
                return ' '.join(paragraphs[:2])[:200]
            text = ' '.join(content.get_text(' ', strip=True).split())
            return text[:200] if len(text) > 20 else None
        except Exception as e:
            logger.debug(f"抓取详情页失败 {link}: {e}")
            return None

    def parse_news_list(self, url: str, max_items: int = 30) -> List[Dict]:
        html = self._fetch_page(url)
        if not html:
            return []
        soup = BeautifulSoup(html, 'lxml')
        items = []
        seen_links = set()

        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            title = ' '.join(a.get_text(' ', strip=True).split())
            if not href or not title:
                continue
            if '/news/' not in href or not href.endswith('.shtml'):
                continue
            if href in seen_links:
                continue
            seen_links.add(href)

            if href.startswith('/'):
                link = self.base_url + href
            elif href.startswith('http'):
                link = href
            else:
                link = self.base_url + '/' + href.lstrip('/')

            title = re.sub(r'^【[^】]+】', '', title).strip()
            if len(title) < 6 or len(title) > 80:
                continue
            if not self._matches_keywords(title):
                continue

            published = self._parse_date_from_url(link) or datetime.now()
            summary = self._fetch_detail_summary(link) or '详情点击链接查看'
            items.append({
                'title': title,
                'source': '铁甲工程机械网',
                'published': published,
                'summary': summary[:140],
                'link': link,
                'category': '行业动态',
            })
            if len(items) >= max_items:
                break

        logger.info(f"CEHome 采集完成：{len(items)} 条")
        return items

    def collect(self, max_items: int = 20) -> List[Dict]:
        all_news = []
        seen_titles = set()
        for url in self.category_urls:
            for item in self.parse_news_list(url, max_items=max_items):
                if item['title'] in seen_titles:
                    continue
                seen_titles.add(item['title'])
                all_news.append(item)
                if len(all_news) >= max_items:
                    return all_news
        return all_news


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    parser = CEHomeParser()
    news = parser.collect(10)
    print(f'采集到 {len(news)} 条新闻')
    for item in news[:5]:
        print(f"- {item['title']} ({item['link']})")
