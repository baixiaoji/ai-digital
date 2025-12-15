"""
测试 LLM 集成到检索系统
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from services.llm import LLMService
from models import SearchResult


async def test_llm_answer_generation():
    """测试 LLM 答案生成"""
    print("=" * 60)
    print("测试 LLM 答案生成功能")
    print("=" * 60)
    
    # 创建 LLM 服务
    llm_service = LLMService()
    
    # 模拟检索结果
    query = "如何使用 Python 进行数据分析？"
    
    local_results = [
        {
            "title": "Python 数据分析基础",
            "content": "使用 Pandas 库进行数据处理和分析。Pandas 提供了 DataFrame 和 Series 两种主要的数据结构，可以高效地处理表格数据。常用操作包括数据清洗、过滤、分组、聚合等。",
            "file_path": "/path/to/note1.md",
            "score": 0.92
        },
        {
            "title": "数据可视化技巧",
            "content": "使用 Matplotlib 和 Seaborn 进行数据可视化。Matplotlib 是最基础的可视化库，Seaborn 在此基础上提供了更美观的默认样式和更高级的统计图表。",
            "file_path": "/path/to/note2.md",
            "score": 0.85
        }
    ]
    
    web_results = [
        {
            "title": "Python Data Analysis Tutorial",
            "content": "Learn data analysis with Python using NumPy, Pandas, and Matplotlib. NumPy provides efficient array operations, Pandas handles structured data, and Matplotlib creates visualizations.",
            "url": "https://example.com/tutorial",
            "score": 0.78
        }
    ]
    
    print(f"\n📝 用户问题: {query}")
    print(f"\n📊 检索结果统计:")
    print(f"  - 本地笔记: {len(local_results)} 条")
    print(f"  - 网络资源: {len(web_results)} 条")
    
    print("\n🤖 正在使用 LLM 生成答案...")
    
    try:
        # 生成答案
        answer = await llm_service.generate_answer(query, local_results, web_results)
        
        print("\n✅ 答案生成成功！\n")
        print("=" * 60)
        print("LLM 生成的答案:")
        print("=" * 60)
        print(answer)
        print("=" * 60)
        
        # 检查答案质量
        print("\n📋 答案质量检查:")
        if len(answer) > 100:
            print("  ✅ 答案长度合适")
        else:
            print("  ⚠️ 答案可能过短")
        
        if "Pandas" in answer or "pandas" in answer:
            print("  ✅ 答案包含关键概念")
        else:
            print("  ⚠️ 答案可能缺少关键概念")
        
        print("\n✅ 测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        raise
    
    finally:
        await llm_service.close()


async def test_fallback_mechanism():
    """测试降级机制"""
    print("\n" + "=" * 60)
    print("测试降级机制（模拟 LLM 失败）")
    print("=" * 60)
    
    llm_service = LLMService()
    
    # 使用无效的 model 触发错误
    original_model = llm_service.model
    llm_service.model = "invalid-model-name"
    
    query = "测试降级机制"
    local_results = [
        {
            "title": "测试笔记",
            "content": "这是一条测试笔记内容",
            "file_path": "/test.md",
            "score": 0.9
        }
    ]
    web_results = []
    
    try:
        answer = await llm_service.generate_answer(query, local_results, web_results)
        
        print("\n✅ 降级机制正常工作")
        print(f"\n降级答案预览:\n{answer[:200]}...")
        
        if "测试笔记" in answer:
            print("\n✅ 降级答案包含检索结果")
        else:
            print("\n⚠️ 降级答案可能不完整")
    
    except Exception as e:
        print(f"\n❌ 降级机制测试失败: {str(e)}")
        raise
    
    finally:
        llm_service.model = original_model
        await llm_service.close()


async def main():
    """主测试函数"""
    print("\n🚀 开始测试 LLM 集成功能\n")
    
    # 测试 1: 正常 LLM 答案生成
    await test_llm_answer_generation()
    
    # 测试 2: 降级机制
    await test_fallback_mechanism()
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
