"""
向量化服务
调用 AI Builders Embedding API
"""
import asyncio
from typing import List

import httpx
from tqdm import tqdm

from config import settings, logger
from database.embedding_cache import EmbeddingCache


class EmbedderService:
    """向量化服务"""
    
    def __init__(self):
        self.api_base = settings.embedding.api_base
        self.model = settings.embedding.model
        self.api_key = settings.api_key
        self.batch_size = settings.embedding.batch_size
        self.dimension = settings.embedding.dimension
        
        # 初始化缓存
        self.cache = EmbeddingCache()
        self._cache_initialized = False
        
        # 分离连接/读写超时，避免大响应体超时
        timeout_config = httpx.Timeout(
            connect=30.0,   # 连接超时：30 秒
            read=180.0,     # 读取超时：180 秒（大响应体）
            write=60.0,     # 写入超时：60 秒
            pool=10.0       # 连接池超时：10 秒
        )
        
        self.client = httpx.AsyncClient(
            base_url=self.api_base,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=timeout_config,  # 使用分离的超时配置
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
    
    async def embed_texts(self, texts: List[str], show_progress: bool = True) -> List[List[float]]:
        """
        批量向量化文本（并发版本 + 缓存）
        
        Args:
            texts: 文本列表
            show_progress: 是否显示进度条
        
        Returns:
            向量列表
        """
        # 确保缓存已初始化
        if not self._cache_initialized:
            await self.cache.initialize()
            self._cache_initialized = True
        
        all_embeddings = []
        
        # 分批处理
        batches = [texts[i:i + self.batch_size] for i in range(0, len(texts), self.batch_size)]
        
        # 并发参数（从配置读取）
        max_concurrent = getattr(settings.embedding, 'max_concurrent', 6)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def embed_with_semaphore(batch, batch_idx):
            """带信号量的向量化（含缓存逻辑）"""
            async with semaphore:
                embeddings = await self._embed_batch_with_cache(batch)
                return batch_idx, embeddings
        
        # 创建并发任务
        tasks = [embed_with_semaphore(batch, i) for i, batch in enumerate(batches)]
        
        # 执行并发请求
        if show_progress:
            results = []
            with tqdm(total=len(batches), desc="向量化") as pbar:
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    results.append(result)
                    pbar.update(1)
        else:
            results = await asyncio.gather(*tasks)
        
        # 按批次顺序排序
        results.sort(key=lambda x: x[0])
        
        # 展平嵌套列表
        for _, embeddings in results:
            all_embeddings.extend(embeddings)
        
        return all_embeddings
    
    async def _embed_batch(self, texts: List[str], max_retries: int = 3) -> List[List[float]]:
        """
        向量化单个批次（带重试机制）
        
        Args:
            texts: 文本列表
            max_retries: 最大重试次数
        
        Returns:
            向量列表
        """
        for attempt in range(max_retries):
            try:
                logger.debug(f"发送 API 请求: {len(texts)} 个文本 (尝试 {attempt+1}/{max_retries})")
                response = await self.client.post(
                    "/v1/embeddings",
                    json={
                        "model": self.model,
                        "input": texts
                    }
                    # 使用全局 timeout 配置（已在 client 初始化时设置）
                )
                response.raise_for_status()
                
                result = response.json()
                
                # 提取向量（按 index 排序）
                embeddings_data = sorted(result['data'], key=lambda x: x['index'])
                embeddings = [item['embedding'] for item in embeddings_data]
                
                logger.debug(f"✅ 成功获取 {len(embeddings)} 个向量")
                return embeddings
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = (attempt + 1) * 5  # 指数退避：5s, 10s, 15s
                    logger.warning(f"⚠️ 触发速率限制，等待 {wait_time}s 后重试...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"❌ API 请求失败: {e.response.status_code}")
                logger.error(f"响应内容: {e.response.text[:200]}")
                if attempt == max_retries - 1:
                    raise
            except httpx.TimeoutException as e:
                logger.warning(f"⚠️ API 请求超时，重试中...")
                if attempt == max_retries - 1:
                    logger.error(f"❌ 最终超时: {str(e)}")
                    raise
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"❌ 向量化失败: {type(e).__name__}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)
        
        raise RuntimeError(f"向量化失败，已重试 {max_retries} 次")
    
    async def _embed_batch_with_cache(self, texts: List[str]) -> List[List[float]]:
        """
        带缓存的批量向量化
        
        Args:
            texts: 文本列表
        
        Returns:
            向量列表
        """
        # 1. 尝试从缓存获取
        cached_embeddings = await self.cache.get_batch(texts, self.model)
        
        # 2. 找出未命中的文本
        uncached_indices = [i for i, emb in enumerate(cached_embeddings) if emb is None]
        uncached_texts = [texts[i] for i in uncached_indices]
        
        # 3. 如果全部命中，直接返回
        if not uncached_texts:
            logger.debug(f"✅ 缓存命中: {len(texts)}/{len(texts)}")
            return cached_embeddings
        
        # 4. 调用 API 获取未命中的向量
        logger.debug(f"📊 缓存命中: {len(texts) - len(uncached_texts)}/{len(texts)}, 需要请求: {len(uncached_texts)}")
        new_embeddings = await self._embed_batch(uncached_texts)
        
        # 5. 存入缓存
        await self.cache.set_batch(uncached_texts, self.model, new_embeddings)
        
        # 6. 合并结果
        result = cached_embeddings[:]
        for i, idx in enumerate(uncached_indices):
            result[idx] = new_embeddings[i]
        
        return result
    
    async def embed_query(self, query: str) -> List[float]:
        """
        向量化单个查询
        
        Args:
            query: 查询文本
        
        Returns:
            查询向量
        """
        embeddings = await self.embed_texts([query], show_progress=False)
        return embeddings[0]
    
    async def close(self):
        """关闭 HTTP 客户端和缓存"""
        await self.client.aclose()
        if self._cache_initialized:
            await self.cache.close()


# 测试代码
async def test_embedder():
    """测试向量化服务"""
    embedder = EmbedderService()
    
    # 测试单个文本
    text = "如何优化 Python 代码性能？"
    vector = await embedder.embed_query(text)
    
    print(f"文本: {text}")
    print(f"向量维度: {len(vector)}")
    print(f"向量示例（前10维）: {vector[:10]}")
    
    # 测试批量文本
    texts = [
        "Python 性能优化技巧",
        "使用 Cython 加速代码",
        "多进程并发处理"
    ]
    
    vectors = await embedder.embed_texts(texts, show_progress=True)
    print(f"\n批量向量化完成: {len(vectors)} 个向量")
    
    await embedder.close()


if __name__ == "__main__":
    asyncio.run(test_embedder())
