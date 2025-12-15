"""
向量化缓存服务
用于缓存已计算的向量，避免重复调用 API
"""
import hashlib
import aiosqlite
from typing import List, Optional
from pathlib import Path

from config import settings, logger


class EmbeddingCache:
    """向量化缓存管理"""
    
    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = cache_path or Path(settings.storage.data_dir) / "embedding_cache.db"
        self.conn: Optional[aiosqlite.Connection] = None
    
    async def initialize(self):
        """初始化缓存数据库"""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(str(self.cache_path))
        await self._create_table()
    
    async def _create_table(self):
        """创建缓存表"""
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                content_hash TEXT NOT NULL,
                model TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (content_hash, model)
            )
        """)
        
        # 创建索引加速查询
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_lookup 
            ON embedding_cache(content_hash, model)
        """)
        
        await self.conn.commit()
    
    def _compute_hash(self, text: str) -> str:
        """计算文本哈希"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    async def get(self, text: str, model: str) -> Optional[List[float]]:
        """
        从缓存获取向量
        
        Args:
            text: 文本内容
            model: 模型名称
        
        Returns:
            向量列表，如果缓存不存在则返回 None
        """
        content_hash = self._compute_hash(text)
        
        cursor = await self.conn.execute("""
            SELECT embedding FROM embedding_cache
            WHERE content_hash = ? AND model = ?
        """, (content_hash, model))
        
        row = await cursor.fetchone()
        
        if row:
            # 将 BLOB 反序列化为 float 列表
            import json
            embedding = json.loads(row[0])
            return embedding
        
        return None
    
    async def get_batch(self, texts: List[str], model: str) -> List[Optional[List[float]]]:
        """
        批量获取缓存向量
        
        Args:
            texts: 文本列表
            model: 模型名称
        
        Returns:
            向量列表，未命中的位置为 None
        """
        hashes = [self._compute_hash(text) for text in texts]
        
        # 批量查询
        placeholders = ','.join(['?'] * len(hashes))
        cursor = await self.conn.execute(f"""
            SELECT content_hash, embedding FROM embedding_cache
            WHERE content_hash IN ({placeholders}) AND model = ?
        """, (*hashes, model))
        
        rows = await cursor.fetchall()
        
        # 构建哈希到向量的映射
        import json
        cache_map = {row[0]: json.loads(row[1]) for row in rows}
        
        # 返回按原顺序排列的结果
        return [cache_map.get(h) for h in hashes]
    
    async def set(self, text: str, model: str, embedding: List[float]):
        """
        存储向量到缓存
        
        Args:
            text: 文本内容
            model: 模型名称
            embedding: 向量
        """
        import json
        content_hash = self._compute_hash(text)
        
        await self.conn.execute("""
            INSERT OR REPLACE INTO embedding_cache (content_hash, model, embedding)
            VALUES (?, ?, ?)
        """, (content_hash, model, json.dumps(embedding)))
        
        await self.conn.commit()
    
    async def set_batch(self, texts: List[str], model: str, embeddings: List[List[float]]):
        """
        批量存储向量到缓存
        
        Args:
            texts: 文本列表
            model: 模型名称
            embeddings: 向量列表
        """
        import json
        
        data = [
            (self._compute_hash(text), model, json.dumps(emb))
            for text, emb in zip(texts, embeddings)
        ]
        
        await self.conn.executemany("""
            INSERT OR REPLACE INTO embedding_cache (content_hash, model, embedding)
            VALUES (?, ?, ?)
        """, data)
        
        await self.conn.commit()
    
    async def get_stats(self) -> dict:
        """获取缓存统计信息"""
        cursor = await self.conn.execute("""
            SELECT model, COUNT(*) as count 
            FROM embedding_cache 
            GROUP BY model
        """)
        rows = await cursor.fetchall()
        
        return {row[0]: row[1] for row in rows}
    
    async def clear(self, model: Optional[str] = None):
        """
        清空缓存
        
        Args:
            model: 如果指定，只清空该模型的缓存
        """
        if model:
            await self.conn.execute("DELETE FROM embedding_cache WHERE model = ?", (model,))
        else:
            await self.conn.execute("DELETE FROM embedding_cache")
        
        await self.conn.commit()
    
    async def close(self):
        """关闭连接"""
        if self.conn:
            await self.conn.close()


# 测试代码
async def test_cache():
    """测试缓存功能"""
    cache = EmbeddingCache()
    await cache.initialize()
    
    # 测试单个缓存
    text = "测试文本"
    model = "text-embedding-3-small"
    embedding = [0.1] * 1536
    
    # 存储
    await cache.set(text, model, embedding)
    
    # 读取
    cached = await cache.get(text, model)
    assert cached == embedding, "缓存数据不匹配"
    
    # 测试批量缓存
    texts = ["文本1", "文本2", "文本3"]
    embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]
    
    await cache.set_batch(texts, model, embeddings)
    
    cached_batch = await cache.get_batch(texts, model)
    assert all(c == e for c, e in zip(cached_batch, embeddings)), "批量缓存数据不匹配"
    
    # 测试部分命中
    mixed_texts = ["文本1", "新文本", "文本3"]
    mixed_results = await cache.get_batch(mixed_texts, model)
    assert mixed_results[0] == embeddings[0], "第1个应命中"
    assert mixed_results[1] is None, "第2个应未命中"
    assert mixed_results[2] == embeddings[2], "第3个应命中"
    
    # 统计
    stats = await cache.get_stats()
    print(f"缓存统计: {stats}")
    
    await cache.close()
    print("✅ 缓存测试通过")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_cache())
