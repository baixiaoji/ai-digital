"""
测试 Markdown 解析器功能
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.markdown_parser import MarkdownParser

# 测试用例
test_content = """
---
title: Python 性能优化
tags: [python, performance]
---

# Python 性能优化技巧

这是关于 [[Python]] 性能优化的笔记。

## 主要方法

1. 使用 #cython 编译
2. 多进程并行 #multiprocessing
3. 参考 [[代码优化实战]]

## 相关资源

- Python 官方文档
- [[高性能Python编程]]

#python #optimization
"""

def test_parser():
    print("=" * 60)
    print("测试 Markdown 解析器")
    print("=" * 60)
    
    parser = MarkdownParser()
    
    # 测试双链提取
    backlinks = parser.extract_backlinks(test_content)
    print(f"\n✅ 双链提取: {backlinks}")
    assert len(backlinks) == 3, "应该提取到 3 个双链"
    
    # 测试标签提取
    tags = parser.extract_tags(test_content)
    print(f"✅ 标签提取: {tags}")
    assert len(tags) >= 3, "应该提取到至少 3 个标签"
    
    # 测试内容清理
    cleaned = parser.clean_content(test_content)
    print(f"\n✅ 清理后内容长度: {len(cleaned)} 字符")
    print(f"预览:\n{cleaned[:200]}...")
    
    # 测试分块
    chunks = parser.chunk_content(cleaned, chunk_size=100, overlap=20)
    print(f"\n✅ 分块结果: {len(chunks)} 个块")
    for i, (chunk_text, start, end) in enumerate(chunks[:3]):
        print(f"  块 {i+1}: [{start}:{end}] {len(chunk_text)} 字符")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

if __name__ == "__main__":
    test_parser()
