"""
配置管理模块
"""
import os
import logging
from pathlib import Path
from typing import List
from dataclasses import dataclass

import yaml
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
CONFIG_FILE = ROOT_DIR / "config.yaml"


@dataclass
class NotesConfig:
    """笔记配置"""
    directory: str
    exclude_patterns: List[str]


@dataclass
class EmbeddingConfig:
    """向量化配置"""
    api_base: str
    model: str
    batch_size: int
    dimension: int


@dataclass
class LLMConfig:
    """LLM 配置"""
    api_base: str
    model: str
    temperature: float
    max_tokens: int


@dataclass
class TimeDecayConfig:
    """时间衰减配置"""
    recent_months: int
    recent_boost: float
    old_years: int
    old_penalty: float


@dataclass
class SearchConfig:
    """检索配置"""
    local_ratio: float
    network_ratio: float
    time_decay: TimeDecayConfig
    top_k_local: int
    top_k_network: int
    similarity_threshold: float
    context_before: int  # 上下文扩展：前N个chunk
    context_after: int   # 上下文扩展：后N个chunk


@dataclass
class IndexingConfig:
    """索引配置"""
    chunk_size: int
    chunk_overlap: int
    min_chunk_size: int  # 最小分块大小
    update_interval: int


@dataclass
class ServerConfig:
    """服务器配置"""
    backend_port: int
    frontend_port: int
    cors_origins: List[str]


@dataclass
class StorageConfig:
    """存储配置"""
    data_dir: Path
    metadata_db: Path
    vector_index: Path
    cache_dir: Path


class Settings:
    """全局配置"""
    
    def __init__(self):
        # 加载 YAML 配置
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 笔记配置
        notes_dir = os.getenv('NOTES_DIRECTORY', config['notes']['directory'])
        self.notes = NotesConfig(
            directory=notes_dir,
            exclude_patterns=config['notes']['exclude_patterns']
        )
        
        # 向量化配置
        self.embedding = EmbeddingConfig(
            api_base=config['embedding']['api_base'],
            model=config['embedding']['model'],
            batch_size=config['embedding']['batch_size'],
            dimension=config['embedding']['dimension']
        )
        
        # LLM 配置
        self.llm = LLMConfig(
            api_base=config['llm']['api_base'],
            model=config['llm']['model'],
            temperature=config['llm']['temperature'],
            max_tokens=config['llm']['max_tokens']
        )
        
        # API Key
        self.api_key = os.getenv('ARK_API_KEY')
        if not self.api_key:
            raise ValueError("请设置环境变量 ARK_API_KEY")
        
        # 检索配置
        time_decay_cfg = config['search']['time_decay']
        self.search = SearchConfig(
            local_ratio=config['search']['local_ratio'],
            network_ratio=config['search']['network_ratio'],
            time_decay=TimeDecayConfig(
                recent_months=time_decay_cfg['recent_months'],
                recent_boost=time_decay_cfg['recent_boost'],
                old_years=time_decay_cfg['old_years'],
                old_penalty=time_decay_cfg['old_penalty']
            ),
            top_k_local=config['search']['top_k_local'],
            top_k_network=config['search']['top_k_network'],
            similarity_threshold=config['search']['similarity_threshold'],
            context_before=config['search'].get('context_before', 3),
            context_after=config['search'].get('context_after', 2)
        )
        
        # 索引配置
        self.indexing = IndexingConfig(
            chunk_size=config['indexing']['chunk_size'],
            chunk_overlap=config['indexing']['chunk_overlap'],
            min_chunk_size=config['indexing'].get('min_chunk_size', 100),
            update_interval=config['indexing']['update_interval']
        )
        
        # 服务器配置
        self.server = ServerConfig(
            backend_port=config['server']['backend_port'],
            frontend_port=config['server']['frontend_port'],
            cors_origins=config['server']['cors_origins']
        )
        
        # 存储配置
        data_dir = ROOT_DIR / config['storage']['data_dir']
        data_dir.mkdir(exist_ok=True)
        
        self.storage = StorageConfig(
            data_dir=data_dir,
            metadata_db=data_dir / config['storage']['metadata_db'],
            vector_index=data_dir / config['storage']['vector_index'],
            cache_dir=data_dir / config['storage']['cache_dir']
        )
        
        # 创建缓存目录
        self.storage.cache_dir.mkdir(exist_ok=True)


# 全局配置实例
settings = Settings()

# 日志配置
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ai-digital-snow')
