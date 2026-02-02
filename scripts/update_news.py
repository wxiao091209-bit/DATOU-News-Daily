#!/usr/bin/env python3
import os
import requests
import re
import random
from datetime import datetime
import json
import html

# NewsAPI 配置
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
API_URL = 'https://newsapi.org/v2/everything'

def fetch_news():
    """从 NewsAPI 抓取中文 AI 新闻"""
    if not NEWS_API_KEY:
        print("Error: NEWS_API_KEY not found")
        return []
    
    # 搜索参数（中文 AI 相关）
    params = {
        'q': '人工智能 OR AI OR 大模型 OR ChatGPT OR OpenAI',
        'language': 'zh',
        'sortBy': 'publishedAt',
        'pageSize': 30,
        'apiKey': NEWS_API_KEY
    }
    
    try:
        print("Fetching news from NewsAPI (Chinese)...")
        response = requests.get(API_URL, params=params, timeout=30)
        data = response.json()
        
        if data.get('status') != 'ok':
            print(f"API Error: {data.get('message')}")
            return fetch_news_english()
        
        articles = data.get('articles', [])
        print(f"Fetched {len(articles)} articles")
        
        entries = []
        for article in articles:
            title = html.unescape(article.get('title', ''))
            description = html.unescape(article.get('description', '') or article.get('content', '')[:200])
            clean_desc = re.sub('<.*?>', '', description)
            
            if title and clean_desc:
                entries.append({
                    'title': title,
                    'summary': clean_desc[:200] + '...' if len(clean_desc) > 200 else clean_desc,
                    'link': article.get('url', ''),
                    'source': article.get('source', {}).get('name', 'NewsAPI'),
                })
        
        return entries
        
    except Exception as e:
        print(f"Error: {e}")
        return fetch_news_english()

def fetch_news_english():
    """备用：获取英文 AI 新闻"""
    try:
        params = {
            'q': 'artificial intelligence OR AI OR ChatGPT',
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': 20,
            'apiKey': NEWS_API_KEY
        }
        
        response = requests.get(API_URL, params=params, timeout=30)
        data = response.json()
        articles = data.get('articles', [])
        
        entries = []
        for article in articles:
            title = html.unescape(article.get('title', ''))
            description = html.unescape(article.get('description', '') or '')
            clean_desc = re.sub('<.*?>', '', description)
            
            if title:
                entries.append({
                    'title': title,
                    'summary': clean_desc[:200] + '...' if len(clean_desc) > 200 else clean_desc,
                    'link': article.get('url', ''),
                    'source': article.get('source', {}).get('name', 'NewsAPI'),
                })
        
        return entries
    except:
        return []

def categorize_and_generate(entries):
    """生成内容数据"""
    if not entries:
        return {
            'summaries': [[]],
            'categories': {}
        }
    
    random.shuffle(entries)
    
    # 前3条作为核心摘要
    top3 = entries[:3]
    summaries = []
    for item in top3:
        summaries.append({
            'text': item['summary'],
            'source': item['source'],
            'url': item['link']
        })
    
    # 分类关键词
    CATEGORY_KEYWORDS = {
        'bigModel': ['GPT', 'ChatGPT', 'OpenAI', 'Claude', 'Llama', '大模型', 'LLM', 'Gemini', '文心', '通义', 'Kimi'],
        'hardware': ['芯片', 'NVIDIA', 'GPU', '算力', '服务器', '推理', '训练', 'hardware', 'chip', 'robot', '机器人'],
        'global': ['出海', 'global', 'policy', '政策', 'regulation', '监管', 'EU', 'European', '美国', '中国'],
        'investment': ['融资', 'investment', 'funding', 'IPO', '估值', '独角兽', 'billion', 'million', '投资'],
        'industry': ['报告', 'report', '分析', '行业', 'study', 'research', 'Gartner', 'market'],
        'product': ['发布', 'launch', 'product', '应用', 'app', 'update', 'version', '新功能', '新品']
    }
    
    categories = {
        'bigModel': {'title': '大模型', 'desc': 'GPT-5、Claude 4、Gemini Ultra 等前沿大模型技术突破与商业化进展追踪', 'icon': 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z', 'articles': []},
        'hardware': {'title': 'AI 硬件', 'desc': '算力芯片、机器人、端侧设备、AI Phone 等硬件载体技术革新与产业链动向', 'icon': 'M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z', 'articles': []},
        'global': {'title': '出海动态', 'desc': '中国 AI 企业全球化布局、海外监管政策、跨境投融资与本地化战略分析', 'icon': 'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z', 'articles': []},
        'investment': {'title': '投融资', 'desc': '一级市场融资速递、独角兽估值变动、IPO 动态与资本风向解读', 'icon': 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z', 'articles': []},
        'industry': {'title': '产业观察', 'desc': '行业政策解读、竞争格局分析、技术趋势预测与商业模式演进研究', 'icon': 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4', 'articles': []},
        'product': {'title': '产品快讯', 'desc': 'AI 应用新品发布、功能更新、用户体验优化与市场化策略追踪报道', 'icon': 'M13 10V3L4 14h7v7l9-11h-7z', 'articles': []}
    }
    
    # 分配文章到分类
    for item in entries[3:]:
        text = (item['title'] + ' ' + item['summary']).lower()
        
        for cat_key, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword.lower() in text for keyword in keywords):
                categories[cat_key]['articles'].append({
                    'title': item['title'],
                    'summary': item['summary'],
                    'content': f"<p>{item['summary']}</p><p><a href='{item['link']}' target='_blank'>查看原文：{item['source']}</a></p>",
                    'readTime': f"{random.randint(3, 8)} 分钟",
                    'source': item['source'],
                    'sourceUrl': item['link']
                })
                break
    
    return {
        'summaries': [summaries],
        'categories': categories
    }

def update_html():
    """更新 HTML 文件"""
    content = categorize_and_generate(fetch_news())
    
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    new_json = json.dumps(content, ensure_ascii=False, indent=4)
    
    pattern = r'const contentDatabase = \{[\s\S]*?\};(?=\s*const START_DATE)'
    replacement = f'const contentDatabase = {new_json};'
    
    new_html = re.sub(pattern, replacement, html_content)
    
    if new_html == html_content:
        pattern2 = r'(const contentDatabase = )\{[\s\S]*?\}(;)'
        new_html = re.sub(pattern2, replacement, html_content)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_html)
    
    print(f"Updated at {datetime.now()}")

if __name__ == '__main__':
    update_html()
