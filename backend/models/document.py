"""
文档数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class Document:
    """文档对象"""
    file_path: Path
    content: str
    title: str
    created_at: datetime
    modified_at: datetime
    tags: List[str] = field(default_factory=list)
    backlinks: List[str] = field(default_factory=list)  # 双链引用 [[page]]
    metadata: Dict = field(default_factory=dict)
    
    @property
    def file_name(self) -> str:
        return self.file_path.name
    
    @property
    def relative_path(self) -> str:
        """相对于笔记根目录的路径"""
        return str(self.file_path)


@dataclass
class DocumentChunk:
    """文档分块"""
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    start_pos: int
    end_pos: int
    embedding: Optional[List[float]] = None
    
    # 从父文档继承的元数据
    file_path: str = ""
    title: str = ""
    tags: List[str] = field(default_factory=list)
    backlinks: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None


@dataclass
class SearchResult:
    """检索结果"""
    content: str
    file_path: str
    title: str
    score: float
    source: str  # "local" or "web"
    chunk_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    backlinks: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    url: Optional[str] = None  # 网络来源的 URL
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "content": self.content,
            "file_path": self.file_path,
            "title": self.title,
            "score": self.score,
            "source": self.source,
            "chunk_id": self.chunk_id,
            "tags": self.tags,
            "backlinks": self.backlinks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "url": self.url
        }
