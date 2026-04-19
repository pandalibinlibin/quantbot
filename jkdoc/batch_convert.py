#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量HTM/HTML转Markdown脚本（修复版）
针对SingleFile生成的自包含HTML优化
用法: python batch_convert.py [目录路径]
"""

import os
import sys
import re
from pathlib import Path

try:
    from markdownify import markdownify as md
    from bs4 import BeautifulSoup, Comment
except ImportError:
    print("请先安装依赖: pip install markdownify beautifulsoup4 lxml")
    sys.exit(1)


def read_html_file(filepath):
    """智能读取HTML，自动处理中文编码"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'cp936']
    
    with open(filepath, 'rb') as f:
        raw = f.read()
    
    for enc in encodings:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    
    return raw.decode('utf-8', errors='ignore')


def clean_single_file(input_path, output_path):
    """转换单个文件"""
    try:
        html_content = read_html_file(input_path)
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 1. 移除完全不需要的标签（导航、脚本、样式、注释等）
        for tag_name in ['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # 移除HTML注释
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # 2. 处理SingleFile内嵌的base64图片（避免Markdown出现超长行）
        # 方案A：如果图片是base64且超过一定长度，替换为简短占位符
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src.startswith('data:image') and len(src) > 500:
                alt = img.get('alt', '图片')
                img.replace_with(soup.new_string(f"[图片: {alt}]"))
            # 如果是普通外链图片，保留（但SingleFile通常全是base64）
        
        # 3. 移除空的div/span（常见噪音）
        for tag in soup.find_all(['div', 'span']):
            if not tag.get_text(strip=True) and not tag.find_all('img'):
                tag.decompose()
        
        # 4. 获取body内容，如果没有body就用整个文档
        body = soup.find('body') or soup
        
        # 5. 转换为Markdown（只使用strip，不再同时使用convert）
        markdown_content = md(
            str(body),
            heading_style="ATX",      # 使用 # 标题格式
            bullets="-",              # 无序列表用 -
            strip=['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript'],
            # 不设置 convert 参数，避免冲突
        )
        
        # 6. 后处理：清理格式
        # 删除多余空行（超过3行合并为2行）
        markdown_content = re.sub(r'\n{4,}', '\n\n', markdown_content)
        # 删除行尾多余空格
        markdown_content = re.sub(r'[ \t]+\n', '\n', markdown_content)
        # 修复被错误转换的表格分隔符（markdownify有时会生成不规范表格）
        markdown_content = re.sub(r'\|\s*-\s*\|', '| --- |', markdown_content)
        
        # 7. 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    # 获取目标目录
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1]).resolve()
    else:
        target_dir = Path(__file__).parent.resolve()
    
    if not target_dir.exists():
        print(f"❌ 目录不存在: {target_dir}")
        sys.exit(1)
    
    # 查找所有htm/html文件
    files = []
    for pattern in ['*.htm', '*.html', '*.HTM', '*.HTML']:
        files.extend(target_dir.glob(pattern))
    
    files = sorted(set(files))
    
    if not files:
        print(f"⚠️  在 {target_dir} 中未找到任何 .htm/.html 文件")
        sys.exit(0)
    
    print(f"📁 目标目录: {target_dir}")
    print(f"📄 发现 {len(files)} 个文件，开始转换...\n")
    
    success = 0
    failed = []
    
    for idx, file_path in enumerate(files, 1):
        # 保持文件名不变，只改扩展名
        output_name = file_path.stem + '.md'
        output_path = target_dir / output_name
        
        ok, err = clean_single_file(file_path, output_path)
        
        if ok:
            # 显示文件大小
            size_kb = output_path.stat().st_size / 1024
            print(f"[{idx}/{len(files)}] ✓ {file_path.name} → {output_name} ({size_kb:.1f} KB)")
            success += 1
        else:
            print(f"[{idx}/{len(files)}] ✗ {file_path.name} 失败: {err}")
            failed.append(file_path.name)
    
    print("\n" + "="*50)
    print(f"✅ 转换完成：成功 {success}/{len(files)}")
    if failed:
        print(f"❌ 失败文件：{', '.join(failed)}")
    print(f"📂 输出位置：{target_dir}")
    print("="*50)


if __name__ == '__main__':
    main()