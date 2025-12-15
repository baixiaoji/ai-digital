"""简单检索测试"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.indexer import IndexerService
from services.retriever import RetrieverService
from config import logger

async def test():
    # 初始化
    indexer = IndexerService()
    await indexer._ensure_initialized()
    indexer.vector_store.load()
    
    retriever = RetrieverService(indexer)
    
    # 测试查询
    queries = ["AI公司", "Logseq"]
    
    for query in queries:
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 测试: {query}")
        logger.info(f"{'='*60}")
        
        results = await retriever.local_search(query, top_k=5)
        logger.info(f"📊 返回 {len(results)} 条结果")
        
        if results:
            for i, result in enumerate(results[:3], 1):
                logger.info(f"  {i}. {result.title} (分数={result.score:.4f})")
                logger.info(f"     {result.content[:80]}...")
        else:
            logger.error("❌ 无结果")
    
    await indexer.metadata_store.close()

if __name__ == "__main__":
    asyncio.run(test())
