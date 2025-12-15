"""
本地检索功能单元测试
测试查询: "检索笔记中AI公司" 和 "Logseq的用法"
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.retriever import RetrieverService
from services.indexer import IndexerService
from config import settings
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_local_retrieval():
    """测试本地检索功能"""
    
    # 初始化组件
    logger.info("=" * 60)
    logger.info("🔍 开始本地检索单元测试")
    logger.info("=" * 60)
    
    # 初始化 indexer（包含所有依赖）
    indexer = IndexerService()
    
    # 检查索引状态
    logger.info("\n📊 索引状态检查:")
    logger.info(f"  - 向量数据库路径: {settings.storage.vector_index}")
    logger.info(f"  - 元数据数据库路径: {settings.storage.metadata_db}")
    
    # 检查向量数量
    vector_count = indexer.vector_store.get_vector_count()
    logger.info(f"  - 向量总数: {vector_count}")
    
    if vector_count == 0:
        logger.error("❌ 向量数据库为空！请先运行索引构建")
        return
    
    # 检查元数据数量
    documents = indexer.metadata_store.list_documents()
    logger.info(f"  - 文档总数: {len(documents)}")
    if documents:
        logger.info(f"  - 前 3 个文档标题: {[doc.get('title', 'N/A') for doc in documents[:3]]}")
    
    # 创建检索器
    retriever = RetrieverService(indexer)
    
    # 测试查询列表
    test_queries = [
        "检索笔记中AI公司",
        "Logseq的用法"
    ]
    
    logger.info("\n" + "=" * 60)
    logger.info("🔍 开始测试查询")
    logger.info("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n{'*' * 60}")
        logger.info(f"测试查询 #{i}: {query}")
        logger.info(f"{'*' * 60}")
        
        try:
            # 1. 测试 query embedding
            logger.info("\n🔹 步骤 1: 生成查询向量")
            query_embedding = await indexer.embedder.embed_texts([query])
            logger.info(f"  ✅ 查询向量维度: {len(query_embedding[0])}")
            logger.info(f"  ✅ 向量前 5 个值: {query_embedding[0][:5]}")
            
            # 2. 测试向量搜索
            logger.info("\n🔹 步骤 2: 执行向量搜索 (top_k=10)")
            vector_results = indexer.vector_store.search(query_embedding[0], top_k=10)
            logger.info(f"  📊 向量搜索返回: {len(vector_results)} 条结果")
            
            if vector_results:
                for j, (chunk_id, score) in enumerate(vector_results[:3], 1):
                    # 注意：search 返回 (chunk_id, score) 元组
                    logger.info(f"    #{j} Chunk ID={chunk_id}, Score={score:.4f}")
                    # 简单检查 chunk 是否存在（元数据库查询较复杂，跳过详细内容）
            else:
                logger.warning("  ⚠️ 向量搜索返回 0 结果")
            
            # 3. 测试本地检索
            logger.info("\n🔹 步骤 3: 执行本地检索 (top_k=5)")
            results = await retriever.local_search(query, top_k=5)
            logger.info(f"  📊 本地检索返回: {len(results)} 条结果")
            
            if results:
                logger.info(f"\n  🎯 检索结果详情:")
                for j, result in enumerate(results, 1):
                    # results 是 SearchResult 对象列表
                    logger.info(f"    --- 结果 #{j} ---")
                    logger.info(f"      来源: {result.source}")
                    logger.info(f"      文档: {result.file_path}")
                    logger.info(f"      相似度: {result.score:.4f}")
                    logger.info(f"      标题: {result.title}")
                    content_preview = result.content[:100]
                    logger.info(f"      内容预览: {content_preview}...")
            else:
                logger.error(f"  ❌ 本地检索返回 0 结果！")
                
                # 进一步诊断
                logger.info("\n  🔧 诊断信息:")
                logger.info(f"    - 向量数据库是否为空: {vector_count == 0}")
                logger.info(f"    - 元数据数据库是否为空: {len(documents) == 0}")
                logger.info(f"    - 查询向量是否有效: {len(query_embedding[0]) == 1536}")
                
                # 检查是否是相似度阈值问题
                logger.info("\n  🔧 测试更宽松的阈值 (top_k=20):")
                loose_results = indexer.vector_store.search(query_embedding[0], top_k=20)
                logger.info(f"    找到 {len(loose_results)} 条候选结果")
                if loose_results:
                    scores = [score for _, score in loose_results]
                    logger.info(f"    相似度范围: {min(scores):.4f} ~ {max(scores):.4f}")
        
        except Exception as e:
            logger.error(f"  ❌ 查询失败: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 测试完成")
    logger.info("=" * 60)


async def test_metadata_query():
    """测试元数据数据库查询能力"""
    logger.info("\n" + "=" * 60)
    logger.info("🔍 元数据数据库内容检查")
    logger.info("=" * 60)
    
    indexer = IndexerService()
    await indexer._ensure_initialized()
    
    # 获取统计信息
    stats = await indexer.metadata_store.get_stats()
    logger.info(f"\n📊 数据库统计:")
    logger.info(f"  - 文档总数: {stats['total_documents']}")
    logger.info(f"  - 分块总数: {stats['total_chunks']}")
    logger.info(f"  - 标签总数: {stats['total_tags']}")
    
    if stats['total_documents'] == 0:
        logger.error("❌ 元数据数据库为空！")
        return
    
    logger.info("\n✅ 元数据数据库检查完成")


if __name__ == "__main__":
    # 运行所有测试
    asyncio.run(test_metadata_query())
    asyncio.run(test_local_retrieval())
