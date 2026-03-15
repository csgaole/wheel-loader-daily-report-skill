#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
装载机行业情报采集器
从多个公开来源采集行业新闻和动态
"""

import os
import sys
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import requests
    from bs4 import BeautifulSoup
    import feedparser
except ImportError as e:
    print(f"缺少依赖：{e}")
    print("请运行：pip install -r requirements.txt")
    sys.exit(1)

import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsCollector:
    """新闻采集器"""
    
    def __init__(self, config_dir=None):
        self.base_dir = Path(__file__).parent.parent
        self.config_dir = config_dir or self.base_dir / "config"
        self.data_dir = self.base_dir / "data"
        self.logs_dir = self.base_dir / "logs"
        
        # 确保目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self.keywords_config = self._load_config("keywords.yaml")
        self.companies_config = self._load_config("companies.yaml")
        
        # 去重缓存
        self.seen_hashes = self._load_seen_hashes()
        
        # 采集结果
        self.news_items = []
        
    def _load_config(self, filename):
        """加载 YAML 配置"""
        config_path = self.config_dir / filename
        if not config_path.exists():
            logger.warning(f"配置文件不存在：{config_path}")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_seen_hashes(self):
        """加载已见新闻的哈希缓存"""
        cache_file = self.data_dir / "seen_hashes.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 清理 7 天前的缓存
                cutoff = (datetime.now() - timedelta(days=7)).timestamp()
                return {k: v for k, v in data.items() if v > cutoff}
        return {}
    
    def _save_seen_hashes(self):
        """保存已见新闻哈希缓存"""
        cache_file = self.data_dir / "seen_hashes.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.seen_hashes, f, ensure_ascii=False, indent=2)
    
    def _generate_hash(self, title, source):
        """生成新闻唯一标识"""
        content = f"{title}:{source}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _is_duplicate(self, news_hash):
        """检查是否重复"""
        if news_hash in self.seen_hashes:
            return True
        self.seen_hashes[news_hash] = datetime.now().timestamp()
        return False
    
    def _build_search_queries(self):
        """构建搜索查询"""
        keywords = self.keywords_config.get('search_keywords', {})
        products = keywords.get('products', [])
        technologies = keywords.get('technologies', [])
        english = keywords.get('english', [])
        
        # 组合查询
        queries = []
        
        # 产品 + 技术组合
        for tech in technologies[:5]:  # 限制数量
            queries.append(tech)
        
        # 英文关键词
        for eng in english[:5]:
            queries.append(eng)
        
        # 厂商相关
        companies = self.companies_config.get('companies', {})
        for company in companies.get('domestic', [])[:5]:
            queries.append(f"{company['name']} 装载机")
        
        for company in companies.get('international', [])[:5]:
            queries.append(f"{company['aliases'][0]} 装载机")
        
        return list(set(queries))
    
    def _build_google_news_urls(self) -> list:
        """构建 Google News RSS 查询 URL"""
        urls = []

        zh_queries = [
            '装载机 工程机械',
            '电动装载机',
            '无人装载机',
            '智能装载机',
            '轮式装载机',
            '装载机 销量',
            '装载机 新品',
            '三一 装载机',
            '徐工 装载机',
            '柳工 装载机',
            '卡特彼勒 装载机',
            '沃尔沃 装载机',
            '临工 装载机',
            '山工 装载机',
        ]
        for query in zh_queries:
            encoded = requests.utils.quote(f'"{query}"')
            url = f"https://news.google.com/rss/search?q={encoded}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
            urls.append(('Google News ZH', url, 'zh'))

        en_queries = [
            'wheel loader',
            'electric wheel loader',
            'autonomous wheel loader',
            'wheel loader news',
            'construction equipment loader',
            'Volvo wheel loader',
            'Caterpillar wheel loader',
            'Komatsu wheel loader',
            'Liugong wheel loader',
            'XCMG loader',
            'SANY wheel loader',
            'SDLG wheel loader',
            'CASE wheel loader',
            'JCB wheel loader',
            'DEVELON wheel loader',
            'Hitachi wheel loader',
        ]
        for query in en_queries:
            encoded = requests.utils.quote(f'"{query}"')
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
            urls.append(('Google News EN', url, 'en'))

        site_queries = [
            ('Industry Site', '"wheel loader" site:constructionequipment.com'),
            ('Industry Site', '"wheel loader" site:equipmentworld.com'),
            ('Industry Site', '"wheel loader" site:forconstructionpros.com'),
            ('Industry Site', '"wheel loader" site:heavyequipmentguide.ca'),
            ('Industry Site', '"wheel loader" site:worldconstructionnetwork.com'),
            ('OEM Site', '"wheel loader" site:volvoce.com'),
            ('OEM Site', '"wheel loader" site:liugong.com'),
            ('OEM Site', '"wheel loader" site:sanyglobal.com'),
            ('OEM Site', '"wheel loader" site:xcmg.com'),
            ('OEM Site', '"wheel loader" site:develon-ce.com'),
            ('OEM Site', '"wheel loader" site:hitachicm.com'),
        ]
        for source_name, query in site_queries:
            encoded = requests.utils.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
            urls.append((source_name, url, 'en'))

        return urls

    def _build_direct_rss_urls(self) -> list:
        """构建可直接抓取的行业媒体 RSS 源。"""
        return [
            ('World Construction Network', 'https://www.worldconstructionnetwork.com/feed/', 'en'),
            ('Equipment Journal', 'https://www.equipmentjournal.com/feed/', 'en'),
            ('International Mining', 'https://im-mining.com/feed/', 'en'),
            ('Industrial Vehicle Technology International', 'https://www.ivtinternational.com/feed', 'en'),
        ]

    def _parse_google_news_entry(self, entry, source_name) -> dict:
        """解析 Google News RSS 条目"""
        # Google News 的 title 格式：标题 - 来源
        title = entry.get('title', '')
        source = source_name
        
        # 尝试从 title 中提取真实来源
        if ' - ' in title:
            parts = title.rsplit(' - ', 1)
            if len(parts) == 2:
                title, source = parts[0], parts[1]
        
        # 发布时间
        published = None
        if 'published' in entry:
            try:
                published = datetime.strptime(entry['published'], '%a, %d %b %Y %H:%M:%S %Z')
            except:
                published = datetime.now()
        
        # 链接
        link = entry.get('link', '')
        if not link and 'links' in entry:
            for l in entry['links']:
                if l.get('type') == 'text/html':
                    link = l.get('href', '')
                    break
        
        # 摘要（从 description 或 summary 提取）
        summary = entry.get('summary', entry.get('description', ''))
        # 清理 HTML 标签
        if summary:
            from html import unescape
            summary = unescape(summary)
            import re
            summary = re.sub(r'<[^>]+>', '', summary)
            summary = summary.strip()[:200]
        
        # 检测是否英文，标记待翻译
        is_english = any(c.isascii() for c in title) and not any('\u4e00' <= c <= '\u9fff' for c in title)
        
        return {
            'title': title.strip(),
            'source': source.strip() if source else 'Google News',
            'published': published or datetime.now(),
            'summary': summary if summary else '详情点击链接查看',
            'link': link,
            'category': '行业动态',
            'is_english': is_english,
        }
    
    def collect_from_rss(self):
        """从 RSS 源采集（Google News RSS + 直接 RSS 媒体源）"""
        urls = self._build_google_news_urls() + self._build_direct_rss_urls()

        collected_count = 0
        noisy_title_markers = [
            'product guide', 'material handlers', 'compact wheel loaders',
            'the sickest construction equipment', 'conexpo 2026', 'conexpo-con/agg',
            '征求意见稿', '问卷调研', '品牌共创者',
        ]
        noisy_link_markers = [
            '/product-guide', '/products/', '/material-handlers', '/compact-wheel-loaders'
        ]

        for source_name, url, lang in urls:
            try:
                logger.info(f"采集 RSS: {source_name} ({lang})")
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; LoaderIntel/1.0)'
                })

                if response.status_code != 200:
                    logger.warning(f"RSS 请求失败：{source_name} - {response.status_code}")
                    continue

                feed = feedparser.parse(response.content)

                for entry in feed.entries[:10]:
                    item = self._parse_google_news_entry(entry, source_name)
                    title = item.get('title', '')
                    summary = item.get('summary', '')
                    link = item.get('link', '')
                    title_lower = title.lower()
                    link_lower = link.lower()

                    if not self._matches_keywords(title + ' ' + summary):
                        continue
                    if any(marker in title_lower for marker in noisy_title_markers):
                        continue
                    if any(marker in link_lower for marker in noisy_link_markers):
                        continue

                    item = self._normalize_item(item)
                    if not self._within_time_window(item.get('published')):
                        continue

                    news_hash = self._generate_hash(item['title'], item['source'])
                    if not self._is_duplicate(news_hash):
                        self.news_items.append(item)
                        collected_count += 1
                        logger.info(f"采集：{item['title'][:40]}...")

            except Exception as e:
                logger.warning(f"RSS 采集失败 {source_name}: {e}")

        return collected_count
    
    def collect_from_industry_sites(self):
        """从行业网站采集"""
        collected_count = 0
        
        # 导入解析器
        try:
            sys.path.insert(0, str(self.base_dir / 'scripts'))
            from parsers.d1cm_parser import D1CMParser
            from parsers.ccema_parser import CCEMAParser
            from parsers.cehome_parser import CEHomeParser
        except ImportError as e:
            logger.warning(f"导入解析器失败：{e}")
            return 0
        
        # 采集第一工程机械网
        try:
            logger.info("采集：第一工程机械网...")
            d1cm = D1CMParser()
            items = d1cm.collect(max_items=15)
            
            for item in items:
                item = self._normalize_item(item)
                if not self._within_time_window(item.get('published')):
                    continue
                news_hash = self._generate_hash(item['title'], item['source'])
                if not self._is_duplicate(news_hash):
                    self.news_items.append(item)
                    collected_count += 1
                    logger.info(f"采集：{item['title'][:40]}...")
        except Exception as e:
            logger.warning(f"第一工程机械网采集失败：{e}")
        
        # 采集中国工程机械工业协会（实际站点：cncma.org）
        try:
            logger.info("采集：中国工程机械工业协会...")
            ccema = CCEMAParser()
            items = ccema.collect(max_items=15)

            for item in items:
                item = self._normalize_item(item)
                if not self._within_time_window(item.get('published')):
                    continue
                news_hash = self._generate_hash(item['title'], item['source'])
                if not self._is_duplicate(news_hash):
                    self.news_items.append(item)
                    collected_count += 1
                    logger.info(f"采集：{item['title'][:40]}...")
        except Exception as e:
            logger.warning(f"中国工程机械工业协会采集失败：{e}")

        # 采集铁甲工程机械网
        try:
            logger.info("采集：铁甲工程机械网...")
            cehome = CEHomeParser()
            items = cehome.collect(max_items=15)

            for item in items:
                item = self._normalize_item(item)
                if not self._within_time_window(item.get('published')):
                    continue
                news_hash = self._generate_hash(item['title'], item['source'])
                if not self._is_duplicate(news_hash):
                    self.news_items.append(item)
                    collected_count += 1
                    logger.info(f"采集：{item['title'][:40]}...")
        except Exception as e:
            logger.warning(f"铁甲工程机械网采集失败：{e}")
        
        return collected_count
    
    def _matches_keywords(self, text: str) -> bool:
        """检查文本是否匹配关键词：聚焦装载机 / wheel loader，尽量排除泛工程机械噪音。"""
        text_lower = text.lower()

        exclude = self.keywords_config.get('exclude_keywords', [])
        if any(kw.lower() in text_lower for kw in exclude):
            return False

        direct_loader_keywords = ['装载机', '轮式装载机', 'wheel loader', 'wheel loaders', '铲车']
        company_aliases = []
        companies = self.companies_config.get('companies', {})
        for company in companies.get('domestic', []) + companies.get('international', []):
            company_aliases.append(company['name'].lower())
            company_aliases.extend([a.lower() for a in company.get('aliases', [])])

        has_direct_loader = any(kw in text_lower for kw in direct_loader_keywords)
        has_company = any(alias in text_lower for alias in company_aliases)
        has_loader_word = 'loader' in text_lower

        if has_direct_loader:
            return True
        if has_company and has_loader_word:
            return True
        return False

    def _within_time_window(self, published, primary_days: int = 7, fallback_days: int = 14) -> bool:
        """优先保留近 7 天，兜底保留近 14 天，避免旧闻反复进入日报。"""
        if not published:
            return True
        if isinstance(published, str):
            try:
                published = datetime.fromisoformat(published)
            except Exception:
                return True
        now = datetime.now()
        if published >= now - timedelta(days=primary_days):
            return True
        if published >= now - timedelta(days=fallback_days):
            return True
        return False

    def _normalize_item(self, item: dict) -> dict:
        title = ' '.join(str(item.get('title', '')).split())[:120]
        summary = ' '.join(str(item.get('summary', '')).split())[:140]
        item['title'] = title
        item['summary'] = summary
        return item
    
    def _get_mock_news(self) -> list:
        """获取模拟新闻（备用）"""
        return [
            {
                "title": "三一重工发布新一代电动装载机，续航能力提升 40%",
                "source": "工程机械周刊",
                "published": datetime.now() - timedelta(hours=5),
                "summary": "三一重工今日发布 SY956E 电动装载机，采用最新电池技术，单次充电工作时间达 8 小时。",
                "link": "https://example.com/news/1",
                "category": "新品发布"
            },
            {
                "title": "徐工无人装载机在矿山场景实现商业化落地",
                "source": "中国工程机械工业协会",
                "published": datetime.now() - timedelta(hours=12),
                "summary": "徐工集团宣布其 LW580KV 无人装载机已在某大型矿山实现 24 小时连续作业。",
                "link": "https://example.com/news/2",
                "category": "商业落地"
            },
            {
                "title": "卡特彼勒推出远程操控系统，操作员可在办公室控制装载机",
                "source": "Construction Equipment",
                "published": datetime.now() - timedelta(hours=24),
                "summary": "Caterpillar 新推出的 Command 系统支持 5G 远程操控，延迟低于 100ms。",
                "link": "https://example.com/news/3",
                "category": "技术突破"
            },
            {
                "title": "柳工与华为合作开发智能工程机械云平台",
                "source": "财经网",
                "published": datetime.now() - timedelta(hours=36),
                "summary": "双方将共同开发基于 AI 的设备预测性维护和车队管理系统。",
                "link": "https://example.com/news/4",
                "category": "商业合作"
            },
            {
                "title": "2026 年 Q1 装载机销量同比增长 15%，电动化趋势明显",
                "source": "第一工程机械网",
                "published": datetime.now() - timedelta(hours=48),
                "summary": "行业协会数据显示，电动装载机渗透率已达 8%，同比提升 5 个百分点。",
                "link": "https://example.com/news/5",
                "category": "市场动态"
            }
        ]
    
    def collect_from_search(self, query):
        """从搜索引擎采集（模拟）"""
        # 实际环境中可以调用搜索 API
        logger.debug(f"搜索查询：{query}")
        return []
    
    def collect_all(self):
        """执行完整采集流程"""
        logger.info("=" * 50)
        logger.info("开始采集装载机行业情报")
        logger.info("=" * 50)
        
        # 从 RSS 采集
        rss_count = self.collect_from_rss()
        
        # 从行业网站采集
        site_count = self.collect_from_industry_sites()
        
        # 保存去重缓存
        self._save_seen_hashes()
        
        total = len(self.news_items)
        logger.info(f"采集完成：共 {total} 条新闻 (RSS: {rss_count}, 行业网站：{site_count})")
        
        # 保存原始数据
        self._save_raw_data()
        
        return self.news_items
    
    def _save_raw_data(self):
        """保存原始采集数据"""
        data_file = self.data_dir / f"raw_{datetime.now().strftime('%Y%m%d')}.json"
        
        serializable_items = []
        for item in self.news_items:
            serializable_item = item.copy()
            if 'published' in item and isinstance(item['published'], datetime):
                serializable_item['published'] = item['published'].isoformat()
            serializable_items.append(serializable_item)
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_items, f, ensure_ascii=False, indent=2)
        
        logger.info(f"原始数据已保存：{data_file}")


def main():
    """主函数"""
    collector = NewsCollector()
    news_items = collector.collect_all()
    
    if news_items:
        print(f"\n✅ 采集完成：{len(news_items)} 条新闻")
        return 0
    else:
        print("\n⚠️  未采集到新闻")
        return 1


if __name__ == "__main__":
    sys.exit(main())
