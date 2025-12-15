"""
检索服务
混合检索：本地向量检索 + 网络搜索
"""
from datetime import datetime, timedelta
from typing import List, Dict
import asyncio

from config import settings, logger
from models import SearchResult
from services.embedder import EmbedderService
from services.web_search import WebSearchService
from services.llm import LLMService


class RetrieverService:
    """检索服务"""
    
    def __init__(self, indexer):
        self.indexer = indexer
        self.embedder = EmbedderService()
        self.web_search = WebSearchService()
        self.llm = LLMService()
        
        # 检索配置
        self.time_decay_config = settings.search.time_decay
        self.similarity_threshold = settings.search.similarity_threshold
    
    async def hybrid_search(self, query: str, local_ratio: float = None) -> List[Dict]:
        """
        混合检索（本地 + 网络）
        
        Args:
            query: 用户查询
            local_ratio: 本地结果占比（None 则使用配置）
        
        Returns:
            排序后的检索结果列表
        """
        if local_ratio is None:
            local_ratio = settings.search.local_ratio
        
        network_ratio = 1 - local_ratio
        
        # 计算本地和网络的 top_k
        total_results = 20
        local_k = int(total_results * local_ratio)
        network_k = int(total_results * network_ratio)
        
        logger.info(f"🔍 混合检索: local_ratio={local_ratio:.2f}, local_k={local_k}, network_k={network_k}")
        
        # 并发执行本地和网络检索（优化：local_k=0 时跳过本地检索）
        tasks = []
        if local_k > 0:
            tasks.append(self.local_search(query, top_k=local_k))
        else:
            logger.info("⏩ 跳过本地检索 (local_ratio=0)")
            tasks.append(asyncio.create_task(asyncio.sleep(0)))  # 占位任务
        
        if network_k > 0:
            tasks.append(self.web_search_async(query, top_k=network_k))
        else:
            logger.info("⏩ 跳过网络检索 (network_ratio=0)")
            tasks.append(asyncio.create_task(asyncio.sleep(0)))  # 占位任务
        
        results = await asyncio.gather(*tasks)
        
        # 提取结果（处理占位任务）
        local_results = results[0] if local_k > 0 and isinstance(results[0], list) else []
        web_results = results[1] if network_k > 0 and len(results) > 1 and isinstance(results[1], list) else []
        
        # 合并结果
        all_results = local_results + web_results
        
        # 按分数排序
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # 转换为字典
        return [result.to_dict() for result in all_results]
    
    async def local_search(self, query: str, top_k: int = 20) -> List[SearchResult]:
        """
        本地向量检索（带上下文扩展）
        
        Args:
            query: 查询文本
            top_k: 返回数量
        
        Returns:
            检索结果列表
        """
        # 防御：top_k <= 0 直接返回空
        if top_k <= 0:
            logger.info(f"⏩ 本地检索跳过 (top_k={top_k})")
            return []
        
        logger.info(f"🔍 本地检索: query=\"{query}\", top_k={top_k}")
        
        # 1. 向量化查询
        query_vector = await self.embedder.embed_query(query)
        
        # 2. 向量检索（扩大搜索范围以便后续过滤）
        vector_results = self.indexer.vector_store.search(query_vector, top_k=top_k * 3)
        
        if not vector_results:
            logger.warning("未找到相似文档")
            return []
        
        logger.info(f"📊 向量检索返回 {len(vector_results)} 条候选结果")
        
        # 3. 获取分块详细信息（带上下文扩展）
        results = []
        for chunk_id, similarity_score in vector_results:
            # 从元数据库获取分块信息（带上下文）
            chunk_data = await self._get_chunk_data_with_context(
                chunk_id,
                context_before=settings.search.context_before,
                context_after=settings.search.context_after
            )
            
            if chunk_data and similarity_score >= self.similarity_threshold:
                # 应用时间衰减
                time_weight = self._calculate_time_decay(chunk_data['modified_at'])
                
                # 🆕 标题匹配加权
                title_boost = self._calculate_title_boost(query, chunk_data.get('title', ''))
                
                # 综合得分：向量相似度 * 时间权重 * 标题权重
                final_score = similarity_score * time_weight * title_boost
                
                result = SearchResult(
                    content=chunk_data['extended_content'],  # 使用扩展后的内容
                    file_path=chunk_data['file_path'],
                    title=chunk_data['title'],
                    score=final_score,
                    source="local",
                    chunk_id=chunk_id,
                    tags=chunk_data.get('tags', []),
                    backlinks=chunk_data.get('backlinks', []),
                    created_at=chunk_data.get('created_at')
                )
                
                results.append(result)
        
        logger.info(f"🔍 相似度过滤: {len(vector_results)} → {len(results)} (阈值={self.similarity_threshold})")
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        # 返回 top_k
        results = results[:top_k]
        
        # 打印详细检索结果（方便调试）
        logger.info(f"✅ 本地检索完成，返回 {len(results)} 条结果")
        if results:
            logger.info("📋 本地召回详情:")
            for i, r in enumerate(results, 1):
                content_preview = r.content[:150].replace('\n', ' ')
                logger.info(f"  [{i}] 文件: {r.file_path}")
                logger.info(f"      分数: {r.score:.4f} | Chunk: {r.chunk_id}")
                logger.info(f"      内容: {content_preview}...")
        
        return results

    
    async def web_search_async(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        网络搜索
        
        Args:
            query: 查询文本
            top_k: 返回数量
        
        Returns:
            网络检索结果列表
        """
        logger.info(f"🌐 网络检索: {query}")
        
        web_results = await self.web_search.search(query, max_results=top_k)
        
        results = []
        for item in web_results:
            # 使用 snippet + content 作为内容
            content = item.get('content', '') or item.get('snippet', '')
            
            result = SearchResult(
                content=content,
                file_path="",
                title=item.get('title', ''),
                score=0.5,  # 网络结果固定分数
                source="web",
                url=item.get('url', '')
            )
            
            results.append(result)
        
        logger.info(f"✅ 网络检索完成，返回 {len(results)} 条结果")
        return results
    
    async def _get_chunk_data(self, chunk_id: str) -> Dict:
        """获取分块数据"""
        # 从元数据库查询
        doc_id = chunk_id.rsplit('_chunk_', 1)[0]
        
        cursor = await self.indexer.metadata_store.conn.execute(
            "SELECT * FROM chunks WHERE chunk_id = ?",
            (chunk_id,)
        )
        chunk_row = await cursor.fetchone()
        
        if not chunk_row:
            return None
        
        # 获取文档信息
        cursor = await self.indexer.metadata_store.conn.execute(
            "SELECT * FROM documents WHERE doc_id = ?",
            (doc_id,)
        )
        doc_row = await cursor.fetchone()
        
        if not doc_row:
            return None
        
        # 获取标签
        cursor = await self.indexer.metadata_store.conn.execute(
            "SELECT tag_name FROM tags WHERE doc_id = ?",
            (doc_id,)
        )
        tags = [row[0] for row in await cursor.fetchall()]
        
        # 获取双链
        cursor = await self.indexer.metadata_store.conn.execute(
            "SELECT target_page FROM backlinks WHERE source_doc_id = ?",
            (doc_id,)
        )
        backlinks = [row[0] for row in await cursor.fetchall()]
        
        # 解析时间
        from dateutil import parser as date_parser
        created_at = date_parser.parse(doc_row[3]) if doc_row[3] else None
        modified_at = date_parser.parse(doc_row[4]) if doc_row[4] else None
        
        return {
            "content": chunk_row[2],
            "file_path": doc_row[1],
            "title": doc_row[2],
            "tags": tags,
            "backlinks": backlinks,
            "created_at": created_at,
            "modified_at": modified_at
        }

    
    async def _get_chunk_data_with_context(self, chunk_id: str, 
                                           context_before: int = 3,
                                           context_after: int = 2) -> Dict:
        """
        获取分块数据并包含上下文
        
        Args:
            chunk_id: chunk ID
            context_before: 包含前面 N 个 chunk
            context_after: 包含后面 N 个 chunk
        
        Returns:
            包含 extended_content 的 chunk 数据
        """
        # 获取当前 chunk 的数据
        current_chunk = await self._get_chunk_data(chunk_id)
        if not current_chunk:
            return None
        
        # 解析 doc_id 和 chunk_index
        doc_id, chunk_idx_str = chunk_id.rsplit('_chunk_', 1)
        chunk_idx = int(chunk_idx_str)
        
        # 获取上下文 chunks
        context_contents = []
        
        # 前面的 chunks
        for i in range(chunk_idx - context_before, chunk_idx):
            if i >= 0:
                ctx_id = f"{doc_id}_chunk_{i}"
                cursor = await self.indexer.metadata_store.conn.execute(
                    "SELECT content FROM chunks WHERE chunk_id = ?",
                    (ctx_id,)
                )
                row = await cursor.fetchone()
                if row:
                    context_contents.append(row[0])
        
        # 当前 chunk
        context_contents.append(current_chunk['content'])
        
        # 后面的 chunks
        for i in range(chunk_idx + 1, chunk_idx + context_after + 1):
            ctx_id = f"{doc_id}_chunk_{i}"
            cursor = await self.indexer.metadata_store.conn.execute(
                "SELECT content FROM chunks WHERE chunk_id = ?",
                (ctx_id,)
            )
            row = await cursor.fetchone()
            if row:
                context_contents.append(row[0])
            else:
                break  # 没有更多 chunk 了
        
        # 合并内容
        current_chunk['extended_content'] = '\n\n'.join(context_contents)
        
        return current_chunk

    
    def _calculate_title_boost(self, query: str, title: str) -> float:
        """
        计算标题匹配加权
        
        策略：
        1. 提取查询关键词（中文按字符，英文按单词）
        2. 计算关键词在标题中的覆盖率
        3. 返回权重倍数（1.0 ~ 2.0）
        
        Args:
            query: 查询文本
            title: 文档标题
        
        Returns:
            权重倍数
        """
        if not title or not query:
            return 1.0
        
        # 转小写
        query_lower = query.lower()
        title_lower = title.lower()
        
        # 停用词
        stopwords = {'的', '了', '和', '是', '在', '有', '我', '你', '他', '她', '它',
                     'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     '告诉', '笔记', '中', '哪些', '相关', '信息', '关于', '有关', '么', '吗'}
        
        # 提取关键词：分割成单词和字符
        query_keywords = set()
        
        # 1. 按空格/标点分割（处理英文单词）
        import re
        tokens = re.split(r'[\s，。！？、]+', query_lower)
        
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            
            # 如果是英文单词（长度>=2）
            if token.isascii() and len(token) >= 2:
                if token not in stopwords:
                    query_keywords.add(token)
            # 如果包含中文，提取2字词和3字词
            else:
                # 提取连续的非停用词中文片段
                for i in range(len(token)):
                    # 2字词
                    if i + 2 <= len(token):
                        word = token[i:i+2]
                        if word not in stopwords and not word.isascii():
                            query_keywords.add(word)
                    # 3字词
                    if i + 3 <= len(token):
                        word = token[i:i+3]
                        if word not in stopwords and not word.isascii():
                            query_keywords.add(word)
        
        if not query_keywords:
            return 1.0
        
        # 计算匹配度
        matched_count = 0
        for keyword in query_keywords:
            if keyword in title_lower:
                matched_count += 1
        
        # 计算覆盖率
        coverage = matched_count / len(query_keywords)
        
        # 返回权重：
        # 0% 匹配 → 1.0x (不加权)
        # 50% 匹配 → 1.5x
        # 100% 匹配 → 2.0x (翻倍)
        boost = 1.0 + coverage
        
        if boost > 1.1:  # 只记录有明显加权的情况
            logger.info(f"📌 标题匹配加权: '{title}' -> {boost:.2f}x (覆盖率: {coverage:.0%})")
        
        return boost
    
    def _calculate_time_decay(self, modified_at) -> float:
        """
        计算时间衰减权重
        
        Args:
            modified_at: 修改时间
        
        Returns:
            权重倍数
        """
        if not modified_at:
            return 1.0
        
        now = datetime.now()
        delta = now - modified_at
        
        # 近期（3个月内）：权重 × 1.5
        if delta < timedelta(days=self.time_decay_config.recent_months * 30):
            return self.time_decay_config.recent_boost
        
        # 旧文档（1年前）：权重 × 0.8
        if delta > timedelta(days=self.time_decay_config.old_years * 365):
            return self.time_decay_config.old_penalty
        
        # 中间时期：线性衰减
        return 1.0
    
    async def format_answer(self, query: str, results: List[SearchResult]):
        """
        流式生成答案（手动分块）
        
        Args:
            query: 用户问题
            results: 检索结果列表
        
        Yields:
            str: 文本片段（按字符分块）
        """
        # 转换结果为字典格式
        local_dicts = [r.to_dict() for r in results if r.source == 'local']
        web_dicts = [r.to_dict() for r in results if r.source == 'web']
        
        logger.info(f"🎨 开始生成答案: 本地结果={len(local_dicts)}条, 网络结果={len(web_dicts)}条")
        
        # 调用非流式 LLM API 获取完整答案
        try:
            answer = await self.llm.generate_answer(query, local_dicts, web_dicts)
            
            logger.info(f"📝 答案生成完成，开始流式分块发送 (总长度={len(answer)}字符)")
            
            # 手动分块发送（每次 10 个字符）
            chunk_size = 10
            total_chunks = (len(answer) + chunk_size - 1) // chunk_size
            
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i + chunk_size]
                chunk_num = i // chunk_size + 1
                logger.debug(f"📤 发送分块 {chunk_num}/{total_chunks}: {len(chunk)}字符")
                yield chunk
                # 稍微延迟以模拟流式效果
                await asyncio.sleep(0.05)
            
            logger.info(f"✅ 流式答案发送完成 ({total_chunks}个分块)")
        
        except Exception as e:
            logger.error(f"❌ 答案生成失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # 降级方案：简单格式化
            fallback = self.llm._fallback_answer(query, local_dicts, web_dicts)
            logger.warning(f"⚠️ 使用降级方案生成答案 (长度={len(fallback)}字符)")
            yield fallback
    
    def format_citations(self, results: List[SearchResult]) -> List[Dict]:
        """
        格式化引用（按文件去重）
        
        Args:
            results: 检索结果
        
        Returns:
            引用列表（同一文件只保留得分最高的）
        """
        # 按 file_path 分组，保留每个文件得分最高的结果
        file_map = {}  # file_path -> (result, max_score)
        
        for result in results:
            # 网络结果使用 URL 作为唯一标识
            key = result.url if result.source == "web" else result.file_path
            
            if not key:
                continue
            
            # 如果是新文件，或分数更高，则更新
            if key not in file_map or result.score > file_map[key][1]:
                file_map[key] = (result, result.score)
        
        # 按原始顺序排序（保持得分顺序）
        unique_results = [item[0] for item in sorted(file_map.values(), key=lambda x: x[1], reverse=True)]
        
        # 构建引用
        citations = []
        for idx, result in enumerate(unique_results, 1):
            citation = {
                "id": idx,
                "title": result.title,
                "source": result.source,
            }
            
            if result.source == "local":
                citation["file_path"] = result.file_path
                citation["tags"] = result.tags
                citation["created_at"] = result.created_at.isoformat() if result.created_at else None
            else:
                citation["url"] = result.url
            
            citations.append(citation)
        
        logger.info(f"📚 引用去重: {len(results)} 条结果 → {len(citations)} 个唯一文件/URL")
        return citations
