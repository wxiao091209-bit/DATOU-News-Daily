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

# 尝试导入翻译库，如果没有则使用增强字典
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
    translator = GoogleTranslator(source='auto', target='zh-CN')
except ImportError:
    TRANSLATOR_AVAILABLE = False
    print("注意：未安装 deep_translator，使用本地字典翻译")

def smart_translate(text, max_chars=150):
    """智能翻译：先尝试API，失败用字典"""
    if not text:
        return "暂无内容"
    
    # 如果已有足够中文，直接返回
    chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
    if chinese_chars > len(text) * 0.4:
        return text[:max_chars]
    
    # 方法1：使用Google Translate API（免费）
    if TRANSLATOR_AVAILABLE:
        try:
            # 分段翻译（API有长度限制）
            if len(text) > 4000:
                text = text[:4000]
            translated = translator.translate(text)
            return translated[:max_chars]
        except Exception as e:
            print(f"API翻译失败: {e}，使用字典翻译")
    
    # 方法2：增强字典翻译（备用）
    return enhanced_dict_translate(text, max_chars)

def enhanced_dict_translate(text, max_chars=150):
    """增强版字典翻译，覆盖更多词汇"""
    if not text:
        return "暂无内容"
    
    # 扩展的翻译字典
    translations = [
        # 基础词汇（按长度降序）
        ("artificial intelligence", "人工智能"),
        ("machine learning", "机器学习"),
        ("large language model", "大语言模型"),
        ("command center", "指挥中心"),
        ("software development", "软件开发"),
        ("enterprise data", "企业级数据"),
        ("frontier intelligence", "前沿智能"),
        ("AI agents", "AI智能体"),
        ("AI agent", "AI智能体"),
        ("data agent", "数据智能体"),
        ("in-house", "自研"),
        ("most valuable", "最有价值的"),
        ("private company", "私营公司"),
        ("weekly newsletter", "每周通讯"),
        
        # 公司/产品
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
        ("TechCrunch", "TechCrunch"),
        ("Musk", "马斯克"),
        ("xAI", "xAI"),
        ("Codex", "Codex"),
        
        # 动词
        ("partner", "合作"),
        ("partnership", "合作"),
        ("introducing", "推出"),
        ("introduces", "推出"),
        ("announce", "宣布"),
        ("announcing", "宣布"),
        ("launch", "发布"),
        ("launches", "发布"),
        ("release", "发布"),
        ("update", "更新"),
        ("bring", "引入"),
        ("enable", "使能够"),
        ("enabling", "使"),
        ("creates", "创建"),
        ("create", "创建"),
        ("built", "构建"),
        ("build", "构建"),
        ("appeared", "发表于"),
        ("appear", "出现"),
        ("paves", "铺平"),
        ("pave", "铺平"),
        ("prove", "证明"),
        ("try", "尝试"),
        ("get", "获取"),
        
        # 名词
        ("merger", "合并"),
        ("agreement", "协议"),
        ("investment", "投资"),
        ("funding", "融资"),
        ("company", "公司"),
        ("business", "业务"),
        ("story", "报道"),
        ("algorithm", "算法"),
        ("newsletter", "通讯"),
        ("inbox", "收件箱"),
        ("way", "道路/方式"),
        ("world", "世界"),
        ("insight", "洞察"),
        ("intelligence", "智能"),
        ("data", "数据"),
        ("chip", "芯片"),
        ("robotics", "机器人"),
        ("infrastructure", "基础设施"),
        
        # 形容词/副词
        ("valuable", "有价值的"),
        ("private", "私有的"),
        ("weekly", "每周的"),
        ("most", "最"),
        ("more", "更多"),
        ("useful", "有用的"),
        ("original", "原创的"),
        ("directly", "直接"),
        ("massive", "海量的"),
        ("reliable", "可靠的"),
        ("long-running", "长时间运行的"),
        ("parallel", "并行的"),
        ("multiple", "多个"),
        
        # 介词/冠词/连词（小写匹配）
        (" the ", " "),
        (" and ", "和"),
        (" in ", "在"),
        (" a ", "一个"),
        (" an ", "一个"),
        (" to ", "来"),
        (" of ", "的"),
        (" for ", "用于"),
        (" with ", "与"),
        (" by ", "通过"),
        (" from ", "来自"),
        (" into ", "进入"),
        (" on ", "在"),
        (" at ", "在"),
    ]
    
    result = text
    for en, cn in sorted(translations, key=lambda x: len(x[0]), reverse=True):
        # 不区分大小写替换，但保留原大小写用于判断
        result = re.sub(r'\b' + re.escape(en) + r'\b', cn, result, flags=re.IGNORECASE)
    
    # 清理多余空格和标点
    result = re.sub(r'\s+', ' ', result).strip()
    result = re.sub(r' ([，。、；：？！])', r'\1', result)  # 移除标点前空格
    
    # 如果翻译后还是英文为主，标记为[原文]
    chinese_count = len([c for c in result if '\u4e00' <= c <= '\u9fff'])
    if chinese_count < len(result) * 0.3:
        return f"[海外资讯] {text[:max_chars-10]}"
    
    return result[:max_chars]

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
        print(f"Fetching: {name}")
        feed = feedparser.parse(url)
        entries = []
        for entry in feed.entries[:5]:
            summary = entry.get('summary', entry.get('description', ''))
            clean_summary = re.sub(r'<[^>]+>', '', summary)
            
            # 翻译处理
            title_cn = smart_translate(entry.title, 100)
            summary_cn = smart_translate(clean_summary, 150)
            
            entries.append({
                "title": title_cn,
                "link": entry.link,
                "date": entry.get('published', ''),
                "summary": summary_cn,
                "source": name,
                "content": f"<p>{summary_cn}</p><p><a href='{entry.link}' target='_blank'>查看原文：{name}</a></p>"
            })
        print(f"  ✓ {len(entries)}条")
        return entries
    except Exception as e:
        print(f"  ✗ Error: {e}")
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
                    "title": f"[论文] {smart_translate(title, 100)}",
                    "link": f"https://huggingface.co/papers/{paper_id}",
                    "date": p.get('publishedAt', ''),
                    "summary": smart_translate(summary, 150) if summary else "最新AI研究论文",
                    "source": "Hugging Face",
                    "content": f"<p>{smart_translate(summary, 200)}</p><p><a href='https://huggingface.co/papers/{paper_id}' target='_blank'>查看论文</a></p>"
                })
        print(f"  ✓ {len(entries)}条")
        return entries
    except Exception as e:
        print(f"  ✗ Error: {e}")
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
                    "title": smart_translate(title, 100),
                    "link": href,
                    "date": datetime.now().isoformat(),
                    "summary": f"{name}最新动态",
                    "source": name,
                    "content": f"<p>{name}发布更新</p><p><a href='{href}' target='_blank'>查看原文</a></p>"
                })
        print(f"  ✓ {len(entries)}条")
        return entries
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return []

def estimate_read_time(text):
    words = len(text) / 2
    minutes = max(1, round(words / 300))
    return f"{minutes} 分钟"

def build_content_database():
    """构建数据库"""
    print("\n" + "="*50)
    database = {"summaries": [[]], "categories": {}}
    all_articles_by_source = {}
    
    # 抓取数据
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
                
                if entries:
                    all_articles_by_source[source['name']] = entries
                if cat_key not in database["categories"]:
                    database["categories"][cat_key] = []
                database["categories"][cat_key].extend(entries)
            except Exception as e:
                print(f"Error: {e}")
    
    # 处理分类数据
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
        print(f"{cat_key}: {len(unique[:8])}篇")
    
    # 选择摘要（强制多样性）
    summaries = []
    priority = ["OpenAI Blog", "Anthropic News", "Google DeepMind", "Meta AI Blog", 
                "Hugging Face", "NVIDIA Blog AI", "TechCrunch AI", "MIT Tech Review AI"]
    
    for src in priority:
        if src in all_articles_by_source and all_articles_by_source[src]:
            article = all_articles_by_source[src][0]
            summaries.append({
                "text": article['summary'][:120] + "..." if len(article['summary']) > 120 else article['summary'],
                "source": article['source'],
                "url": article['link']
            })
            print(f"摘要来源: {src}")
            if len(summaries) >= 3:
                break
    
    database["summaries"] = [summaries[:3]]
    return database

def update_html_file():
    """更新HTML"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        new_db = build_content_database()
        json_str = json.dumps(new_db, ensure_ascii=False, indent=8)
        
        pattern = r'const contentDatabase = \{.*?\};'
        replacement = f'const contentDatabase = {json_str};'
        new_html = re.sub(pattern, replacement, html_content, flags=re.DOTALL)
        
        if new_html == html_content:
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
        print(f"\n✅ 完成！共{total}篇文章，{len(new_db['summaries'][0])}条摘要")
        
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == '__main__':
    print("🤖 DATOU AI News - 智能翻译版")
    print("=" * 50)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if TRANSLATOR_AVAILABLE:
        print("🌐 使用Google Translate API")
    else:
        print("📚 使用本地字典翻译")
    print("=" * 50)
    update_html_file()
