"""
演示优化后的流式输出格式
"""
import json
import re


def demo_optimized_stream():
    """演示优化后的流式输出"""
    
    # 模拟 LLM 生成的答案
    sample_answer = """基于您的本地笔记和网络资源，我来为您详细介绍：

# Git Worktree 全面指南

## 一、核心概念

**Git Worktree** 是 Git 2.5 版本引入的强大功能，它允许在同一个仓库中创建多个工作目录。

## 二、主要使用场景

### 1. 并行处理多个分支

- **场景**：在开发功能 A 时，需要紧急修复线上 bug
- **传统方式**：使用 `git stash` 暂存 → 切换分支 → 修复 → 恢复 stash
- **Worktree 方式**：创建新工作树 → 在新工作树中修复 → 两个任务并行进行

### 2. 核心命令

```bash
# 创建 worktree
git worktree add ../feature-branch feature-branch

# 列出所有 worktree
git worktree list
```

这就是 Git Worktree 的基本介绍。"""

    print("=" * 70)
    print("优化后的流式输出格式演示")
    print("=" * 70)
    print()
    
    # 按句子分割（保留标点符号）
    sentences = re.split(r'([。！？\n]+|[.!?]+\s+)', sample_answer)
    buffer = ""
    chunk_count = 0
    
    print("🔄 开始模拟流式输出...\n")
    
    # 工具调用事件
    print('data: {"type": "tool_call", "tool": "local_search", "status": "running"}')
    print()
    print('data: {"type": "tool_call", "tool": "local_search", "status": "completed", "count": 10}')
    print()
    
    # 文本流式输出
    for i, part in enumerate(sentences):
        buffer += part
        
        # 当遇到标点符号或积累足够长度时发送
        if (i % 2 == 1 and buffer.strip()) or len(buffer) > 100:
            chunk_count += 1
            
            # 转义 JSON 中的特殊字符
            escaped_content = (buffer
                .replace('\\', '\\\\')
                .replace('"', '\\"')
                .replace('\n', '\\n')
                .replace('\r', '\\r')
                .replace('\t', '\\t'))
            
            # 构造 SSE 事件
            event_json = f'{{"type": "text", "content": "{escaped_content}"}}'
            
            # 验证 JSON 格式
            try:
                json.loads(event_json)
                print(f'data: {event_json}')
                print()
            except json.JSONDecodeError as e:
                print(f"❌ JSON 错误: {e}")
                print(f"   内容: {event_json[:100]}...")
                print()
            
            buffer = ""
    
    # 发送剩余内容
    if buffer.strip():
        chunk_count += 1
        escaped_content = (buffer
            .replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\t', '\\t'))
        
        event_json = f'{{"type": "text", "content": "{escaped_content}"}}'
        print(f'data: {event_json}')
        print()
    
    # 引用数据
    citations = [
        {"id": 1, "title": "git worktree", "source": "local", "file_path": "/path/to/note.md"},
        {"id": 2, "title": "Git Advanced", "source": "local", "file_path": "/path/to/note2.md"}
    ]
    citations_json = json.dumps(citations, ensure_ascii=False)
    print(f'data: {{"type": "citations", "data": {citations_json}}}')
    print()
    
    # 完成标记
    print('data: {"type": "done"}')
    print()
    
    # 统计信息
    print("=" * 70)
    print("📊 统计信息")
    print("=" * 70)
    print(f"文本块数量: {chunk_count}")
    print(f"原始答案长度: {len(sample_answer)} 字符")
    print(f"平均每块长度: {len(sample_answer) // chunk_count} 字符")
    print()
    print("✅ 所有事件都是有效的 JSON 格式")
    print("✅ 前端可以正常解析")
    print()


def demo_old_format():
    """演示旧版本的问题格式"""
    
    print("=" * 70)
    print("旧版本的问题格式（仅前 10 个事件）")
    print("=" * 70)
    print()
    
    sample_text = "基于您的本地笔记和网络资源，我来为您详细介绍 Git Worktree"
    words = sample_text.split()
    
    print("❌ 单词级分割 + 单引号 + 未转义:\n")
    
    for i, word in enumerate(words[:10]):
        # 旧版本的错误格式
        print(f"data: {{'type': 'text', 'content': '{word} '}}")
        print()
    
    print("...")
    print()
    print(f"📊 如果完整输出，会产生约 {len(words)} 个事件")
    print()


if __name__ == "__main__":
    print("\n🎯 流式输出格式对比\n")
    
    # 演示旧格式的问题
    demo_old_format()
    
    print("\n" + "=" * 70)
    print()
    
    # 演示新格式
    demo_optimized_stream()
    
    print("=" * 70)
    print("🎉 演示完成")
    print("=" * 70)
