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

def force_translate(text):
    """强制翻译英文标题/摘要为中文"""
    if not text:
        return "暂无内容"
    
    # 如果已经有足够多中文，直接返回
    chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
    if chinese_chars > len(text) * 0.3:
        return text
    
    # 英中映射表（按长度降序，避免短词覆盖）
    translations = [
        # 公司和产品
        ("OpenAI", "OpenAI"),
        ("Anthropic", "Anthropic"),
        ("Claude", "Claude"),
        ("GPT-5", "GPT-5"),
        ("GPT-4", "GPT-4"),
        ("GPT", "GPT"),
        ("Gemini", "Gemini"),
        ("Google", "谷歌"),
        ("Meta", "Meta"),
        ("NVIDIA", "英伟达"),
        ("Microsoft", "微软"),
        ("Amazon", "亚马逊"),
        ("Snowflake", "Snowflake"),
        ("xAI", "xAI"),
        ("Mistral", "Mistral"),
        ("Hugging Face", "Hugging Face"),
        
        # 技术和产品
        ("Codex", "Codex"),
        ("ChatGPT", "ChatGPT"),
        ("AI agent", "AI智能体"),
        ("AI agents", "AI智能体"),
        ("artificial intelligence", "人工智能"),
        ("machine learning", "机器学习"),
        ("large language model", "大语言模型"),
        ("LLM", "大模型"),
        ("multimodal", "多模态"),
        ("infrastructure", "基础设施"),
        ("enterprise", "企业级"),
        ("dataset", "数据集"),
        ("training", "训练"),
        ("inference", "推理"),
        ("chip", "芯片"),
        ("GPU", "GPU"),
        ("robotics", "机器人技术"),
        
        # 动作和商业
        ("partnership", "合作"),
        ("partner", "合作"),
        ("agreement", "协议"),
        ("investment", "投资"),
        ("funding", "融资"),
        ("billion", "十亿美元"),
        ("million", "百万美元"),
        ("launch", "发布"),
        ("introducing", "推出"),
        ("announce", "宣布"),
        ("release", "发布"),
        ("update", "更新"),
        ("available", "上线"),
        ("built", "构建"),
        ("bring", "引入"),
        
        # 描述词
        ("frontier", "前沿"),
        ("intelligence", "智能"),
        ("command center", "指挥中心"),
        ("software development", "软件开发"),
        ("multiple", "多"),
        ("parallel", "并行"),
        ("workflows", "工作流"),
        ("long-running", "长时间运行"),
        ("reliable", "可靠的"),
        ("insights", "洞察"),
        ("reason", "推理"),
        ("memory", "记忆"),
        ("massive", "海量"),
    ]
    
    # 翻译处理
    result = text
    for en, cn in sorted(translations, key=lambda x: len(x[0]), reverse=True):
        result = re.sub(r'\b' + re.escape(en) + r'\b', cn, result, flags=re.IGNORECASE)
    
    # 清理多余空格
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result

# 一手信源配置
SOURCES = {
    "bigModel": [
        {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "type": "rss"},
        {"name": "Anthropic News", "url": "https://www.anthropic.com/news/rss.xml", "type": "rss"},
        {"name": "Google DeepMind", "url": "https://deepmind.google/discover/feed/", "type": "rss"},
        {"name": "Meta AI Blog", "url": "https://ai.meta.com/blog/rss/", "type": "rss"},
        {"name": "Hugging Face Papers", "url": "https://huggingface.co/api/papers?limit=15", "type": "hf_api"},
        {"name": "Mistral AI", "url": "https://mistral.ai/news", "type": "html", "selector": "article h2 a, article h3 a"},
        {"name": "xAI", "url": "https://x.ai/news", "type": "html", "selector": "a[href*='/news/']"},
    ],
    "hardware": [
        {"name": "NVIDIA Blog AI", "url": "https://blogs.nvidia.com/blog/category/artificial-intelligence/feed/", "type": "rss"},
        {"name": "NVIDIA Robotics", "url": "https://blogs.nvidia.com/blog/category/robotics/feed/", "type": "rss"},
    ],
    "investment": [
        {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "type": "rss"},
        {"name": "TechCrunch Funding", "url": "https://techcrunch.com/category/venture/feed/", "type": "rss"},
    ],
    "global": [
        {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "type": "rss"},
        {"name": "The Verge AI", "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "type": "rss"},
    ],
    "industry": [
        {"name": "Google AI Blog", "url": "https://ai.googleblog.com/feeds/posts/default", "type": "rss"},
        {"name": "Microsoft AI", "url": "https://blogs.microsoft.com/ai/feed/", "type": "rss"},
    ],
    "product": [
        {"name": "OpenAI Product", "url": "https://openai.com/blog/rss.xml", "type": "rss"},
        {"name": "Anthropic Product", "url": "https://www.anthropic.com/news/rss.xml", "type": "rss"},
    ]
}

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
    """抓取RSS"""
    try:
        print(f"Fetching RSS: {name}")
        feed = feedparser.parse(url)
        entries = []
        for entry in feed.entries[:5]:
            summary = entry.get('summary', entry.get('description', ''))
            clean_summary = re.sub(r'<[^>]+>', '', summary)
            
            # 强制翻译
            title_cn = force_translate(entry.title)
            summary_cn = force_translate(clean_summary[:200])
            
            entries.append({
                "title": title_cn,
                "link": entry.link,
                "date": entry.get('published', ''),
                "summary": summary_cn if summary_cn else title_cn,
                "source": name,
                "content": f"<p>{summary_cn}</p><p><a href='{entry.link}' target='_blank'>查看原文：{name}</a></p>"
            })
        print(f"  ✓ {name}: {len(entries)} articles")
        return entries
    except Exception as e:
        print(f"  ✗ Error {name}: {e}")
        return []

def fetch_hf_papers():
    """抓取Hugging Face论文"""
    try:
        print("Fetching: Hugging Face Papers")
        resp = requests.get("https://huggingface.co/api/papers?limit=10", timeout=15)
        papers = resp.json()
        entries = []
        for p in papers:
            title = p.get('title', '')
            summary = p.get('summary', '')
            paper_id = p.get('id', '')
            
            if title:
                entries.append({
                    "title": f"[论文] {force_translate(title)}",
                    "link": f"https://huggingface.co/papers/{paper_id}",
                    "date": p.get('publishedAt', ''),
                    "summary": force_translate(summary[:200]) if summary else "最新AI研究论文",
                    "source": "Hugging Face",
                    "content": f"<p>{force_translate(summary[:200])}</p><p><a href='https://huggingface.co/papers/{paper_id}' target='_blank'>查看论文</a></p>"
                })
        print(f"  ✓ Hugging Face: {len(entries)} papers")
        return entries
    except Exception as e:
        print(f"  ✗ Error HF: {e}")
        return []

def fetch_html_list(url, name, selector):
    """抓取HTML列表"""
    try:
        print(f"Fetching HTML: {name}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        entries = []
        
        links = soup.select(selector)[:3]
        for link in links:
            href = link.get('href', '')
            if href and not href.startswith('http'):
                href = urljoin(url, href)
            title = link.get_text(strip=True)
            if title and 10 < len(title) < 150:
                entries.append({
                    "title": force_translate(title),
                    "link": href,
                    "date": datetime.now().isoformat(),
                    "summary": f"{name}最新动态",
                    "source": name,
                    "content": f"<p>{name}发布更新</p><p><a href='{href}' target='_blank'>查看原文</a></p>"
                })
        print(f"  ✓ {name}: {len(entries)} articles")
        return entries
    except Exception as e:
        print(f"  ✗ Error {name}: {e}")
        return []

def estimate_read_time(text):
    words = len(text) / 2
    minutes = max(1, round(words / 300))
    return f"{minutes} 分钟"

def build_content_database():
    """构建数据库 - 强制多样性"""
    print("\n" + "="*50)
    print("开始抓取数据...")
    print("="*50)
    
    database = {"summaries": [[]], "categories": {}}
    all_articles_by_source = {}  # 按来源分组
    
    # 抓取所有数据
    for cat_key, sources in SOURCES.items():
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
                
                # 按来源存储，用于后续多样性选择
                if entries:
                    all_articles_by_source[source['name']] = entries
                
                # 同时按分类存储
                if cat_key not in database["categories"]:
                    database["categories"][cat_key] = []
                database["categories"][cat_key].extend(entries)
                
            except Exception as e:
                print(f"Error processing {source['name']}: {e}")
    
    # 处理分类数据 - 去重并限制数量
    for cat_key in CATEGORY_META.keys():
        articles = database["categories"].get(cat_key, [])
        seen = set()
        unique = []
        for a in articles:
            if a['link'] not in seen:
                seen.add(a['link'])
                a['readTime'] = estimate_read_time(a.get('summary', ''))
                unique.append(a)
        
        database["categories"][cat_key] = {
            "title": CATEGORY_META[cat_key]["title"],
            "desc": CATEGORY_META[cat_key]["desc"],
            "icon": CATEGORY_META[cat_key]["icon"],
            "articles": unique[:8]
        }
        print(f"\n{cat_key}: {len(unique[:8])} articles")
    
    # 强制多样性：从不同来源选摘要，每个来源最多1条
    print("\n" + "="*50)
    print("选择摘要（强制多样性）...")
    
    summaries = []
    sources_used = set()
    
    # 优先级顺序
    priority_order = [
        "OpenAI Blog", "Anthropic News", "Google DeepMind", "Meta AI Blog",
        "Hugging Face", "NVIDIA Blog AI", "TechCrunch AI", "MIT Tech Review AI"
    ]
    
    # 第一轮：每个优先级来源取1条
    for src_name in priority_order:
        if src_name in all_articles_by_source and all_articles_by_source[src_name]:
            article = all_articles_by_source[src_name][0]
            if article['link'] not in [s['url'] for s in summaries]:
                summaries.append({
                    "text": article['summary'][:120] + "..." if len(article['summary']) > 120 else article['summary'],
                    "source": article['source'],
                    "url": article['link']
                })
                sources_used.add(src_name)
                print(f"  ✓ 来自 {src_name}")
            if len(summaries) >= 3:
                break
    
    # 如果不够3条，从其他来源补充
    if len(summaries) < 3:
        for src_name, articles in all_articles_by_source.items():
            if src_name not in sources_used and articles:
                article = articles[0]
                summaries.append({
                    "text": article['summary'][:120] + "..." if len(article['summary']) > 120 else article['summary'],
                    "source": article['source'],
                    "url": article['link']
                })
                print(f"  ✓ 来自 {src_name} (补充)")
            if len(summaries) >= 3:
                break
    
    database["summaries"] = [summaries[:3]]
    
    print(f"\n✓ 摘要选择完成: {len(summaries)}条，来自 {len(sources_used)}个不同来源")
    for i, s in enumerate(summaries, 1):
        print(f"  {i}. [{s['source']}] {s['text'][:40]}...")
    
    return database

def update_html_file():
    """更新HTML"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        new_db = build_content_database()
        json_str = json.dumps(new_db, ensure_ascii=False, indent=8)
        
        # 替换contentDatabase
        pattern = r'const contentDatabase = \{.*?\};'
        replacement = f'const contentDatabase = {json_str};'
        new_html = re.sub(pattern, replacement, html_content, flags=re.DOTALL)
        
        if new_html == html_content:
            # 备选替换方案
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
        
        total = sum(len(c['articles']) for c in new_db['categories'].values())
        print(f"\n✅ 更新成功！总文章数: {total}, 摘要数: {len(new_db['summaries'][0])}")
        
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == '__main__':
    print("🤖 DATOU AI News - 强制中文翻译 + 来源多样性")
    print("=" * 50)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    update_html_file()
