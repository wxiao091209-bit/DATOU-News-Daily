def update_html():
    """更新 HTML 文件"""
    entries = fetch_news()
    content = categorize_and_generate(entries)
    
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 生成新的 JSON 数据
    new_json = json.dumps(content, ensure_ascii=False, indent=4)
    
    # 使用更可靠的正则替换
    pattern = r'(const contentDatabase\s*=\s*)\{[\s\S]*?\}(\s*;)'
    replacement = r'\g<1>' + new_json + r'\g<2>'
    
    new_html = re.sub(pattern, replacement, html_content)
    
    if new_html == html_content:
        print("Warning: Pattern not found, trying alternative...")
        # 备选方案：直接查找 const contentDatabase = 后面的大括号
        alt_pattern = r'const contentDatabase\s*=\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s*;'
        new_html = re.sub(alt_pattern, f'const contentDatabase = {new_json};', html_content)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_html)
    
    print(f"Updated HTML with {len(entries)} articles at {datetime.now()}")
