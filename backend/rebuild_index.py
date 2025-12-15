#!/usr/bin/env python3
"""重建索引脚本"""
import asyncio
from services.indexer import IndexerService
from config import logger

async def main():
    logger.info("🔄 开始重建索引（向量已缓存，仅重建元数据）...")
    
    indexer = IndexerService()
    await indexer.build_index()
    
    stats = await indexer.metadata_store.get_stats()
    logger.info("✅ 索引重建完成！")
    logger.info(f"   - 文档数: {stats['total_documents']}")
    logger.info(f"   - 分块数: {stats['total_chunks']}")
    logger.info(f"   - 标签数: {stats['total_tags']}")
    
    await indexer.metadata_store.close()

if __name__ == "__main__":
    asyncio.run(main())
