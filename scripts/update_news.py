#!/usr/bin/env python3
import feedparser
import re
import random
from datetime import datetime
import json
import html

# RSS 源配置（免费、无需 API Key）
RSS_SOURCES = {
    'TechCrunch AI': 'https://techcrunch.com/category/artificial-intelligence/feed/',
    'The Verge AI': 'https://www.theverge.com/ai-artificial-intelligence/rss/index.xml',
    'Wired AI': 'https://www.wired.com/feed/tag/artificial-intelligence/latest/rss',
    'MIT Technology Review': 'https://www.technologyreview.com/feed/',
}

def fetch_news():
    """抓取新闻"""
    all_entries = []
    
    for source_name, url in RSS_SOURCES.items():
        try:
            print(f"Fetching {source_name}...")
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:  # 每个源取前5条
                # 清理 HTML 标签
                summary = entry.get('summary', entry.get('description', 'No summary'))
                # 去除 HTML 标签
                clean = re.sub('<.*?>', '', summary)
                clean = html.unescape(clean)  # 解码 HTML 实体
                
                all_entries.append({
                    'title': html.unescape(entry.get('title', 'No title')),
                    'summary': clean[:200] + '...' if len(clean) > 200 else clean,
                    'link': entry.get('link', ''),
                    'source': source_name,
                })
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")
    
    return all_entries

def categorize_and_generate(entries):
    """生成内容数据"""
    if not entries:
        print("No entries fetched, using fallback")
        return None
    
    print(f"Total entries fetched: {len(entries)}")
    
    # 打乱顺序，确保每天不一样
    random.shuffle(entries)
    
    # 取前3条作为核心摘要
    top3 = entries[:3]
    summaries = []
    for item in top3:
        summaries.append({
            'text': item['summary'][:150] + '...',
            'source': item['source'],
            'url': item['link']
        })
    
    # 剩余的分到6个分类（每个分类至少1条，最多3条）
    remaining = entries[3:]
    
    categories = {
        'bigModel': {'title': '大模型', 'articles': []},
        'hardware': {'title': 'AI 硬件', 'articles': []},
        'global': {'title': '出海动态', 'articles': []},
        'investment': {'title': '投融资', 'articles': []},
        'industry': {'title': '产业观察', 'articles': []},
        'product': {'title': '产品快讯', 'articles': []},
    }
    
    cat_keys = list(categories.keys())
    
    # 分配文章到各个分类
    for i, item in enumerate(remaining):
        cat_key = cat_keys[i % len(cat_keys)]
        categories[cat_key]['articles'].append({
            'title': item['title'],
            'summary': item['summary'],
            'content': f"<p>{item['summary']}</p><p><a href='{item['link']}' target='_blank' class='text-gold-400 hover:text-gold-300 underline'>查看原文</a></p>",
            'readTime': f"{random.randint(3, 8)} 分钟",
            'source': item['source'],
            'sourceUrl': item['link']
        })
    
    # 确保每个分类至少有1篇文章（如果没抓到就用默认的）
    for key in categories:
        if not categories[key]['articles']:
            categories[key]['articles'].append({
                'title': f'{categories[key]["title"]}领域最新动态',
                'summary': '今日该领域暂无重大新闻更新，建议关注相关技术博客获取最新资讯。',
                'content': '<p>今日该领域暂无重大新闻。</p>',
                'readTime': '3 分钟',
                'source': '系统提示',
                'sourceUrl': '#'
            })
    
    return {
        'summaries': [summaries],  # 保持原有数组结构
        'categories': categories
    }

def update_html():
    """更新 HTML 文件"""
    entries = fetch_news()
    new_data = categorize_and_generate(entries)
    
    if not new_data:
        print("Failed to generate content, skipping update")
        return
    
    # 读取现有 HTML
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 生成新的 JSON 数据（确保使用双引号）
    new_json = json.dumps(new_data, ensure_ascii=False, indent=4)
    
    # 使用正则替换 contentDatabase
    # 匹配 const contentDatabase = { ... }; 这一段
    pattern = r'const contentDatabase = \{[\s\S]*?\};(?=\s*const START_DATE|</script>)'
    
    replacement = f'const contentDatabase = {new_json};'
    
    new_html = re.sub(pattern, replacement, html_content)
    
    if new_html == html_content:
        print("Warning: Pattern not matched, trying alternative method...")
        # 备用方案：直接替换整个 script 标签中的变量
        pattern2 = r'(const contentDatabase = )(\{[\s\S]*?\})(;)'
        new_html = re.sub(pattern2, replacement, html_content)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_html)
    
    print(f"Updated at {datetime.now()}")

if __name__ == '__main__':
    update_html()
