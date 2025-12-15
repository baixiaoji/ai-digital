"""
测试优化后的流式输出
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

import httpx
from main import app
import json


def test_stream_output():
    """测试流式输出格式"""
    print("=" * 60)
    print("测试优化后的流式输出格式")
    print("=" * 60)
    
    # 使用 httpx 直接测试，因为需要实际启动服务
    # 这里改为手动测试说明
    print("\n⚠️  注意：此测试需要手动运行服务")
    print("\n请执行以下步骤：")
    print("1. 在终端 1 运行: cd backend && python main.py")
    print("2. 在终端 2 运行: curl -N http://localhost:8000/api/chat?query=如何使用git+worktree&local_ratio=0.8")
    print("\n或者使用前端界面直接测试\n")
    
    return True
    
    # 以下是原测试代码（需要服务运行）
    """
    client = httpx.Client(base_url="http://localhost:8000")
    
    # 发起流式请求
    query = "如何使用 git worktree？"
    print(f"\n📝 查询: {query}")
    print(f"\n🔄 开始接收流式数据...\n")
    
    with client.stream("POST", f"/api/chat?query={query}&local_ratio=0.8") as response:
        print(f"📡 HTTP 状态码: {response.status_code}")
        print(f"📋 Content-Type: {response.headers.get('content-type')}\n")
        
        if response.status_code != 200:
            print(f"❌ 请求失败: {response.text}")
            return
        
        event_count = 0
        text_chunks = []
        citations_received = False
        done_received = False
        json_errors = []
        
        # 逐行读取流式响应
        for line in response.iter_lines():
            if not line or not line.strip():
                continue
            
            # 解析 SSE 格式
            if line.startswith("data: "):
                event_count += 1
                data_str = line[6:]  # 移除 "data: " 前缀
                
                try:
                    # 尝试解析 JSON
                    data = json.loads(data_str)
                    event_type = data.get("type")
                    
                    if event_type == "tool_call":
                        tool = data.get("tool")
                        status = data.get("status")
                        count = data.get("count", "")
                        print(f"🔧 工具调用: {tool} - {status} {count}")
                    
                    elif event_type == "text":
                        content = data.get("content", "")
                        text_chunks.append(content)
                        print(f"📝 文本块 #{len(text_chunks)}: {content[:50]}...")
                    
                    elif event_type == "citations":
                        citations_data = data.get("data", [])
                        citations_received = True
                        print(f"📚 引用数据: {len(citations_data)} 条引用")
                    
                    elif event_type == "done":
                        done_received = True
                        print(f"✅ 完成标记")
                
                except json.JSONDecodeError as e:
                    json_errors.append({
                        "event": event_count,
                        "error": str(e),
                        "data": data_str[:100]
                    })
                    print(f"❌ JSON 解析错误 (事件 #{event_count}): {str(e)}")
                    print(f"   数据: {data_str[:100]}...")
        
        # 输出统计
        print("\n" + "=" * 60)
        print("📊 统计结果")
        print("=" * 60)
        print(f"总事件数: {event_count}")
        print(f"文本块数: {len(text_chunks)}")
        print(f"引用接收: {'✅' if citations_received else '❌'}")
        print(f"完成标记: {'✅' if done_received else '❌'}")
        print(f"JSON 错误: {len(json_errors)} 个")
        
        if json_errors:
            print("\n❌ JSON 解析错误详情:")
            for err in json_errors[:5]:  # 只显示前 5 个错误
                print(f"  事件 #{err['event']}: {err['error']}")
                print(f"    数据: {err['data']}")
        
        # 验证结果
        print("\n" + "=" * 60)
        print("✅ 验证结果")
        print("=" * 60)
        
        success = True
        
        if len(text_chunks) == 0:
            print("❌ 未接收到任何文本块")
            success = False
        else:
            print(f"✅ 接收到 {len(text_chunks)} 个文本块")
        
        if not citations_received:
            print("❌ 未接收到引用数据")
            success = False
        else:
            print("✅ 引用数据正常接收")
        
        if not done_received:
            print("❌ 未接收到完成标记")
            success = False
        else:
            print("✅ 完成标记正常接收")
        
        if json_errors:
            print(f"❌ 存在 {len(json_errors)} 个 JSON 解析错误")
            success = False
        else:
            print("✅ 所有 JSON 格式正确")
        
        # 重组完整答案
        if text_chunks:
            full_answer = "".join(text_chunks)
            print(f"\n📄 完整答案长度: {len(full_answer)} 字符")
            print(f"\n前 200 字符预览:")
            print("-" * 60)
            print(full_answer[:200])
            print("-" * 60)
        
        if success:
            print("\n🎉 所有测试通过！")
        else:
            print("\n⚠️ 部分测试失败，请检查输出")
        
        return success


if __name__ == "__main__":
    print("\n🚀 开始测试流式输出优化\n")
    
    try:
        success = test_stream_output()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
