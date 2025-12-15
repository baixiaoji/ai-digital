"""
索引服务
负责扫描文档、构建索引
"""
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from tqdm import tqdm

from config import settings, logger
from models import Document, DocumentChunk
from utils import MarkdownParser
from database import MetadataStore, VectorStore
from services.embedder import EmbedderService


class IndexerService:
    """索引构建服务"""
    
    def __init__(self):
        self.notes_dir = Path(settings.notes.directory)
        self.exclude_patterns = settings.notes.exclude_patterns
        self.chunk_size = settings.indexing.chunk_size
        self.chunk_overlap = settings.indexing.chunk_overlap
        
        # 初始化组件
        self.metadata_store = MetadataStore()
        self.vector_store = VectorStore()
        self.embedder = EmbedderService()
        self.parser = MarkdownParser()
        
        self._initialized = False
    
    async def _ensure_initialized(self):
        """确保服务已初始化"""
        if not self._initialized:
            await self.metadata_store.initialize()
            self._initialized = True
    
    def is_index_exists(self) -> bool:
        """检查索引是否存在"""
        return (
            settings.storage.metadata_db.exists() and
            settings.storage.vector_index.exists()
        )
    
    async def build_index(self):
        """构建完整索引"""
        await self._ensure_initialized()
        
        logger.info(f"📚 开始扫描笔记目录: {self.notes_dir}")
        
        # 1. 扫描 Markdown 文件
        md_files = self._scan_markdown_files()
        logger.info(f"✅ 找到 {len(md_files)} 个 Markdown 文件")
        
        if not md_files:
            logger.warning("未找到任何 Markdown 文件")
            return
        
        # 2. 解析文档
        documents = []
        for file_path in tqdm(md_files, desc="解析文档"):
            try:
                doc = await self._parse_document(file_path)
                if doc:
                    documents.append(doc)
            except Exception as e:
                logger.error(f"解析文件失败 {file_path}: {str(e)}")
        
        logger.info(f"✅ 成功解析 {len(documents)} 个文档")
        
        # 3. 分块处理
        all_chunks = []
        for doc in tqdm(documents, desc="分块处理"):
            chunks = self._chunk_document(doc)
            all_chunks.extend(chunks)
        
        logger.info(f"✅ 生成 {len(all_chunks)} 个文档块")
        
        # 4. 向量化
        logger.info(f"🔄 开始向量化 {len(all_chunks)} 个文档块...")
        texts = [chunk.content for chunk in all_chunks]
        
        try:
            embeddings = await self.embedder.embed_texts(texts, show_progress=True)
            
            # 将向量赋值给 chunk
            for chunk, embedding in zip(all_chunks, embeddings):
                chunk.embedding = embedding
            
            logger.info(f"✅ 向量化完成")
        except Exception as e:
            logger.error(f"❌ 向量化失败: {str(e)}")
            raise
        
        # 5. 存储到数据库
        self.vector_store.create_index()
        
        for doc in tqdm(documents, desc="存储元数据"):
            await self._store_document(doc)
        
        for chunk in tqdm(all_chunks, desc="存储分块"):
            await self._store_chunk(chunk)
        
        # 6. 构建向量索引
        self.vector_store.add_vectors(all_chunks)
        self.vector_store.save()
        
        logger.info(f"✅ 索引构建完成！")
    
    async def load_index(self):
        """加载现有索引"""
        await self._ensure_initialized()
        
        success = self.vector_store.load()
        if success:
            logger.info("✅ 索引加载成功")
        else:
            logger.error("❌ 索引加载失败")
    
    def _scan_markdown_files(self) -> List[Path]:
        """扫描 Markdown 文件"""
        md_files = []
        
        for pattern in ['**/*.md', '**/*.markdown']:
            for file_path in self.notes_dir.glob(pattern):
                # 检查排除模式
                should_exclude = False
                for exclude in self.exclude_patterns:
                    if exclude.startswith('*.'):
                        # 文件扩展名匹配
                        if file_path.suffix == exclude[1:]:
                            should_exclude = True
                            break
                    elif file_path.match(exclude):
                        should_exclude = True
                        break
                
                if not should_exclude:
                    md_files.append(file_path)
        
        return md_files
    
    async def _parse_document(self, file_path: Path) -> Document:
        """解析单个文档"""
        content, metadata = self.parser.parse_file(file_path)
        
        # 提取双链和标签
        backlinks = self.parser.extract_backlinks(content)
        tags = self.parser.extract_tags(content)
        
        # 清理内容
        clean_content = self.parser.clean_content(content)
        
        return Document(
            file_path=file_path,
            content=clean_content,
            title=metadata.get('title', file_path.stem),
            created_at=metadata.get('created_at'),
            modified_at=metadata.get('modified_at'),
            tags=tags,
            backlinks=backlinks,
            metadata=metadata
        )
    
    def _chunk_document(self, doc: Document) -> List[DocumentChunk]:
        """分块文档"""
        chunks_data = self.parser.chunk_content(
            doc.content,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
            min_chunk_size=settings.indexing.min_chunk_size
        )
        
        doc_id = self._generate_doc_id(doc.file_path)
        
        chunks = []
        for idx, (chunk_text, start_pos, end_pos) in enumerate(chunks_data):
            chunk_id = f"{doc_id}_chunk_{idx}"
            
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=doc_id,
                content=chunk_text,
                chunk_index=idx,
                start_pos=start_pos,
                end_pos=end_pos,
                file_path=str(doc.file_path),
                title=doc.title,
                tags=doc.tags,
                backlinks=doc.backlinks,
                created_at=doc.created_at,
                modified_at=doc.modified_at
            )
            
            chunks.append(chunk)
        
        return chunks
    
    async def _store_document(self, doc: Document):
        """存储文档元数据"""
        doc_id = self._generate_doc_id(doc.file_path)
        content_hash = self._hash_content(doc.content)
        
        await self.metadata_store.insert_document(
            doc_id=doc_id,
            file_path=str(doc.file_path),
            title=doc.title,
            created_at=doc.created_at,
            modified_at=doc.modified_at,
            content_hash=content_hash,
            metadata=doc.metadata
        )
        
        # 存储标签
        if doc.tags:
            await self.metadata_store.insert_tags(doc_id, doc.tags)
        
        # 存储双链
        if doc.backlinks:
            await self.metadata_store.insert_backlinks(doc_id, doc.backlinks)
    
    async def _store_chunk(self, chunk: DocumentChunk):
        """存储分块"""
        await self.metadata_store.insert_chunk(
            chunk_id=chunk.chunk_id,
            doc_id=chunk.document_id,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            start_pos=chunk.start_pos,
            end_pos=chunk.end_pos
        )
    
    def _generate_doc_id(self, file_path: Path) -> str:
        """生成文档ID"""
        # 使用相对路径的 hash
        rel_path = file_path.relative_to(self.notes_dir)
        return hashlib.md5(str(rel_path).encode()).hexdigest()
    
    def _hash_content(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_stats(self) -> Dict:
        """获取索引统计信息"""
        await self._ensure_initialized()
        
        stats = await self.metadata_store.get_stats()
        stats['vector_count'] = self.vector_store.get_size()
        stats['last_update'] = datetime.now().isoformat()
        
        # 计算索引大小
        index_size = 0
        if settings.storage.vector_index.exists():
            index_size = settings.storage.vector_index.stat().st_size
        stats['index_size_mb'] = round(index_size / 1024 / 1024, 2)
        
        stats['total_files'] = stats['total_documents']
        stats['total_chunks'] = stats['total_chunks']
        
        return stats
    
    async def close(self):
        """关闭服务"""
        await self.metadata_store.close()
        await self.embedder.close()
