"""
测试 AI Builders API 连接
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.embedder import EmbedderService

async def test_api():
    print("=" * 60)
    print("测试 AI Builders API 连接")
    print("=" * 60)
    
    embedder = EmbedderService()
    
    # 测试单个文本向量化
    test_text = "这是一段测试文本"
    
    try:
        print(f"\n📤 发送测试请求...")
        print(f"文本: {test_text}")
        
        vector = await embedder.embed_query(test_text)
        
        print(f"✅ API 连接成功！")
        print(f"向量维度: {len(vector)}")
        print(f"向量示例（前10维）: {vector[:10]}")
        
        # 测试批量请求
        print(f"\n📤 测试批量请求（3个文本）...")
        test_texts = [
            "Python 编程",
            "机器学习",
            "数据分析"
        ]
        
        vectors = await embedder.embed_texts(test_texts, show_progress=True)
        print(f"✅ 批量请求成功！返回 {len(vectors)} 个向量")
        
        await embedder.close()
        
        print("\n" + "=" * 60)
        print("✅ API 测试通过！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ API 测试失败: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        await embedder.close()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_api())
    sys.exit(0 if result else 1)
