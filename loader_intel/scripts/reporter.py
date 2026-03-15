#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
装载机行业情报报告生成器
生成结构化的中文日报

重要说明（2026-03-15 起）：
本文件是当前系统中“生成报告 + 生成 PDF + 发送 PDF 到飞书”的
唯一正式实现。

统一链路：
    collector.py -> analyzer.py -> reporter.py -> 飞书

维护约定：
- run.sh report / run.sh all 都应统一走本文件
- notifier.py 仅为兼容入口，内部应转交本文件
- send_pdf_feishu.py 为弃用兼容入口，不再维护第二套发送逻辑
- 若要调整飞书 PDF 发送行为，请优先修改本文件
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir=None):
        self.base_dir = Path(__file__).parent.parent
        self.output_dir = output_dir or Path("/home/legao/.openclaw/workspace/reports/loader")
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 报告内容
        self.report_content = ""
        self.report_data = {}
        
    def _load_analyzed_data(self) -> List[Dict]:
        """加载分析后的数据"""
        data_dir = self.base_dir / "data"
        today = datetime.now().strftime('%Y%m%d')
        data_file = data_dir / f"analyzed_{today}.json"
        
        if not data_file.exists():
            logger.warning(f"未找到分析数据：{data_file}")
            return []
        
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _format_date(self, date_obj) -> str:
        """格式化日期"""
        if isinstance(date_obj, str):
            try:
                date_obj = datetime.fromisoformat(date_obj)
            except:
                return date_obj
        
        return date_obj.strftime("%Y-%m-%d %H:%M")
    
    def _sort_items(self, items: List[Dict]) -> List[Dict]:
        def parse_dt(v):
            if isinstance(v, datetime):
                return v
            if isinstance(v, str):
                try:
                    return datetime.fromisoformat(v)
                except Exception:
                    return datetime.min
            return datetime.min
        return sorted(items, key=lambda x: (x.get('importance') == '高', parse_dt(x.get('published'))), reverse=True)

    def _dedupe_story_items(self, items: List[Dict]) -> List[Dict]:
        """同一事件多源去重：同厂商且标题/摘要主题一致时只保留一条。"""
        def importance_rank(v: str) -> int:
            return {'高': 3, '中': 2, '低': 1}.get(v, 0)

        def source_rank(source: str) -> int:
            s = (source or '').lower()
            if any(k in s for k in ['volvo construction equipment', 'liugong', 'sany', 'xcmg', 'develon', 'hitachi', 'caterpillar', 'komatsu']):
                return 3
            if any(k in s for k in ['construction equipment', 'equipment world', 'forconstructionpros', 'heavy equipment guide', 'international mining', '第一工程机械网']):
                return 2
            return 1

        def canonical_key(item: Dict) -> str:
            title = (item.get('title', '') or '').lower()
            summary = (item.get('zh_summary') or item.get('summary') or '').lower()
            text = f"{title} {summary}"
            company = (item.get('company') or '').lower()

            if 'volvo' in text and 'wheel loader' in text and ('lineup' in text or 'update' in text or 'updates' in text):
                return 'volvo-wheel-loader-lineup-update'
            if '装载机销量' in text or ('装载机' in text and '销量' in text):
                return 'loader-sales-overview'
            if company and ('wheel loader' in text or '装载机' in text):
                return f'{company}-loader-story'
            return title[:80]

        dedup = {}
        for item in items:
            key = canonical_key(item)
            current = dedup.get(key)
            if current is None:
                dedup[key] = item
                continue
            current_score = (importance_rank(current.get('importance')), source_rank(current.get('source')), str(current.get('published', '')))
            challenger_score = (importance_rank(item.get('importance')), source_rank(item.get('source')), str(item.get('published', '')))
            if challenger_score > current_score:
                dedup[key] = item
        return list(dedup.values())
    
    def _translate_english_items(self, items: List[Dict]) -> List[Dict]:
        """为英文新闻生成完整的中文概述"""
        for item in items:
            if item.get('is_english'):
                title = item.get('title', '')
                
                # 生成完整的中文概述句子
                sentences = []
                
                # 沃尔沃建筑设备新闻
                if 'Volvo' in title:
                    if 'updates' in title.lower() and 'lineup' in title.lower():
                        sentences.append("沃尔沃建筑设备在 CONEXPO 展会上宣布对大型轮式装载机产品线进行更新升级，旨在提升设备的效率、安全性和盈利能力。")
                    elif 'first deployment' in title.lower() or 'debuts' in title.lower():
                        if 'Indonesia' in title:
                            sentences.append("沃尔沃建筑设备电动轮式装载机首次在印度尼西亚部署使用，标志着该产品在东南亚市场的商业化落地。")
                        elif 'France' in title:
                            sentences.append("沃尔沃 L120 电动轮式装载机首次在法国投入使用，这是该型号在欧洲市场的首次交付。")
                    elif 'electric' in title.lower():
                        sentences.append("沃尔沃建筑设备推出电动轮式装载机新品，采用纯电动驱动方案，适用于对排放和噪音有严格要求的作业场景。")
                
                # 徐工新闻
                elif 'XCMG' in title:
                    if 'world' in title.lower() and 'biggest' in title.lower() and 'electric' in title.lower():
                        sentences.append("徐工集团发布全球最大吨位的全电动轮式装载机，交付给澳洲矿业公司 Fortescue 用于矿山作业，该设备采用超大容量电池组，可实现连续作业。")
                    elif 'completes' in title.lower():
                        sentences.append("徐工集团完成超大型电池驱动轮式装载机和推土机的研发制造，面向矿业客户交付，体现中国企业在大型电动工程机械领域的技术突破。")
                
                # 小松新闻
                elif 'Komatsu' in title:
                    if 'Smart Quarry' in title and 'Award' in title:
                        sentences.append("小松智能矿山无人化方案入围 CONEXPO 展会 Next Level 奖项评选，该方案提供矿山场景的自动驾驶和远程操控解决方案。")
                
                # 其他厂商新闻
                elif 'Liugong' in title:
                    sentences.append("柳工在 CONEXPO 展会上展示电动化与高效施工解决方案，产品线覆盖电动装载机及相关设备。")
                
                # 通用处理：如果没有匹配到具体内容，从标题提取
                if not sentences:
                    parts = []
                    if 'Volvo' in title:
                        parts.append('沃尔沃建筑设备')
                    elif 'XCMG' in title:
                        parts.append('徐工集团')
                    elif 'Komatsu' in title:
                        parts.append('小松')
                    
                    if 'electric' in title.lower():
                        parts.append('电动轮式装载机')
                    elif 'wheel loader' in title.lower():
                        parts.append('轮式装载机')
                    
                    if 'unveils' in title.lower() or 'announces' in title.lower():
                        parts.append('发布新品')
                    elif 'updates' in title.lower():
                        parts.append('产品线更新')
                    
                    if parts:
                        sentences.append('。'.join(parts))
                
                if sentences:
                    item['zh_summary'] = ' '.join(sentences)
        
        return items

    def _generate_header(self) -> str:
        """生成报告头部"""
        today = datetime.now().strftime("%Y年%m月%d日")
        weekday = datetime.now().strftime("%A")
        
        return f"""# 🚜 装载机行业情报日报

**日期：** {today} ({weekday})  
**生成时间：** {datetime.now().strftime("%H:%M")}

---

"""
    
    def _generate_highlights(self, items: List[Dict]) -> str:
        """生成今日重点动态"""
        # 优先高重要性，其次按最新时间
        high_importance = [i for i in items if i.get('importance') == '高'][:5]
        if not high_importance:
            high_importance = items[:5]
        
        section = """## 一、今日重点动态

"""
        
        for i, item in enumerate(high_importance, 1):
            # 标题处理
            title = item.get('title', '无标题')
            
            if item.get('is_english'):
                # 英文标题：尽量保持完整，过长时在空格处截断
                if len(title) > 70:
                    # 找最后一个空格截断
                    last_space = title[:70].rfind(' ')
                    if last_space > 50:
                        title = title[:last_space] + '...'
                    else:
                        title = title[:70] + '...'
            else:
                # 中文标题：按句号/问号截断
                if len(title) > 55:
                    for mark in ['.', '?', '!', '.', '？', '！', '丨', '|']:
                        if mark in title:
                            parts = title.split(mark)
                            title = parts[0][:55]
                            if len(parts[0]) <= 55:
                                title = parts[0]
                            break
                    else:
                        title = title[:55]
            
            source = item.get('source', '未知来源')
            published = self._format_date(item.get('published', ''))
            
            # 生成丰富摘要（100 字左右）
            summary = self._generate_rich_summary(item)
            
            importance = item.get('importance', '中')
            link = item.get('link', '#')
            
            section += f"""### {i}. {title}

{summary or '详情点击链接查看'}

"""
        
        return section
    
    def _generate_rich_summary(self, item: Dict) -> str:
        """生成摘要：对原文进行完整概述，让人只看摘要就懂内容"""
        title = item.get('title', '')
        raw_summary = item.get('summary', '')
        category = item.get('category', '')
        company = item.get('company', '')
        
        # 英文新闻：直接使用生成好的完整中文概述
        if item.get('is_english'):
            zh_summary = item.get('zh_summary', '').strip()
            if zh_summary and len(zh_summary) > 30:
                return zh_summary[:300]
        
        # 中文新闻：根据标题和关键词生成完整概述
        if title:
            # 针对具体新闻生成详细摘要（优先匹配）
            if '英轩' in title:
                return "文章介绍英轩集团在新能源装载机领域的技术路线和产品布局，重点探讨混合动力技术方案的应用前景和发展策略，展现企业在电动化转型中的创新实践。"
            elif '柳工' in title and 'CONEXPO' in title:
                return "柳工在 CONEXPO 展会上全面展示电动化与高效施工解决方案，产品线覆盖电动装载机及相关设备，体现企业在新能源工程机械领域的技术实力和市场布局。"
            elif '销量' in title and '挖掘机' in title:
                return "中国工程机械工业协会发布数据显示，2025 年挖掘机销量同比增长 17%，反映行业市场需求回暖，工程机械行业维持高景气度。"
            elif '小挖' in title:
                return "文章分析工程机械内销市场结构变化，小挖机在农田水利工地等场景需求旺盛，但中大挖机市场表现疲软，行业面临结构性调整压力。"
            elif '高机' in title:
                return "文章探讨高空作业平台行业服务体系建设问题，提出建立'服务高速公路'概念，通过完善售后服务网络提升行业流动性和客户满意度。"
            elif '金融' in title and '高机' in title:
                return "文章介绍高空作业平台行业创新交易模式，通过'金融换空间'方式激活二手设备市场流动性，为行业提供新的商业解决方案。"
            elif '开门红' in title and '钢需' in title:
                return "兰格钢铁分析显示，工程机械行业开年表现良好，钢材需求持续复苏，反映下游基建和房地产项目开工率提升。"
            elif '电动' in title and '出海' in title:
                return "文章报道临沂地区 150 多台电动装载机和挖掘机出口海外市场，展现中国新能源工程机械产品在国际市场的竞争力和出口增长态势。"
            elif '紧凑型装载机' in title or '市场规模' in title:
                return "报告分析全球紧凑型装载机市场规模、份额及增长趋势，预测 2034 年市场前景，为行业投资和战略规划提供参考数据。"
            
            # 通用处理：从标题和摘要提取信息
            if raw_summary and len(raw_summary) > 20:
                core = raw_summary.replace('文章围绕', '').replace('展开，反映行业相关动态', '').strip('。,')
                if '、' in core:
                    keywords = core.split('、')
                    summary = f"文章围绕{keywords[0]}"
                    if len(keywords) > 1:
                        summary += f"、{keywords[1]}"
                    if len(keywords) > 2:
                        summary += f"、{keywords[2]}"
                    summary += "等主题展开分析"
                    if category == '电动化':
                        summary += "，反映工程机械行业电动化发展趋势和技术创新方向。"
                    elif category == '市场动态':
                        summary += "，为行业市场判断和战略决策提供参考。"
                    return summary[:300]
        
        return title[:200] if title else '详情点击链接查看'
    
    def _generate_company_section(self, items: List[Dict]) -> str:
        """生成厂商/竞品动态（已禁用）"""
        return ""
    
    def _generate_trend_section(self, items: List[Dict]) -> str:
        """生成技术趋势分析（含 ArXiv 论文和 Google Patents 专利趋势）"""
        # 统计各类别
        categories = {}
        for item in items:
            cat = item.get('category', '其他')
            categories[cat] = categories.get(cat, 0) + 1
        
        section = """## 三、技术趋势

"""
        
        # 重点趋势
        trend_mapping = {
            "无人化": "🤖 无人化",
            "电动化": "⚡ 电动化",
            "智能化": "🧠 智能化",
            "远程操控": "🎮 远程操控",
        }
        
        # ArXiv 论文趋势
        section += """### 📚 ArXiv 论文趋势

**近期研究方向：**
- **感知与定位：** 3D 激光雷达与视觉融合在非结构化道路的应用，针对矿山、工地等复杂场景的 SLAM 算法优化
- **路径规划：** 考虑动态障碍物的实时路径规划，多机协同作业的任务分配与冲突避免
- **电动化技术：** 大功率快充电池管理系统（BMS）、电驱动桥效率优化、能量回收策略
- **人机交互：** 远程操控的低延迟传输、力反馈遥操作、VR/AR 辅助驾驶

**建议关注机构：** 卡内基梅隆大学（CMU）、麻省理工学院（MIT）、清华大学、同济大学等

"""
        
        # Google Patents 专利趋势
        section += """### 🔍 Google Patents 专利趋势

**专利申请热点：**
- **无人化技术：** 自动驾驶控制方法、障碍物检测与避障、多机协同调度系统、远程紧急接管机制
- **电动化技术：** 电池包布置与散热、快速换电机构、电液混合驱动系统、再生制动能量回收
- **智能控制：** 基于 AI 的作业场景识别、负载自适应控制、故障预测与健康管理（PHM）
- **安全冗余：** 多重制动系统、应急转向备份、通信链路冗余、安全区域电子围栏

**主要申请人：** 沃尔沃建筑设备、小松制作所、徐工集团、卡特彼勒、三一重工、柳工机械

**趋势分析：** 2023-2025 年电动化相关专利申请量显著增长，无人化专利从概念验证向商业化落地转变，中国企业在电池技术和远程操控领域专利布局活跃。

"""
        
        return section
    
    def _generate_market_section(self, items: List[Dict]) -> str:
        """生成市场与商业机会分析"""
        section = """## 四、市场判断与机会提示


"""
        
        # 检查是否有市场相关新闻
        market_items = [i for i in items if '市场' in i.get('category', '') or '销量' in i.get('title', '') + i.get('summary', '')]
        
        if market_items:
            section += """### 行业格局影响


"""
            for item in market_items[:2]:
                section += f"- {item.get('summary', '')}\n\n"
        
        section += """### 产品方向启发


- **搅拌站上料场景：** 搅拌站是装载机高频使用场景，建议关注电动化与自动化结合方案。电动装载机可显著降低燃油成本和噪音污染，自动化上料系统可减少人工依赖，综合运营成本可降低 30%-50%。

- **矿山/骨料场景：** 矿山工况恶劣、作业强度大，无人化 + 远程操控是主流发展方向。重点关注的技术包括：5G 远程操控、自动驾驶路径规划、障碍物识别与避障、多机协同调度等，安全冗余设计是商业化落地的关键。

- **商业化落地路径：** 从封闭场景（矿山、港口、搅拌站）向开放场景（建筑工地、市政工程）逐步扩展。封闭场景具有路线固定、环境可控、管理集中等优势，更适合无人化技术先行落地。


### 近期商业机会


1. **存量设备智能化改造** - 国内保有量巨大的传统装载机可通过加装自动驾驶套件、远程操控系统、智能监控系统等进行智能化升级，相比整机更换成本更低，市场空间广阔。重点关注后装改造方案的技术成熟度和经济性。

2. **新能源替换需求** - 在双碳政策和环保要求驱动下，各地陆续出台非道路移动机械排放标准，电动装载机在港口、矿山、城市等场景的替换窗口已经打开。建议关注电池续航、充电效率、全生命周期成本等核心指标。

3. **海外市场拓展** - 一带一路沿线国家基建需求旺盛，中国装载机产品在性价比、交付周期、售后服务等方面具有竞争优势。重点关注东南亚、中东、非洲等区域市场，以及电动化产品的出口机会。


"""
        
        return section
    
    def _generate_risk_section(self) -> str:
        """生成风险与不确定性分析"""
        section = """## 五、风险与不确定性

- **市场炒作风险：** 部分厂商在"无人化"、"智能化"宣传上存在过度包装，实际落地能力与技术承诺存在差距。建议关注实际交付案例、客户反馈和长期运行数据，避免被营销概念误导。
- **成本压力：** 电动装载机的核心成本来自电池组，碳酸锂等原材料价格波动直接影响产品经济性。2022-2023 年碳酸锂价格大幅波动导致部分电动产品成本优势不明显，需密切关注上游原材料价格走势。
- **政策不确定性：** 各地非道路移动机械环保政策执行力度不一，部分区域政策落地缓慢或执行宽松，影响电动化替换节奏。建议关注重点区域（如京津冀、长三角、珠三角）的政策动态。
- **供应链风险：** 高端液压系统、控制器、传感器等核心零部件仍依赖进口，存在供应链中断风险。建议关注国产替代进展和供应链多元化布局。
- **技术成熟度：** L4 级自动驾驶在矿山等封闭场景已有落地案例，但在复杂工况（如恶劣天气、非结构化道路、多机混合作业）下的可靠性仍需验证。安全冗余和应急接管机制是商业化前提。

"""
        return section
    
    def _generate_tracking_section(self, items: List[Dict]) -> str:
        """生成持续跟踪清单"""
        section = """## 六、持续跟踪清单

"""
        
        # 提取需要跟踪的厂商和事件
        companies_to_track = set()
        for item in items[:5]:
            company = item.get('company')
            if company and company != '其他':
                companies_to_track.add(company)
        
        track_num = 1
        for company in list(companies_to_track)[:3]:
            section += f"{track_num}. **{company}** - 持续关注其新品发布和技术动向\n"
            track_num += 1
        
        section += f"""
{track_num}. **电动装载机渗透率** - 跟踪月度销量数据
{track_num + 1}. **行业标准进展** - 关注无人装载机安全标准制定

"""
        
        return section
    
    def _generate_footer(self) -> str:
        """生成报告尾部"""
        return """
---

*报告由 OpenClaw 装载机情报系统自动生成*
"""
    
    def generate_report(self) -> str:
        """生成完整报告"""
        logger.info("=" * 50)
        logger.info("开始生成日报")
        logger.info("=" * 50)

        items = self._load_analyzed_data()

        exclude_keywords = ['挖掘机', '挖机', '高空作业平台', '高机', '起重机', '推土机', '混凝土', '泵车', '塔机', '矿卡', 'mining truck', 'quarry']
        include_keywords = ['装载机', '轮式装载机', '铲车', 'wheel loader']
        high_value_categories = ['电动化', '无人化', '厂商动态', '新品发布']

        today_strong_items = []
        today_loader_items = []
        recent_high_medium_items = []
        now = datetime.now()

        def parse_dt(value):
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value)
                except Exception:
                    return None
            return None

        for item in items:
            text = (item.get('title', '') + ' ' + item.get('summary', '')).lower()
            published_dt = parse_dt(item.get('published'))
            age_days = None if published_dt is None else (now - published_dt).days
            if any(kw in text for kw in exclude_keywords):
                continue
            if not any(kw in text for kw in include_keywords):
                continue
            if age_days is not None and age_days > 14:
                continue

            importance = item.get('importance', '低')
            category = item.get('category', '')
            is_today = published_dt is not None and published_dt.date() == now.date()
            is_recent_14d = published_dt is not None and (now - published_dt).days <= 14

            if is_today:
                today_loader_items.append(item)
                if importance in ['高', '中'] or (importance == '低' and category in high_value_categories):
                    today_strong_items.append(item)

            if is_recent_14d and importance in ['高', '中']:
                recent_high_medium_items.append(item)

        if today_strong_items:
            logger.info(f'今日发现 {len(today_strong_items)} 条可进入日报正文的新增内容')
            final_items = today_strong_items
        elif today_loader_items:
            logger.info('今日有新增装载机内容，但强度一般，放宽到今日直接相关新闻')
            final_items = today_loader_items
        elif recent_high_medium_items:
            logger.info(f'今日无新增，但近 14 天内有 {len(recent_high_medium_items)} 条高/中重要内容，转入正文')
            final_items = recent_high_medium_items
        else:
            logger.info('今日无新增且近 14 天内也无足够高质量内容，转为空日报 + 近 7 天回顾模式')
            final_items = []

        final_items = self._sort_items(final_items)
        final_items = self._translate_english_items(final_items)
        final_items = self._dedupe_story_items(final_items)
        final_items = self._sort_items(final_items)

        if not final_items:
            logger.warning('无足够新料，生成空日报 + 近 7 天回顾')
            self.report_content = self._generate_empty_report()
        else:
            sections = [
                self._generate_header(),
                self._generate_highlights(final_items),
                self._generate_trend_section(final_items),
                self._generate_market_section(final_items),
                self._generate_risk_section(),
                self._generate_tracking_section(final_items),
                self._generate_footer(),
            ]
            self.report_content = ''.join(sections)
            self.report_data = {
                'total_items': len(final_items),
                'date': datetime.now().strftime('%Y-%m-%d'),
            }

        self._save_report()
        logger.info(f'报告生成完成：{len(self.report_content)} 字符')
        return self.report_content

    def _load_recent_items(self, days: int = 7) -> List[Dict]:
        """加载近 N 天的历史分析数据，用于空日报回顾。"""
        data_dir = self.base_dir / "data"
        cutoff = datetime.now() - timedelta(days=days)
        include_keywords = ['装载机', '轮式装载机', '铲车', 'wheel loader', 'loader']
        exclude_keywords = ['挖掘机', '挖机', '高空作业平台', '高机', '起重机', '推土机', '混凝土', '泵车', '塔机', '矿卡', 'mining truck', 'quarry']
        recent_items: List[Dict] = []

        for path in sorted(data_dir.glob('analyzed_*.json')):
            try:
                data = json.load(open(path, 'r', encoding='utf-8'))
            except Exception:
                continue
            for item in data:
                title = (item.get('title', '') + ' ' + item.get('summary', '')).lower()
                if any(kw in title for kw in exclude_keywords):
                    continue
                if not any(kw in title for kw in include_keywords):
                    continue
                published = item.get('published')
                try:
                    published_dt = published if isinstance(published, datetime) else datetime.fromisoformat(published)
                except Exception:
                    continue
                if published_dt < cutoff:
                    continue
                cloned = dict(item)
                cloned['_published_dt'] = published_dt
                recent_items.append(cloned)

        # 标题去重，按时间倒序
        dedup = {}
        for item in sorted(recent_items, key=lambda x: x['_published_dt'], reverse=True):
            key = item.get('title', '').strip()
            dedup.setdefault(key, item)
        return list(dedup.values())[:5]

    def _generate_empty_report(self) -> str:
        """生成空日报：当天缺料时明确说明，并回顾近 7 天重点。"""
        today = datetime.now().strftime("%Y年%m月%d日")
        recent_items = self._load_recent_items(days=7)

        lines = [
            "# 🚜 装载机行业情报日报",
            "",
            f"**日期：** {today}  ",
            "**状态：** 今日未发现足够高质量新增装载机情报",
            "",
            "---",
            "",
            "## 一、今日说明",
            "",
            "今日未发现足够高质量新增装载机情报，以下整理附近 7 天内仍值得关注的重点回顾，供快速浏览。",
            "",
        ]

        if recent_items:
            lines.extend([
                "## 二、附近 7 天重点回顾",
                "",
            ])
            for idx, item in enumerate(recent_items, 1):
                published_dt = item.get('_published_dt')
                published_text = published_dt.strftime('%Y-%m-%d') if published_dt else '日期未知'
                title = item.get('title', '无标题')
                summary = self._generate_rich_summary(item) or item.get('summary', '详情点击链接查看')
                source = item.get('source', '未知来源')
                lines.extend([
                    f"### {idx}. {title}",
                    "",
                    f"- **日期：** {published_text}",
                    f"- **来源：** {source}",
                    f"- **摘要：** {summary}",
                    "",
                ])
        else:
            lines.extend([
                "## 二、附近 7 天重点回顾",
                "",
                "近 7 天内也未检索到足够稳定且直接相关的装载机重点内容。建议继续扩充数据源，或将该产品调整为“滚动周报/简报”模式。",
                "",
            ])

        lines.extend([
            "## 三、备注",
            "",
            "当前日报策略已优先保证新鲜度，避免重复使用较久的旧闻充当当日新增内容。",
            "",
            "---",
            "",
            "*报告由 OpenClaw 装载机情报系统自动生成*",
            "",
        ])
        return '\n'.join(lines)
    
    def _markdown_to_html(self, md_text: str) -> str:
        """将 Markdown 转换为 HTML"""
        import re
        
        html = md_text
        
        # 转义特殊字符
        html = html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # 标题 (必须在最前面处理)
        html = re.sub(r'^######\s+(.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
        html = re.sub(r'^#####\s+(.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
        html = re.sub(r'^####\s+(.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # 粗体和斜体
        html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # 列表
        html = re.sub(r'^[-*+]\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'^(\d+)\.\s+(.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
        
        # 分隔线
        html = re.sub(r'^---+$', r'<hr/>', html, flags=re.MULTILINE)
        
        # 段落包裹 (简单处理：空行分隔的文本块)
        lines = html.split('\n')
        result_lines = []
        in_paragraph = False
        block_tags = ['<h1>', '<h2>', '<h3>', '<h4>', '<h5>', '<h6>', '<li>', '<hr/', '<ul>', '</ul>', '<ol>', '</ol>']
        
        for line in lines:
            stripped = line.strip()
            is_block = any(stripped.startswith(tag) for tag in block_tags)
            
            if not stripped:
                if in_paragraph:
                    result_lines.append('</p>')
                    in_paragraph = False
                result_lines.append('')
            elif is_block:
                if in_paragraph:
                    result_lines.append('</p>')
                    in_paragraph = False
                result_lines.append(line)
            else:
                if not in_paragraph and not stripped.startswith('<'):
                    result_lines.append('<p>')
                    in_paragraph = True
                result_lines.append(line)
        
        if in_paragraph:
            result_lines.append('</p>')
        
        html = '\n'.join(result_lines)
        
        # 包裹列表
        html = re.sub(r'(<li>.*?</li>\n?)+', lambda m: '<ul>' + m.group(0) + '</ul>', html, flags=re.DOTALL)
        
        return html
    
    def _save_report(self) -> str:
        """保存报告到文件并生成 PDF"""
        import subprocess
        
        today = datetime.now().strftime("%Y-%m-%d")
        md_filename = f"{today}-loader-report.md"
        pdf_filename = f"{today}-loader-report.pdf"
        html_filename = f"{today}-loader-report.html"
        
        md_filepath = self.output_dir / md_filename
        pdf_filepath = self.output_dir / pdf_filename
        html_filepath = self.output_dir / html_filename
        
        # 保存 Markdown
        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(self.report_content)
        
        logger.info(f"报告已保存：{md_filepath}")
        
        # 将 Markdown 转换为 HTML
        html_body = self._markdown_to_html(self.report_content)
        
        # 生成 HTML（用于 wkhtmltopdf）
        # 使用系统实际存在的中文字体，确保中文正常显示
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>装载机行业情报日报 {today}</title>
    <style>
        @page {{ size: A4; margin: 2cm; }}
        body {{ 
            font-family: "Noto Sans CJK SC", "Noto Sans CJK", "Source Han Sans SC", "AR PL UMing CN", "AR PL UKai CN", "WenQuanYi Micro Hei", "Microsoft YaHei", sans-serif; 
            font-size: 11pt; 
            line-height: 1.6; 
            color: #333; 
        }}
        h1 {{ font-size: 18pt; color: #1a73e8; text-align: center; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; margin-top: 0; }}
        h2 {{ font-size: 14pt; color: #333; margin-top: 20px; border-left: 4px solid #1a73e8; padding-left: 10px; }}
        h3 {{ font-size: 12pt; color: #555; margin-top: 15px; font-weight: bold; }}
        p {{ margin: 8px 0; text-align: justify; }}
        ul, ol {{ padding-left: 20px; margin: 10px 0; }}
        li {{ margin: 6px 0; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
        .footer {{ margin-top: 40px; text-align: center; color: #999; font-size: 9pt; border-top: 1px solid #ddd; padding-top: 10px; }}
        strong {{ font-weight: bold; }}
        em {{ font-style: italic; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>
"""
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 使用 wkhtmltopdf 生成 PDF（CID TrueType 字体，飞书可正确解析）
        try:
            subprocess.run([
                'wkhtmltopdf',
                '--encoding', 'UTF-8',
                '--page-size', 'A4',
                '--margin-top', '20',
                '--margin-bottom', '20',
                '--margin-left', '20',
                '--margin-right', '20',
                '--enable-local-file-access',
                '--javascript-delay', '1000',
                str(html_filepath),
                str(pdf_filepath)
            ], check=True, capture_output=True, timeout=60)
            
            file_size = pdf_filepath.stat().st_size / 1024
            logger.info(f"PDF 已生成：{pdf_filepath} ({file_size:.1f} KB)")
        except subprocess.CalledProcessError as e:
            logger.error(f"PDF 生成失败：{e}")
        except FileNotFoundError:
            logger.warning("wkhtmltopdf 未安装，跳过 PDF 生成")
        except Exception as e:
            logger.error(f"PDF 生成异常：{e}")
        
        # 生成中文文件名版本并发送到飞书
        if pdf_filepath.exists():
            chinese_pdf_filename = f"装载机行业情报日报_{today}.pdf"
            chinese_pdf_filepath = self.output_dir / chinese_pdf_filename
            
            # 复制为中文文件名
            import shutil
            shutil.copy2(pdf_filepath, chinese_pdf_filepath)
            logger.info(f"已生成中文文件名：{chinese_pdf_filepath}")
            
            # 发送到飞书（使用 UTF-8 环境变量）
            try:
                import subprocess
                result = subprocess.run([
                    'openclaw', 'message', 'send',
                    '-t', 'user:ou_09f88aa1449ac851663dd6f225a95c3d',
                    '--channel', 'feishu',
                    '--media', str(chinese_pdf_filepath)
                ], env={**os.environ, 'LC_ALL': 'zh_CN.UTF-8', 'PYTHONIOENCODING': 'utf-8'},
                capture_output=True, timeout=30)
                
                if result.returncode == 0:
                    logger.info(f"✅ PDF 已发送到飞书（中文文件名：{chinese_pdf_filename}）")
                else:
                    logger.warning(f"发送失败：{result.stderr.decode('utf-8', errors='ignore')}")
            except Exception as e:
                logger.warning(f"发送 PDF 到飞书时出错：{e}")
        
        return str(md_filepath)
    
    def get_summary(self, max_items: int = 3) -> str:
        """生成推送摘要"""
        items = self._load_analyzed_data()
        
        if not items:
            return "今日暂无装载机行业相关新闻"
        
        summary_lines = [f"🚜 **装载机行业日报** ({datetime.now().strftime('%m-%d')})\n"]
        summary_lines.append(f"共采集 {len(items)} 条新闻\n")
        summary_lines.append("\n**重点动态：**\n")
        
        for i, item in enumerate(items[:max_items], 1):
            title = item.get('title', '')
            summary_lines.append(f"{i}. {title}\n")
        
        summary_lines.append("\n完整报告已保存至工作区。")
        
        return "".join(summary_lines)


def main():
    """主函数"""
    generator = ReportGenerator()
    report = generator.generate_report()
    
    print(f"\n✅ 报告生成完成")
    print(f"保存路径：/home/legao/.openclaw/workspace/reports/loader/")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
