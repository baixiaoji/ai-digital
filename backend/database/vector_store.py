"""
向量存储（FAISS）
"""
import pickle
from typing import List, Tuple, Optional
from pathlib import Path

import numpy as np
import faiss

from config import settings, logger
from models import DocumentChunk


class VectorStore:
    """FAISS 向量数据库"""
    
    def __init__(self):
        self.index_path = settings.storage.vector_index
        self.dimension = settings.embedding.dimension
        
        self.index: Optional[faiss.Index] = None
        self.chunk_ids: List[str] = []  # chunk_id 映射
    
    def create_index(self):
        """创建新索引"""
        # 使用 Inner Product (IP) 相似度
        # 注意：需要对向量进行归一化
        self.index = faiss.IndexFlatIP(self.dimension)
        self.chunk_ids = []
        logger.info(f"✅ 创建新的 FAISS 索引 (维度: {self.dimension})")
    
    def add_vectors(self, chunks: List[DocumentChunk]):
        """
        添加向量到索引
        
        Args:
            chunks: 包含 embedding 的分块列表
        """
        if not chunks:
            return
        
        # 提取向量
        vectors = np.array([chunk.embedding for chunk in chunks], dtype=np.float32)
        
        # L2 归一化（用于 Inner Product）
        faiss.normalize_L2(vectors)
        
        # 添加到索引
        self.index.add(vectors)
        
        # 记录 chunk_id 映射
        self.chunk_ids.extend([chunk.chunk_id for chunk in chunks])
        
        logger.info(f"✅ 添加 {len(chunks)} 个向量到索引")
    
    def search(self, query_vector: List[float], top_k: int = 20) -> List[Tuple[str, float]]:
        """
        向量检索
        
        Args:
            query_vector: 查询向量
            top_k: 返回 Top-K 结果
        
        Returns:
            [(chunk_id, score), ...]
        """
        if not self.index or self.index.ntotal == 0:
            logger.warning("索引为空，无法检索")
            return []
        
        # 归一化查询向量
        query = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(query)
        
        # 检索
        scores, indices = self.index.search(query, min(top_k, self.index.ntotal))
        
        # 构建结果
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and idx < len(self.chunk_ids):
                results.append((self.chunk_ids[idx], float(score)))
        
        return results
    
    def save(self):
        """保存索引到磁盘"""
        if not self.index:
            logger.warning("索引未初始化，跳过保存")
            return
        
        # 保存 FAISS 索引
        faiss.write_index(self.index, str(self.index_path))
        
        # 保存 chunk_id 映射
        mapping_path = self.index_path.with_suffix('.pkl')
        with open(mapping_path, 'wb') as f:
            pickle.dump(self.chunk_ids, f)
        
        logger.info(f"✅ 索引已保存: {self.index_path}")
    
    def load(self):
        """从磁盘加载索引"""
        if not self.index_path.exists():
            logger.warning(f"索引文件不存在: {self.index_path}")
            return False
        
        # 加载 FAISS 索引
        self.index = faiss.read_index(str(self.index_path))
        
        # 加载 chunk_id 映射
        mapping_path = self.index_path.with_suffix('.pkl')
        with open(mapping_path, 'rb') as f:
            self.chunk_ids = pickle.load(f)
        
        logger.info(f"✅ 索引已加载: {self.index_path} (共 {self.index.ntotal} 个向量)")
        return True
    
    def is_empty(self) -> bool:
        """判断索引是否为空"""
        return self.index is None or self.index.ntotal == 0
    
    def get_size(self) -> int:
        """获取索引大小"""
        if self.index:
            return self.index.ntotal
        return 0
