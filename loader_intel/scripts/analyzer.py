#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
装载机行业情报分析器
对采集的新闻进行分类、重要性判断和趋势分析
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsAnalyzer:
    """新闻分析器"""
    
    def __init__(self, config_dir=None):
        self.base_dir = Path(__file__).parent.parent
        self.config_dir = config_dir or self.base_dir / "config"
        
        # 加载配置
        self.keywords_config = self._load_config("keywords.yaml")
        self.companies_config = self._load_config("companies.yaml")
        
        # 分析结果
        self.analyzed_items = []
        
    def _load_config(self, filename):
        """加载 YAML 配置"""
        config_path = self.config_dir / filename
        if not config_path.exists():
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _categorize_news(self, item: Dict) -> str:
        """对新闻进行分类"""
        title = item.get('title', '').lower()
        summary = item.get('summary', '').lower()
        content = f"{title} {summary}"
        
        # 厂商动态
        companies = self.companies_config.get('companies', {})
        for company in companies.get('domestic', []) + companies.get('international', []):
            for alias in company.get('aliases', [company['name']]):
                if alias.lower() in content:
                    return "厂商动态"
        
        # 技术类别判断
        tech_keywords = {
            "无人化": ["无人", "自动", "autonomous", "unmanned"],
            "电动化": ["电动", "电池", "electric", "新能源"],
            "智能化": ["智能", "AI", "人工智能", "intelligent", "smart"],
            "远程操控": ["远程", "遥控", "teleoperation", "remote control"],
            "新品发布": ["发布", "推出", "launch", "new product"],
            "商业合作": ["合作", "签约", "partnership", "collaboration"],
            "市场动态": ["销量", "市场", "增长", "market", "sales"],
        }
        
        for category, keywords in tech_keywords.items():
            if any(kw in content for kw in keywords):
                return category
        
        return "行业动态"
    
    def _assess_importance(self, item: Dict) -> str:
        """评估新闻重要性（针对装载机 / wheel loader 相关新闻校准）"""
        title = item.get('title', '')
        summary = item.get('summary', '')
        category = item.get('category', '')
        source = item.get('source', '') or ''

        title_lower = title.lower()
        summary_lower = summary.lower()
        content = f"{title} {summary}"
        content_lower = f"{title_lower} {summary_lower}"

        score = 0
        reasons = []

        def add(points: int, reason: str):
            nonlocal score
            score += points
            reasons.append(f"{points:+d} {reason}")

        # 类别权重
        high_priority_categories = ["无人化", "电动化", "新品发布", "技术突破"]
        if category in high_priority_categories:
            add(30, f"high-priority category={category}")
        elif category in ["厂商动态", "市场动态"]:
            add(12, f"category={category}")

        # 直接装载机 / wheel loader 相关性加分
        if 'wheel loader' in content_lower or '装载机' in content or '轮式装载机' in content:
            add(20, 'direct loader relevance')
        if 'wheel loader lineup' in content_lower or '装载机销量' in content or 'loader lineup' in content_lower:
            add(12, 'loader lineup / sales signal')

        # 对装载机 OEM 正式新闻、产品更新/发布/销量数据加分
        high_priority_keywords = [
            "首台", "突破", "量产", "商业化", "发布", "更新", "升级",
            "战略合作", "重大", "全球首款", "行业领先", "销量", "交付",
            "debut", "launch", "introduces", "unveils", "award", "finalist",
            "update", "updates", "lineup", "sales", "delivers", "delivery"
        ]
        keyword_hits = []
        for kw in high_priority_keywords:
            if kw.lower() in content_lower:
                keyword_hits.append(kw)
        if keyword_hits:
            add(min(len(keyword_hits) * 6, 24), f"keywords={','.join(keyword_hits[:6])}")

        # 厂商权重（重点厂商）
        companies = self.companies_config.get('companies', {})
        for company in companies.get('domestic', [])[:4] + companies.get('international', [])[:6]:
            if any(alias.lower() in content_lower for alias in company.get('aliases', [company['name']])):
                add(15, f"company={company['name']}")
                break

        # 来源权重：官方站和垂直媒体提高优先级
        source_lower = source.lower()
        if any(k in source_lower for k in ['volvo construction equipment', 'liugong', 'sany', 'xcmg', 'develon', 'hitachi', 'caterpillar', 'komatsu']):
            add(18, f"oem source={source}")
        elif any(k in source_lower for k in ['construction equipment', 'equipment world', 'forconstructionpros', 'heavy equipment guide', 'international mining', '第一工程机械网']):
            add(10, f"industry source={source}")

        # 时效性权重：近 7 天仍应有存在感，但当天/24h 内优先
        published = item.get('published')
        if published:
            if isinstance(published, str):
                published = datetime.fromisoformat(published)
            hours_ago = (datetime.now() - published).total_seconds() / 3600
            if hours_ago < 24:
                add(20, 'fresh<24h')
            elif hours_ago < 72:
                add(12, 'fresh<72h')
            elif hours_ago < 24 * 7:
                add(6, 'fresh<7d')
            elif hours_ago < 24 * 14:
                add(2, 'fresh<14d')

        # 轻度降权：明显偏问答/百科型内容不应占据日报重点
        if any(k in content_lower for k in ['是什么', 'what is', 'how to', '百科', '参数详解']):
            add(-18, 'qa/explainer penalty')

        # 重要性分级：让 OEM 正式 wheel loader 新闻更容易进“中”
        if score >= 58:
            level = "高"
        elif score >= 28:
            level = "中"
        else:
            level = "低"

        logger.info(f"打分明细：{title[:50]}... => {level} ({score}) | {'; '.join(reasons) if reasons else 'no hits'}")
        return level
    
    def _extract_company(self, item: Dict) -> str:
        """提取相关新闻的厂商"""
        title = item.get('title', '')
        summary = item.get('summary', '')
        content = f"{title} {summary}"
        
        companies = self.companies_config.get('companies', {})
        for company in companies.get('domestic', []) + companies.get('international', []):
            for alias in company.get('aliases', [company['name']]):
                if alias in content:
                    return company['name']
        
        return "其他"
    
    def analyze(self, news_items: List[Dict]) -> List[Dict]:
        """分析新闻列表"""
        logger.info("=" * 50)
        logger.info("开始分析新闻内容")
        logger.info("=" * 50)

        analyzed = []
        noisy_markers = ['征求意见稿', '问卷调研', '品牌共创者', 'product guide', 'material handlers']

        for item in news_items:
            title = item.get('title', '')
            if any(marker.lower() in title.lower() for marker in noisy_markers):
                logger.info(f"跳过噪音：{title[:30]}...")
                continue
            analyzed_item = item.copy()
            analyzed_item['category'] = self._categorize_news(item)
            analyzed_item['importance'] = self._assess_importance(item)
            analyzed_item['company'] = self._extract_company(item)
            analyzed.append(analyzed_item)

            logger.info(f"分析：{item['title'][:30]}... → {analyzed_item['category']} ({analyzed_item['importance']})")
        
        # 按重要性排序
        importance_order = {"高": 0, "中": 1, "低": 2}
        analyzed.sort(key=lambda x: (importance_order.get(x['importance'], 3), x.get('published', '')))
        
        self.analyzed_items = analyzed
        
        logger.info(f"分析完成：{len(analyzed)} 条新闻")
        
        # 统计
        categories = {}
        importance_counts = {"高": 0, "中": 0, "低": 0}
        for item in analyzed:
            cat = item.get('category', '未知')
            categories[cat] = categories.get(cat, 0) + 1
            importance_counts[item.get('importance', '低')] += 1
        
        logger.info(f"分类统计：{categories}")
        logger.info(f"重要性分布：{importance_counts}")
        
        # 保存分析结果
        self._save_analyzed_data(analyzed)
        
        return analyzed
    
    def _save_analyzed_data(self, analyzed: List[Dict]):
        """保存分析结果到文件"""
        data_dir = self.base_dir / "data"
        today = datetime.now().strftime('%Y%m%d')
        output_file = data_dir / f"analyzed_{today}.json"
        
        # 处理 datetime 序列化
        serializable = []
        for item in analyzed:
            serializable_item = item.copy()
            if 'published' in item and isinstance(item['published'], datetime):
                serializable_item['published'] = item['published'].isoformat()
            serializable.append(serializable_item)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分析结果已保存：{output_file}")
    
    def get_trend_insights(self) -> Dict:
        """生成趋势洞察"""
        insights = {
            "无人化": 0,
            "电动化": 0,
            "智能化": 0,
            "远程操控": 0,
        }
        
        for item in self.analyzed_items:
            category = item.get('category', '')
            if category in insights:
                insights[category] += 1
        
        # 找出最热门趋势
        top_trend = max(insights, key=insights.get) if insights else "无明显趋势"
        
        return {
            "trend_scores": insights,
            "top_trend": top_trend,
            "summary": self._generate_trend_summary(insights)
        }
    
    def _generate_trend_summary(self, insights: Dict) -> str:
        """生成趋势总结"""
        active_trends = [k for k, v in insights.items() if v > 0]
        
        if not active_trends:
            return "今日暂无明显技术趋势"
        
        if len(active_trends) == 1:
            return f"今日重点关注：{active_trends[0]}"
        
        return f"今日多趋势并行：{', '.join(active_trends)}"


def main():
    """主函数"""
    # 读取采集数据
    data_dir = Path(__file__).parent.parent / "data"
    today = datetime.now().strftime('%Y%m%d')
    data_file = data_dir / f"raw_{today}.json"
    
    if not data_file.exists():
        logger.error(f"未找到采集数据：{data_file}")
        return 1
    
    with open(data_file, 'r', encoding='utf-8') as f:
        news_items = json.load(f)
    
    analyzer = NewsAnalyzer()
    analyzed = analyzer.analyze(news_items)
    
    # 保存分析结果
    output_file = data_dir / f"analyzed_{today}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        # 处理 datetime 序列化
        serializable = []
        for item in analyzed:
            serializable_item = item.copy()
            if 'published' in item and isinstance(item['published'], datetime):
                serializable_item['published'] = item['published'].isoformat()
            serializable.append(serializable_item)
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    
    logger.info(f"分析结果已保存：{output_file}")
    print(f"\n✅ 分析完成：{len(analyzed)} 条新闻")
    print(f"分析结果已保存：{output_file}")
    
    return analyzed


if __name__ == "__main__":
    sys.exit(main())
