#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第一工程机械网 (d1cm.com) 新闻爬虫解析器
网站：https://www.d1cm.com
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
    print("请运行：pip install -r requirements.txt")
    raise

logger = logging.getLogger(__name__)


class D1CMParser:
    """第一工程机械网解析器"""
    
    def __init__(self):
        self.base_url = "https://www.d1cm.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False
        
        # 装载机相关栏目
        self.category_urls = [
            "https://www.d1cm.com/news/",  # 新闻中心
        ]
        
        # 工程机械大关键词（先宽泛采集，后续再过滤）
        self.keywords = ['装载机', '电动装载机', '无人装载机', '铲车', '工程机械', '挖掘机', '高机', '英轩', '潍柴', '电池']
    
    def _fetch_page(self, url: str, timeout: int = 10) -> Optional[str]:
        try:
            response = self.session.get(url, timeout=timeout, verify=False)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except Exception as e:
            logger.warning(f"获取网页失败 {url}: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        patterns = [
            (r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', '%Y-%m-%d %H:%M'),
            (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),
        ]
        for pattern, fmt in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    return datetime.strptime(match.group(1), fmt)
                except ValueError:
                    continue
        return None
    
    def _fetch_detail_summary(self, link: str, timeout: int = 5) -> Optional[str]:
        """抓取详情页生成更丰富的摘要"""
        try:
            response = self.session.get(link, timeout=timeout, verify=False)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 查找正文内容（D1CM 通常使用 .news_content 或 .content）
            content_div = soup.select_one('.news_content') or soup.select_one('.content') or soup.select_one('article')
            
            if content_div:
                # 提取前 2-3 段
                paragraphs = content_div.select('p')[:3]
                if paragraphs:
                    text_parts = []
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if len(text) > 20:  # 跳过太短的行
                            text_parts.append(text)
                    
                    if text_parts:
                        # 组合前 2 段，限制长度
                        summary = ' '.join(text_parts[:2])[:200]
                        # 清理多余空格
                        summary = ' '.join(summary.split())
                        return summary
            
            return None
        except Exception as e:
            logger.debug(f"抓取详情页失败 {link}: {e}")
            return None
    
    def _matches_keywords(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.keywords)
    
    def parse_news_list(self, url: str, max_items: int = 30) -> List[Dict]:
        """解析新闻列表页"""
        news_items = []
        
        logger.info(f"采集列表页：{url}")
        html = self._fetch_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        news_containers = soup.select('dl.newslistDiv')
        
        for dl in news_containers[:max_items]:
            try:
                # 提取标题
                a = dl.select_one('a')
                if not a:
                    continue
                
                # 清理标题：只取主标题，去除所有多余信息
                raw_title = a.get_text(strip=True)
                import re
                
                # 策略：多层次清洗，优先保留主标题
                title = raw_title
                
                # 1. 按"【"分割（系列报道标记，优先处理）
                if '【' in title:
                    title = title.split('【')[0]
                
                # 2. 按 D1CM 特有分隔符分割（竖线）
                for separator in ['丨', '|']:
                    if separator in title:
                        title = title.split(separator)[0]
                        break
                
                # 3. 移除正文片段：查找"哲学 2025 年"、"革命 2025 年"等模式（名词 + 时间）
                # 常见模式："...哲学 2025 年 12 月" -> 删除时间及其后内容
                title = re.sub(r'([^\s\d])\s*\d{4}年\d{2}月.*$', r'\1', title)
                title = re.sub(r'([^\s\d])\s*\d{4}-\d{2}-\d{2}.*$', r'\1', title)
                
                # 4. 移除时间格式（多种格式）
                title = re.sub(r'\d{4}年\d{2}月\d{2}日\s*\d{2}?:?\d{2}?.*$', '', title)
                title = re.sub(r'\d{4}-\d{2}-\d{2}\s*\d{2}?:?\d{2}?.*$', '', title)
                
                # 5. 移除"来源/初审/复审/终审/编辑/关键词"等元数据
                title = re.sub(r'\s*(来源 | 初审 | 复审 | 终审 | 编辑 | 关键词)[:：]\s*\S+', '', title)
                
                # 6. 按换行分割
                title = title.split('\n')[0]
                
                # 7. 如果标题过长，在合适位置截断
                if len(title) > 45:
                    # 找第一个问号/感叹号（优先保留问句）
                    for mark in ['?', '!', '?', '!']:
                        if mark in title:
                            idx = title.index(mark)
                            title = title[:idx+1]
                            break
                    else:
                        # 没有问叹号就找句号
                        if '.' in title:
                            title = title.split('.')[0]
                        # 还是没有就直接截断
                        elif len(title) > 45:
                            title = title[:45]
                
                title = title.strip()
                # 清理末尾标点
                title = title.rstrip('.,;:,.!?.')
                
                link = a.get('href', '')
                
                if not title or not self._matches_keywords(title):
                    continue
                
                # 处理链接
                if link and not link.startswith('http'):
                    link = self.base_url + link.lstrip('/')
                
                # 提取时间和关键词（从 span）
                spans = dl.select('span')
                published = None
                keywords = []
                
                if spans:
                    # 第一个 span 通常是时间
                    time_text = spans[0].get_text(strip=True)
                    published = self._parse_date(time_text)
                    # 后续 span 是关键词
                    keywords = [s.get_text(strip=True) for s in spans[1:4] if s.get_text(strip=True)]
                
                # 生成自然语言摘要（增强版）
                summary = None
                
                # 1. 优先尝试抓取详情页获取丰富摘要
                if link:
                    summary = self._fetch_detail_summary(link)
                
                # 2. 如果详情页抓取失败，使用关键词生成摘要
                if not summary and keywords:
                    kw_text = "、".join(keywords[:3])
                    # 尝试从标题提取更多信息
                    title_context = ""
                    if "电动" in title or "新能源" in title:
                        title_context = "，聚焦电动化技术发展趋势"
                    elif "无人" in title or "智能" in title:
                        title_context = "，探讨智能化/无人化应用方向"
                    elif "销量" in title or "市场" in title:
                        title_context = "，反映市场动态与行业格局"
                    elif "发布" in title or "新品" in title:
                        title_context = "，介绍最新产品与技术突破"
                    elif "合作" in title or "签约" in title:
                        title_context = "，报道企业战略合作动态"
                    
                    summary = f"文章围绕{kw_text}展开{title_context}，反映行业相关动态"
                
                if not summary:
                    summary = "详情点击链接查看"
                
                news_items.append({
                    'title': title,
                    'source': '第一工程机械网',
                    'published': published or datetime.now(),
                    'summary': summary[:140],
                    'link': link,
                    'category': '行业动态',
                })
                
            except Exception as e:
                logger.debug(f"解析条目失败：{e}")
        
        logger.info(f"D1CM 采集完成：{len(news_items)} 条")
        return news_items
    
    def collect(self, max_items: int = 30) -> List[Dict]:
        all_news = []
        for url in self.category_urls:
            items = self.parse_news_list(url, max_items)
            all_news.extend(items)
            if len(all_news) >= max_items:
                break
        
        # 去重
        seen = set()
        unique = []
        for item in all_news:
            if item['title'] not in seen:
                seen.add(item['title'])
                unique.append(item)
        
        return unique[:max_items]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = D1CMParser()
    news = parser.collect(max_items=15)
    print(f"\n采集到 {len(news)} 条新闻:")
    for item in news[:5]:
        print(f"  - {item['title'][:50]}... ({item['published']})")
