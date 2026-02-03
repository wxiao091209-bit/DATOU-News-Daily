#!/usr/bin/env python3
import os
import re
import json
import html
import random
from datetime import datetime, timedelta
from urllib.parse import urljoin
import feedparser
import requests
from bs4 import BeautifulSoup

# 简单AI术语翻译字典（常见标题关键词映射）
TRANSLATION_MAP = {
    # 公司/产品
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "claude": "Claude",
    "gpt": "GPT",
    "gemini": "Gemini",
    "google": "谷歌",
    "meta": "Meta",
    "nvidia": "英伟达",
    "microsoft": "微软",
    "amazon": "亚马逊",
    
    # 技术术语
    "artificial intelligence": "人工智能",
    "machine learning": "机器学习",
    "large language model": "大语言模型",
    "llm": "大模型",
    "agent": "智能体",
    "ai agent": "AI智能体",
    "coding": "编程",
    "app": "应用",
    "model": "模型",
    "training": "训练",
    "inference": "推理",
    "chip": "芯片",
    "gpu": "GPU",
    "robotics": "机器人",
    "funding": "融资",
    "investment": "投资",
    "partnership": "合作",
    "announcing": "发布",
    "introducing": "推出",
    "new": "全新",
    "update": "更新",
    "release": "发布",
    "launch": "上线",
    "available": "可用",
    "enterprise": "企业级",
    "research": "研究",
    "paper": "论文",
    "benchmark": "基准测试",
    "performance": "性能",
    "multimodal": "多模态",
    "reasoning": "推理能力",
    "alignment": "对齐",
    "safety": "安全",
    "open source": "开源",
}

def translate_title(title):
    """简单翻译标题（关键词替换+格式优化）"""
    if not title:
        return "无标题"
    
    # 如果已经是中文为主，直接返回
    chinese_chars = len([c for c in title if '\u4e00' <= c <= '\u9fff'])
    if chinese_chars > len(title) * 0.3:
        return title
    
    # 英文标题翻译处理
    translated = title.lower()
    
    # 按长度降序替换（避免短词覆盖长词）
    for en, cn in sorted(TRANSLATION_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        translated = translated.replace(en.lower(), cn)
    
    # 首字母大写
    translated = translated.capitalize()
    
    # 如果翻译后还是太像英文，添加前缀提示
    if len([c for c in translated if '\u4e00' <= c <= '\u9fff']) < 3:
        return f"[海外] {title}"
    
    return translated

def translate_summary(text, source):
    """翻译摘要，保留关键信息"""
    if not text:
        return f"来自{source}的最新动态..."
    
    # 清理HTML
    clean = re.sub(r'<[^>]+>', '', text)
    
    # 如果已有中文，直接截断
    chinese_chars = len([c for c in clean if '\u4e00' <= c <= '\u9fff'])
    if chinese_chars > len(clean) * 0.2:
        return clean[:120] + "..." if len(clean) > 120 else clean
    
    # 翻译关键术语
    translated = clean.lower()
    for en, cn in sorted(TRANSLATION_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        translated = translated.replace(en.lower(), cn)
    
    # 添加来源提示
    result = translated.capitalize()
    if len(result) > 150:
        result = result[:150] + "..."
    
    return result

# 一手信源配置（官方RSS源，去除所有港澳台站点）
SOURCES = {
    "bigModel": [  # 大模型
        {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "type": "rss"},
        {"name": "Anthropic News", "url": "https://www.anthropic.com/news/rss.xml", "type": "rss"},
        {"name": "Google DeepMind", "url": "https://deepmind.google/discover/feed/", "type": "rss"},
        {"name": "Meta AI Blog", "url": "https://ai.meta.com/blog/rss/", "type": "rss"},
        {"name": "Hugging Face Papers", "url": "https://huggingface.co/api/papers?limit=15", "type": "hf_api"},
        {"name": "Mistral AI", "url": "https://mistral.ai/news", "type": "html", "selector": "article h2 a, article h3 a"},
        {"name": "xAI", "url": "https://x.ai/news", "type": "html", "selector": "a[href*='/news/']"},
    ],
    "hardware": [  # AI硬件
        {"name": "NVIDIA Blog AI", "url": "https://blogs.nvidia.com/blog/category/artificial-intelligence/feed/", "type": "rss"},
        {"name": "NVIDIA Blog Robotics", "url": "https://blogs.nvidia.com/blog/category/robotics/feed/", "type": "rss"},
    ],
    "investment": [  # 投融资
        {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "type": "rss"},
        {"name": "TechCrunch Funding", "url": "https://techcrunch.com/category/venture/feed/", "type": "rss"},
        {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "type": "rss"},
    ],
    "global": [  # 出海动态
        {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "type": "rss"},
        {"name": "The Verge AI", "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "type": "rss"},
    ],
    "industry": [  # 产业观察
        {"name": "Google AI Blog", "url": "https://ai.googleblog.com/feeds/posts/default", "type": "rss"},
        {"name": "Microsoft AI Blog", "url": "https://blogs.microsoft.com/ai/feed/", "type": "rss"},
    ],
    "product": [  # 产品快讯
        {"name": "OpenAI Product", "url": "https://openai.com/blog/rss.xml", "type": "rss"},
        {"name": "Anthropic Product", "url": "https://www.anthropic.com/news/rss.xml", "type": "rss"},
    ]
}

# 分类元数据（与现有HTML结构完全匹配）
CATEGORY_META = {
    "bigModel": {
        "title": "大模型",
        "desc": "GPT-5、Claude 4、Gemini Ultra 等前沿大模型技术突破与商业化进展追踪",
        "icon": "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
    },
    "hardware": {
        "title": "AI 硬件",
        "desc": "算力芯片、机器人、端侧设备、AI Phone 等硬件载体技术革新与产业链动向",
        "icon": "M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
    },
    "global": {
        "title": "出海动态",
        "desc": "中国 AI 企业全球化布局、海外监管政策、跨境投融资与本地化战略分析",
        "icon": "M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
    },
    "investment": {
        "title": "投融资",
        "desc": "一级市场融资速递、独角兽估值变动、IPO 动态与资本风向解读",
        "icon": "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
    },
    "industry": {
        "title": "产业观察",
        "desc": "行业政策解读、竞争格局分析、技术趋势预测与商业模式演进研究",
        "icon": "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
    },
    "product": {
        "title": "产品快讯",
        "desc": "AI 应用新品发布、功能更新、用户体验优化与市场化策略追踪报道",
        "icon": "M13 10V3L4 14h7v7l9-11h-7z"
    }
}

def fetch_rss(url, name):
    """抓取RSS feed"""
    try:
        print(f"Fetching: {name}")
        feed = feedparser.parse(url)
        entries = []
        for entry in feed.entries[:8]:
            published = entry.get('published', entry.get('updated', ''))
            summary = entry.get('summary', entry.get('description', ''))
            clean_summary = re.sub(r'<[^>]+>', '', summary)
            
            entries.append({
                "title": translate_title(entry.title),  # 翻译标题
                "link": entry.link,
                "date": published,
                "summary": translate_summary(clean_summary, name),  # 翻译摘要
                "source": name,
                "content": f"<p>{translate_summary(clean_summary, name)}</p><p><a href='{entry.link}' target='_blank'>查看原文：{name}</a></p>"
            })
        return entries
    except Exception as e:
        print(f"Error {name}: {e}")
        return []

def fetch_hf_papers():
    """抓取Hugging Face最新论文"""
    try:
        print("Fetching: Hugging Face Papers")
        resp = requests.get("https://huggingface.co/api/papers?limit=15", timeout=15)
        papers = resp.json()
        entries = []
        for p in papers:
            paper_id = p.get('id', '')
            title = p.get('title', '')
            summary = p.get('summary', '')
            
            if title and len(title) > 10:
                entries.append({
                    "title": f"[论文] {translate_title(title)}",
                    "link": f"https://huggingface.co/papers/{paper_id}",
                    "date": p.get('publishedAt', ''),
                    "summary": translate_summary(summary, "Hugging Face"),
                    "source": "Hugging Face",
                    "content": f"<p>论文摘要：{translate_summary(summary, 'Hugging Face')}</p><p><a href='https://huggingface.co/papers/{paper_id}' target='_blank'>查看论文详情</a></p>"
                })
        return entries
    except Exception as e:
        print(f"Error HF: {e}")
        return []

def fetch_html_list(url, name, selector):
    """简单的HTML列表抓取"""
    try:
        print(f"Fetching: {name}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        entries = []
        
        links = soup.select(selector)[:5]
        for link in links:
            href = link.get('href', '')
            if href and not href.startswith('http'):
                href = urljoin(url, href)
            title = link.get_text(strip=True)
            if title and 15 < len(title) < 200:
                entries.append({
                    "title": translate_title(title),
                    "link": href,
                    "date": datetime.now().isoformat(),
                    "summary": f"{name}最新动态...",
                    "source": name,
                    "content": f"<p>{name}发布了最新更新。</p><p><a href='{href}' target='_blank'>查看原文：{name}</a></p>"
                })
        return entries
    except Exception as e:
        print(f"Error {name}: {e}")
        return []

def estimate_read_time(text):
    """估算阅读时间"""
    words = len(text) / 2
    minutes = max(1, round(words / 300))
    return f"{minutes} 分钟"

def build_content_database():
    """构建内容数据库"""
    database = {"summaries": [], "categories": {}}  # 确保初始化为空字典
    
    all_articles = []
    category_articles = {key: [] for key in CATEGORY_META.keys()}
    
    for cat_key, sources in SOURCES.items():
        print(f"\nProcessing: {cat_key}")
        for source in sources:
            try:
                if source['type'] == 'rss':
                    entries = fetch_rss(source['url'], source['name'])
                elif source['type'] == 'hf_api':
                    entries = fetch_hf_papers()
                elif source['type'] == 'html':
                    entries = fetch_html_list(source['url'], source['name'], source['selector'])
                else:
                    entries = []
                
                for entry in entries:
                    entry['readTime'] = estimate_read_time(entry.get('summary', ''))
                    final_cat = cat_key
                    
                    # 智能分类
                    title_lower = entry['title'].lower()
                    if any(k in title_lower for k in ['融资', '投资', 'funding', 'investment', '$', 'million', '估值', 'billion']):
                        final_cat = 'investment'
                    elif any(k in title_lower for k in ['发布', '推出', '上线', 'launch', 'release', 'product', 'update', 'available']):
                        if final_cat not in ['product', 'bigModel']:
                            final_cat = 'product'
                    
                    if final_cat in category_articles:
                        category_articles[final_cat].append(entry)
                    all_articles.append(entry)
                    
            except Exception as e:
                print(f"Error: {e}")
    
    # 填充分类数据 - 确保每个分类都有数据（即使为空数组）
    for cat_key, meta in CATEGORY_META.items():
        articles = category_articles.get(cat_key, [])
        # 去重
        seen = set()
        unique = []
        for a in articles:
            if a['link'] not in seen:
                seen.add(a['link'])
                unique.append(a)
        
        database["categories"][cat_key] = {
            "title": meta["title"],
            "desc": meta["desc"],
            "icon": meta["icon"],
            "articles": unique[:8]  # 最多8条
        }
        print(f"{cat_key}: {len(unique[:8])} articles")
    
    # 生成今日核心摘要 - 确保多样性（不要全是OpenAI）
    # 按来源分组，每个来源取1条，确保多样性
    source_groups = {}
    for a in all_articles:
        src = a['source']
        if src not in source_groups:
            source_groups[src] = []
        source_groups[src].append(a)
    
    # 优先取不同来源的Top文章
    summaries = []
    priority_sources = ['OpenAI Blog', 'Anthropic News', 'Google DeepMind', 'Meta AI Blog', 'Hugging Face', 'NVIDIA Blog AI']
    
    for src in priority_sources:
        if src in source_groups and source_groups[src]:
            summaries.append(source_groups[src][0])
        if len(summaries) >= 3:
            break
    
    # 如果不够3条，补充其他来源
    if len(summaries) < 3:
        for src, articles in source_groups.items():
            if articles and articles[0] not in summaries:
                summaries.append(articles[0])
            if len(summaries) >= 3:
                break
    
    # 格式化摘要
    formatted = []
    for article in summaries[:3]:
        clean = re.sub(r'<[^>]+>', '', article.get('summary', ''))
        if len(clean) > 150:
            clean = clean[:150] + "..."
        
        formatted.append({
            "text": clean or article['title'],
            "source": article['source'],
            "url": article['link']
        })
    
    database["summaries"] = [formatted]  # 保持数组的数组结构
    
    # 关键：确保categories不为空
    if not database["categories"]:
        print("WARNING: categories is empty!")
        # 填充空结构避免报错
        for cat_key, meta in CATEGORY_META.items():
            database["categories"][cat_key] = {
                "title": meta["title"],
                "desc": meta["desc"],
                "icon": meta["icon"],
                "articles": []
            }
    
    return database

def update_html_file():
    """更新HTML文件"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        new_db = build_content_database()
        
        # 验证数据结构
        print(f"\nDatabase structure check:")
        print(f"- summaries count: {len(new_db['summaries'])}")
        print(f"- summaries[0] count: {len(new_db['summaries'][0]) if new_db['summaries'] else 0}")
        print(f"- categories count: {len(new_db['categories'])}")
        for cat, data in new_db['categories'].items():
            print(f"  - {cat}: {len(data.get('articles', []))} articles")
        
        json_str = json.dumps(new_db, ensure_ascii=False, indent=8)
        
        # 替换contentDatabase
        pattern = r'const contentDatabase = \{.*?\};'
        replacement = f'const contentDatabase = {json_str};'
        new_html = re.sub(pattern, replacement, html_content, flags=re.DOTALL)
        
        if new_html == html_content:
            print("Warning: Using line-based replacement...")
            lines = html_content.split('\n')
            for i, line in enumerate(lines):
                if 'const contentDatabase = {' in line:
                    start = i
                    brace = 1
                    j = i + 1
                    while j < len(lines) and brace > 0:
                        brace += lines[j].count('{') - lines[j].count('}')
                        if brace == 0:
                            new_lines = lines[:start] + [f'const contentDatabase = {json_str};'] + lines[j+1:]
                            new_html = '\n'.join(new_lines)
                            break
                        j += 1
                    break
        
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(new_html)
        
        total = sum(len(c.get('articles', [])) for c in new_db['categories'].values())
        print(f"\n✅ Success! Total articles: {total}, Summaries: {len(new_db['summaries'][0]) if new_db['summaries'] else 0}")
        
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == '__main__':
    print("🤖 DATOU AI News - Official Sources + Chinese Translation")
    print("=" * 50)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Sources: OpenAI, Anthropic, DeepMind, Meta, NVIDIA, HF")
    print("=" * 50)
    update_html_file()
