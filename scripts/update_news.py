#!/usr/bin/env python3
import os
import requests
import re
import random
from datetime import datetime, timedelta
import json
import html

# NewsAPI 配置
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
API_URL = 'https://newsapi.org/v2/everything'

# 繁体/非科技媒体黑名单
BLOCKED_DOMAINS = [
    'tw.news.yahoo.com', 'yahoo.com.tw', 'technews.tw', 
    'techbang.com', 'hk01.com', 'setn.com', 'ettoday.net', 
    'chinatimes.com', 'udn.com', 'tvb.com', 'mingpao.com', 
    'scmp.com', 'bbc.com/zhongwen', 'cool3c.com', 'inside.com.tw'
]

# 内容质量黑名单
BLOCKED_KEYWORDS = [
    '假冒', '诈骗', '骗局', '色情', '娱乐', '八卦', 
    '出轨', '离婚', '恋爱', '综艺', '明星', '网红', '阿富汗'
]

def clean_text(text):
    """清理文本，移除换行符和多余空格"""
    if not text:
        return ""
    # 移除 HTML 标签
    text = re.sub('<.*?>', '', text)
    # 替换换行符、制表符、多余空格
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    text = ' '.join(text.split())  # 合并多个空格
    return text.strip()

def is_valid_news(title, desc, url):
    """检查新闻是否真正与AI相关"""
    if not title or not desc:
        return False
        
    text = (title + ' ' + desc).lower()
    url_lower = url.lower()
    
    # 排除黑名单域名
    for domain in BLOCKED_DOMAINS:
        if domain in url_lower:
            return False
    
    # 排除黑名单关键词
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text:
            return False
    
    # 确保包含AI关键词
    ai_keywords = [
        'ai', '人工智能', 'chatgpt', 'openai', '大模型', 'llm', 
        'gpt', 'claude', 'gemini', '文心', '通义', 'kimi',
        '算力', '芯片', 'nvidia', '英伟达', '微软', 'google', 
        'anthropic', '深度学习', '机器学习', '神经网络', 
        '算法', '自动驾驶', '机器人', '科技', 'copilot'
    ]
    
    title_lower = title.lower()
    has_ai_keyword = any(kw in title_lower for kw in ai_keywords)
    
    return has_ai_keyword

def fetch_news():
    """从 NewsAPI 抓取最近24小时的中文 AI 新闻"""
    if not NEWS_API_KEY:
        print("Error: NEWS_API_KEY not found")
        return []
    
    # 关键修复：获取最近24小时的新闻
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    
    search_queries = [
        '人工智能 AND (技术 OR 科技 OR 发布 OR 推出)',
        'ChatGPT OR OpenAI OR Claude OR Gemini',
        '大模型 OR LLM OR 算力 OR NVIDIA',
        'AI芯片 OR 自动驾驶 OR 机器人 OR 微软 Copilot'
    ]
    
    all_entries = []
    
    for query in search_queries:
        params = {
            'q': query,
            'language': 'zh',
            'sortBy': 'publishedAt',
            'pageSize': 20,
            'from': yesterday,  # 关键：只获取最近24小时
            'to': today,
            'apiKey': NEWS_API_KEY
        }
        
        try:
            print(f"Fetching: {query}...")
            response = requests.get(API_URL, params=params, timeout=30)
            data = response.json()
            
            if data.get('status') != 'ok':
                print(f"API Error: {data.get('message')}")
                continue
            
            articles = data.get('articles', [])
            print(f"  Found {len(articles)} articles")
            
            for article in articles:
                title = html.unescape(article.get('title', ''))
                description = html.unescape(article.get('description', '') or '')
                content = html.unescape(article.get('content', '') or '')
                
                # 优先使用 description，如果为空使用 content 前300字符
                full_text = description if description else content[:300]
                clean_desc = clean_text(full_text)
                
                url = article.get('url', '')
                published = article.get('publishedAt', '')[:10]  # YYYY-MM-DD
                
                # 严格过滤
                if title and clean_desc and is_valid_news(title, clean_desc, url):
                    all_entries.append({
                        'title': clean_text(title),
                        'summary': clean_desc[:200] + '...' if len(clean_desc) > 200 else clean_desc,
                        'link': url,
                        'source': article.get('source', {}).get('name', 'NewsAPI'),
                        'date': published
                    })
            
        except Exception as e:
            print(f"Error fetching query '{query}': {e}")
            continue
    
    # 去重
    seen = set()
    unique_entries = []
    for entry in all_entries:
        if entry['link'] not in seen:
            seen.add(entry['link'])
            unique_entries.append(entry)
    
    # 按日期排序，最新的在前
    unique_entries.sort(key=lambda x: x['date'], reverse=True)
    
    print(f"Total valid unique articles: {len(unique_entries)}")
    for e in unique_entries[:5]:
        print(f"  - [{e['date']}] {e['title'][:40]}...")
    
    return unique_entries[:20]

def categorize_and_generate(entries):
    """生成内容数据"""
    if not entries:
        print("Warning: No entries found!")
        # 返回空结构，避免页面报错
        return {
            'summaries': [[]],
            'categories': {}
        }
    
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
        'bigModel': ['GPT', 'ChatGPT', 'OpenAI', 'Claude', 'Llama', '大模型', 'LLM', 'Gemini', '文心', '通义', 'Kimi', 'DeepSeek'],
        'hardware': ['芯片', 'NVIDIA', 'GPU', '算力', '服务器', '推理', '训练', 'chip', 'robot', '机器人', '自动驾驶', 'tesla', '硬件'],
        'global': ['出海', 'global', 'policy', '政策', 'regulation', '监管', 'EU', 'European', '美国', '中国', '国际'],
        'investment': ['融资', 'investment', 'funding', 'IPO', '估值', '独角兽', 'billion', 'million', '投资', '收购', '并购'],
        'industry': ['报告', 'report', '分析', '行业', 'Gartner', 'market', '趋势', '研究', '市场', '产业'],
        'product': ['发布', 'launch', 'product', '应用', 'app', 'update', 'version', '新功能', '新品', '上线', 'copilot']
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
        assigned = False
        
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
                assigned = True
                break
        
        # 如果没匹配到任何分类，放入 product
        if not assigned:
            categories['product']['articles'].append({
                'title': item['title'],
                'summary': item['summary'],
                'content': f"<p>{item['summary']}</p><p><a href='{item['link']}' target='_blank'>查看原文：{item['source']}</a></p>",
                'readTime': f"{random.randint(3, 8)} 分钟",
                'source': item['source'],
                'sourceUrl': item['link']
            })
    
    return {
        'summaries': [summaries],
        'categories': categories
    }

def update_html():
    """更新 HTML 文件 - 使用可靠的标记替换法"""
    entries = fetch_news()
    content = categorize_and_generate(entries)
    
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 生成 JSON，确保 ASCII 编码正确处理中文
    new_json = json.dumps(content, ensure_ascii=False, separators=(',', ':'))
    
    # 关键修复：使用标记替换法，而不是复杂的正则
    # 在 HTML 中找到 contentDatabase 的开始和结束
    start_marker = 'const contentDatabase = '
    end_marker = ';\n\n        const START_DATE'
    
    start_idx = html_content.find(start_marker)
    end_idx = html_content.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("Error: Could not find contentDatabase markers")
        # 尝试备用方案
        alt_end = html_content.find(';\n\n        let currentCategory')
        if start_idx != -1 and alt_end != -1:
            end_idx = alt_end
        else:
            print("Failed to update HTML - markers not found")
            return
    
    # 构建新的 HTML
    new_html = (
        html_content[:start_idx + len(start_marker)] + 
        new_json + 
        html_content[end_idx:]
    )
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_html)
    
    print(f"✅ Successfully updated HTML with {len(entries)} articles at {datetime.now()}")

if __name__ == '__main__':
    update_html()
