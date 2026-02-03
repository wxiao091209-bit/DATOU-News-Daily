#!/usr/bin/env python3
import os
import re
import json
import html
from datetime import datetime, timedelta
from urllib.parse import urljoin
import feedparser
import requests
from bs4 import BeautifulSoup

# 保底数据 - 当RSS抓取失败时自动使用（防止页面空白）
FALLBACK_DATA = {
    "summaries": [[
        {
            "text": "OpenAI发布新一代模型更新，提升推理能力与多模态理解，企业级API同步优化。",
            "source": "OpenAI Blog",
            "url": "https://openai.com/blog"
        },
        {
            "text": "Anthropic推出Claude新功能，支持更长上下文窗口与代码生成能力。",
            "source": "Anthropic News", 
            "url": "https://www.anthropic.com/news"
        },
        {
            "text": "NVIDIA发布新一代AI芯片架构，推理性能提升显著，云服务商已同步上线。",
            "source": "NVIDIA Blog",
            "url": "https://blogs.nvidia.com"
        }
    ]],
    "categories": {
        "bigModel": {
            "title": "大模型",
            "desc": "GPT-5、Claude 4、Gemini Ultra 等前沿大模型技术突破与商业化进展追踪",
            "icon": "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
            "articles": [
                {"title": "OpenAI GPT-5最新技术进展", "link": "https://openai.com/blog", "date": "", "summary": "OpenAI发布最新模型能力更新", "source": "OpenAI Blog", "readTime": "5 分钟", "content": "<p>OpenAI最新动态</p><p><a href='https://openai.com/blog' target='_blank'>查看原文</a></p>"},
                {"title": "Anthropic Claude 4能力升级", "link": "https://www.anthropic.com/news", "date": "", "summary": "Claude系列模型新功能发布", "source": "Anthropic News", "readTime": "4 分钟", "content": "<p>Anthropic最新动态</p><p><a href='https://www.anthropic.com/news' target='_blank'>查看原文</a></p>"}
            ]
        },
        "hardware": {
            "title": "AI 硬件",
            "desc": "算力芯片、机器人、端侧设备、AI Phone 等硬件载体技术革新与产业链动向",
            "icon": "M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z",
            "articles": [
                {"title": "NVIDIA新一代AI芯片发布", "link": "https://blogs.nvidia.com", "date": "", "summary": "GPU架构升级，推理性能提升", "source": "NVIDIA Blog", "readTime": "6 分钟", "content": "<p>NVIDIA最新硬件动态</p><p><a href='https://blogs.nvidia.com' target='_blank'>查看原文</a></p>"}
            ]
        },
        "global": {
            "title": "出海动态",
            "desc": "中国 AI 企业全球化布局、海外监管政策、跨境投融资与本地化战略分析",
            "icon": "M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
            "articles": []
        },
        "investment": {
            "title": "投融资",
            "desc": "一级市场融资速递、独角兽估值变动、IPO 动态与资本风向解读",
            "icon": "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
            "articles": []
        },
        "industry": {
            "title": "产业观察",
            "desc": "行业政策解读、竞争格局分析、技术趋势预测与商业模式演进研究",
            "icon": "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
            "articles": []
        },
        "product": {
            "title": "产品快讯",
            "desc": "AI 应用新品发布、功能更新、用户体验优化与市场化策略追踪报道",
            "icon": "M13 10V3L4 14h7v7l9-11h-7z",
            "articles": []
        }
    }
}

# 主要信源配置（只保留稳定的英文源）
SOURCES = [
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "cat": "bigModel"},
    {"name": "Anthropic News", "url": "https://www.anthropic.com/news/rss.xml", "cat": "bigModel"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/discover/feed/", "cat": "bigModel"},
    {"name": "Meta AI Blog", "url": "https://ai.meta.com/blog/rss/", "cat": "bigModel"},
    {"name": "NVIDIA Blog", "url": "https://blogs.nvidia.com/blog/category/artificial-intelligence/feed/", "cat": "hardware"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "cat": "investment"},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "cat": "industry"},
]

def fetch_rss_simple(url, name):
    """简化版RSS抓取"""
    try:
        print(f"  抓取: {name}...")
        feed = feedparser.parse(url)
        
        if not feed.entries:
            print(f"    ⚠️ {name} 无数据")
            return []
        
        entries = []
        for entry in feed.entries[:3]:
            summary = entry.get('summary', entry.get('description', ''))
            clean_summary = re.sub(r'<[^>]+>', '', summary)
            
            entries.append({
                "title": entry.title,
                "link": entry.link,
                "date": entry.get('published', ''),
                "summary": clean_summary[:150] + "..." if len(clean_summary) > 150 else clean_summary,
                "source": name,
                "readTime": "5 分钟",
                "content": f"<p>{clean_summary[:200]}</p><p><a href='{entry.link}' target='_blank'>查看原文：{name}</a></p>"
            })
        
        print(f"    ✓ {name}: {len(entries)} 条")
        return entries
        
    except Exception as e:
        print(f"    ✗ {name}: 失败")
        return []

def build_database():
    """构建数据库"""
    print("\n开始抓取数据...")
    
    # 初始化数据结构
    database = {
        "summaries": [[]],
        "categories": {
            "bigModel": {"title": "大模型", "desc": "GPT-5、Claude 4、Gemini Ultra 等前沿大模型技术突破与商业化进展追踪", "icon": "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z", "articles": []},
            "hardware": {"title": "AI 硬件", "desc": "算力芯片、机器人、端侧设备、AI Phone 等硬件载体技术革新与产业链动向", "icon": "M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z", "articles": []},
            "global": {"title": "出海动态", "desc": "中国 AI 企业全球化布局、海外监管政策、跨境投融资与本地化战略分析", "icon": "M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z", "articles": []},
            "investment": {"title": "投融资", "desc": "一级市场融资速递、独角兽估值变动、IPO 动态与资本风向解读", "icon": "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z", "articles": []},
            "industry": {"title": "产业观察", "desc": "行业政策解读、竞争格局分析、技术趋势预测与商业模式演进研究", "icon": "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4", "articles": []},
            "product": {"title": "产品快讯", "desc": "AI 应用新品发布、功能更新、用户体验优化与市场化策略追踪报道", "icon": "M13 10V3L4 14h7v7l9-11h-7z", "articles": []},
        }
    }
    
    all_articles = []
    
    # 抓取各源数据
    for source in SOURCES:
        entries = fetch_rss_simple(source['url'], source['name'])
        if entries:
            cat = source['cat']
            database['categories'][cat]['articles'].extend(entries)
            all_articles.extend(entries)
    
    # 如果没有抓到任何数据，使用保底数据
    if not all_articles:
        print("\n⚠️ 所有RSS源失败，使用保底数据")
        return FALLBACK_DATA
    
    # 去重
    for cat_key in database['categories']:
        articles = database['categories'][cat_key]['articles']
        seen = set()
        unique = []
        for a in articles:
            if a['link'] not in seen:
                seen.add(a['link'])
                unique.append(a)
        database['categories'][cat_key]['articles'] = unique[:6]
    
    # 生成摘要
    summaries = []
    used_sources = set()
    for article in all_articles:
        if article['source'] not in used_sources:
            summaries.append({
                "text": article['summary'][:120] + "..." if len(article['summary']) > 120 else article['summary'],
                "source": article['source'],
                "url": article['link']
            })
            used_sources.add(article['source'])
        if len(summaries) >= 3:
            break
    
    database['summaries'] = [summaries]
    
    total = sum(len(v['articles']) for v in database['categories'].values())
    print(f"\n✓ 总计: {total} 篇文章")
    
    return database

def update_html():
    """更新HTML文件"""
    try:
        print("\n正在更新 index.html...")
        
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        new_db = build_database()
        json_str = json.dumps(new_db, ensure_ascii=False, indent=8)
        
        # 替换 contentDatabase
        pattern = r'const contentDatabase\s*=\s*\{[\s\S]*?\};'
        replacement = f'const contentDatabase = {json_str};'
        new_html = re.sub(pattern, replacement, html_content)
        
        # 如果正则失败，使用字符串查找
        if new_html == html_content:
            start_marker = 'const contentDatabase = {'
            start_idx = html_content.find(start_marker)
            if start_idx != -1:
                brace_count = 1
                i = start_idx + len(start_marker)
                while i < len(html_content) and brace_count > 0:
                    if html_content[i] == '{':
                        brace_count += 1
                    elif html_content[i] == '}':
                        brace_count -= 1
                    i += 1
                
                if brace_count == 0:
                    new_html = html_content[:start_idx] + f'const contentDatabase = {json_str};' + html_content[i:]
        
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(new_html)
        
        print("✓ 更新成功")
        return True
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False

if __name__ == '__main__':
    print("🤖 DATOU AI News")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    update_html()
