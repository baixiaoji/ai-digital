"""
元数据存储（SQLite）
"""
import aiosqlite
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from config import settings, logger


class MetadataStore:
    """元数据数据库"""
    
    def __init__(self):
        self.db_path = settings.storage.metadata_db
        self.conn: Optional[aiosqlite.Connection] = None
    
    async def initialize(self):
        """初始化数据库"""
        self.conn = await aiosqlite.connect(self.db_path)
        await self._create_tables()
        logger.info(f"✅ 元数据数据库初始化完成: {self.db_path}")
    
    async def _create_tables(self):
        """创建数据表"""
        # 文档表
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                title TEXT,
                created_at TIMESTAMP,
                modified_at TIMESTAMP,
                content_hash TEXT,
                metadata TEXT
            )
        """)
        
        # 分块表
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER,
                start_pos INTEGER,
                end_pos INTEGER,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
            )
        """)
        
        # 标签表
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
            )
        """)
        
        # 双链表
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS backlinks (
                link_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_doc_id TEXT NOT NULL,
                target_page TEXT NOT NULL,
                FOREIGN KEY (source_doc_id) REFERENCES documents(doc_id)
            )
        """)
        
        # 创建索引
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id)")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_doc ON tags(doc_id)")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(tag_name)")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_backlinks_source ON backlinks(source_doc_id)")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_backlinks_target ON backlinks(target_page)")
        
        await self.conn.commit()
    
    async def insert_document(self, doc_id: str, file_path: str, title: str, 
                             created_at: datetime, modified_at: datetime, 
                             content_hash: str, metadata: dict):
        """插入文档"""
        import json
        from datetime import datetime as dt
        
        # 递归转换 metadata 中的 datetime 对象为 ISO 字符串
        def serialize_datetime(obj):
            if isinstance(obj, dt):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetime(item) for item in obj]
            return obj
        
        serialized_metadata = serialize_datetime(metadata)
        
        await self.conn.execute("""
            INSERT OR REPLACE INTO documents 
            (doc_id, file_path, title, created_at, modified_at, content_hash, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, file_path, title, created_at, modified_at, content_hash, json.dumps(serialized_metadata)))
        
        await self.conn.commit()
    
    async def insert_chunk(self, chunk_id: str, doc_id: str, content: str,
                          chunk_index: int, start_pos: int, end_pos: int):
        """插入分块"""
        await self.conn.execute("""
            INSERT OR REPLACE INTO chunks
            (chunk_id, doc_id, content, chunk_index, start_pos, end_pos)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (chunk_id, doc_id, content, chunk_index, start_pos, end_pos))
        await self.conn.commit()
    
    async def insert_tags(self, doc_id: str, tags: List[str]):
        """插入标签"""
        # 先删除旧标签
        await self.conn.execute("DELETE FROM tags WHERE doc_id = ?", (doc_id,))
        
        # 插入新标签
        for tag in tags:
            await self.conn.execute(
                "INSERT INTO tags (doc_id, tag_name) VALUES (?, ?)",
                (doc_id, tag)
            )
        await self.conn.commit()
    
    async def insert_backlinks(self, doc_id: str, backlinks: List[str]):
        """插入双链"""
        # 先删除旧双链
        await self.conn.execute("DELETE FROM backlinks WHERE source_doc_id = ?", (doc_id,))
        
        # 插入新双链
        for target in backlinks:
            await self.conn.execute(
                "INSERT INTO backlinks (source_doc_id, target_page) VALUES (?, ?)",
                (doc_id, target)
            )
        await self.conn.commit()
    
    async def get_document_by_path(self, file_path: str) -> Optional[Dict]:
        """根据路径获取文档"""
        cursor = await self.conn.execute(
            "SELECT * FROM documents WHERE file_path = ?",
            (file_path,)
        )
        row = await cursor.fetchone()
        
        if row:
            import json
            return {
                "doc_id": row[0],
                "file_path": row[1],
                "title": row[2],
                "created_at": row[3],
                "modified_at": row[4],
                "content_hash": row[5],
                "metadata": json.loads(row[6])
            }
        return None
    
    async def get_chunks_by_doc(self, doc_id: str) -> List[Dict]:
        """获取文档的所有分块"""
        cursor = await self.conn.execute(
            "SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_index",
            (doc_id,)
        )
        rows = await cursor.fetchall()
        
        return [
            {
                "chunk_id": row[0],
                "doc_id": row[1],
                "content": row[2],
                "chunk_index": row[3],
                "start_pos": row[4],
                "end_pos": row[5]
            }
            for row in rows
        ]
    
    async def get_documents_by_tag(self, tag_name: str) -> List[str]:
        """根据标签获取文档ID列表"""
        cursor = await self.conn.execute(
            "SELECT DISTINCT doc_id FROM tags WHERE tag_name = ?",
            (tag_name,)
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
    
    async def get_backlinked_documents(self, target_page: str) -> List[str]:
        """获取引用了指定页面的文档列表"""
        cursor = await self.conn.execute(
            "SELECT DISTINCT source_doc_id FROM backlinks WHERE target_page = ?",
            (target_page,)
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
    
    async def get_stats(self) -> Dict:
        """获取统计信息"""
        cursor = await self.conn.execute("SELECT COUNT(*) FROM documents")
        doc_count = (await cursor.fetchone())[0]
        
        cursor = await self.conn.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = (await cursor.fetchone())[0]
        
        cursor = await self.conn.execute("SELECT COUNT(DISTINCT tag_name) FROM tags")
        tag_count = (await cursor.fetchone())[0]
        
        return {
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "total_tags": tag_count
        }
    
    async def close(self):
        """关闭数据库连接"""
        if self.conn:
            await self.conn.close()
