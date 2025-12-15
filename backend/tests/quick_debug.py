"""快速诊断：检查向量检索分数"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.indexer import IndexerService
from config import logger

async def main():
    indexer = IndexerService()
    await indexer._ensure_initialized()
    
    # 统计信息
    stats = await indexer.metadata_store.get_stats()
    logger.info(f"📊 数据库: {stats['total_documents']} 文档, {stats['total_chunks']} 分块")
    
    # 加载向量索引
    indexer.vector_store.load()
    vector_count = indexer.vector_store.index.ntotal if indexer.vector_store.index else 0
    logger.info(f"📊 向量索引: {vector_count} 个向量")
    
    # 测试查询
    test_queries = ["检索笔记中AI公司", "Logseq的用法"]
    
    for query in test_queries:
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 测试查询: {query}")
        logger.info(f"{'='*60}")
        
        # 生成向量
        query_embedding = await indexer.embedder.embed_texts([query])
        logger.info(f"✅ 查询向量维度: {len(query_embedding[0])}")
        
        # 搜索 Top-20
        results = indexer.vector_store.search(query_embedding[0], top_k=20)
        logger.info(f"📊 返回 {len(results)} 条结果")
        
        if results:
            scores = [score for _, score in results]
            logger.info(f"📈 分数范围: {min(scores):.4f} ~ {max(scores):.4f}")
            logger.info(f"📈 平均分数: {sum(scores)/len(scores):.4f}")
            logger.info(f"\n前 10 个结果:")
            for i, (chunk_id, score) in enumerate(results[:10], 1):
                passed = "✅" if score >= 0.6 else "❌"
                logger.info(f"  {i}. {chunk_id} - 分数={score:.4f} {passed}")
        else:
            logger.error("❌ 未找到任何结果")
    
    await indexer.metadata_store.close()

if __name__ == "__main__":
    asyncio.run(main())
