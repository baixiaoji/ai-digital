#!/usr/bin/env python3
"""诊断检索问题"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.indexer import IndexerService
from services.retriever import RetrieverService
from config import logger
import numpy as np

async def main():
    indexer = IndexerService()
    await indexer._ensure_initialized()
    indexer.vector_store.load()
    
    retriever = RetrieverService(indexer)
    
    query = "AI公司和站点"
    logger.info(f"🔍 测试查询: {query}")
    
    # 1. 获取查询向量
    logger.info("\n步骤 1: 生成查询向量")
    query_vector = await indexer.embedder.embed_query(query)
    logger.info(f"✅ 向量维度: {len(query_vector)}")
    
    # 2. 向量搜索
    logger.info("\n步骤 2: FAISS 向量搜索")
    vector_results = indexer.vector_store.search(query_vector, top_k=20)
    logger.info(f"📊 FAISS 返回: {len(vector_results)} 条结果")
    
    if vector_results:
        for i, (chunk_id, score) in enumerate(vector_results[:5], 1):
            logger.info(f"  {i}. chunk_id={chunk_id}, score={score:.4f}")
            
            # 检查元数据是否存在
            cursor = await indexer.metadata_store.conn.execute(
                "SELECT doc_id, content FROM chunks WHERE chunk_id = ?", 
                (chunk_id,)
            )
            row = await cursor.fetchone()
            if row:
                logger.info(f"     ✅ 元数据存在: doc_id={row[0]}")
                logger.info(f"     内容: {row[1][:80]}...")
            else:
                logger.error(f"     ❌ 元数据缺失！")
    
    # 3. 检查相似度阈值
    logger.info(f"\n步骤 3: 检查阈值")
    logger.info(f"  当前阈值: {retriever.similarity_threshold}")
    
    if vector_results:
        scores = [score for _, score in vector_results]
        logger.info(f"  分数范围: {min(scores):.4f} ~ {max(scores):.4f}")
        logger.info(f"  超过阈值的数量: {sum(1 for s in scores if s >= retriever.similarity_threshold)}")
    
    # 4. 完整检索流程
    logger.info("\n步骤 4: 完整检索（含阈值过滤）")
    results = await retriever.local_search(query, top_k=5)
    logger.info(f"📊 最终返回: {len(results)} 条结果")
    
    if results:
        for i, result in enumerate(results, 1):
            logger.info(f"  {i}. {result.title} (score={result.score:.4f})")
    
    await indexer.metadata_store.close()

if __name__ == "__main__":
    asyncio.run(main())
