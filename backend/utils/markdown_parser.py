"""
Markdown 解析器
支持 Logseq 双链语法和标签提取
"""
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

import frontmatter


class MarkdownParser:
    """Markdown 文档解析器"""
    
    # 正则表达式
    BACKLINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')  # [[页面名]]
    TAG_PATTERN = re.compile(r'(?:^|\s)#([a-zA-Z0-9_\u4e00-\u9fa5]+)')  # #标签
    
    @staticmethod
    def parse_file(file_path: Path) -> Tuple[str, Dict]:
        """
        解析 Markdown 文件
        
        Returns:
            (content, metadata) 元组
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        
        # 提取元数据
        metadata = dict(post.metadata)
        content = post.content
        
        # 提取文件时间
        stat = file_path.stat()
        metadata['created_at'] = datetime.fromtimestamp(stat.st_ctime)
        metadata['modified_at'] = datetime.fromtimestamp(stat.st_mtime)
        
        # 提取标题（优先级：frontmatter > 文件名）
        if 'title' not in metadata:
            metadata['title'] = file_path.stem
        
        return content, metadata
    
    @staticmethod
    def extract_backlinks(content: str) -> List[str]:
        """
        提取双链引用 [[页面名]]
        
        Args:
            content: 文档内容
        
        Returns:
            双链列表
        """
        matches = MarkdownParser.BACKLINK_PATTERN.findall(content)
        return list(set(matches))  # 去重
    
    @staticmethod
    def extract_tags(content: str) -> List[str]:
        """
        提取标签 #tag
        
        Args:
            content: 文档内容
        
        Returns:
            标签列表
        """
        matches = MarkdownParser.TAG_PATTERN.findall(content)
        return list(set(matches))  # 去重
    
    @staticmethod
    def clean_content(content: str) -> str:
        """
        清理内容（移除 Markdown 语法）
        
        Args:
            content: 原始内容
        
        Returns:
            清理后的纯文本
        """
        # 移除代码块
        content = re.sub(r'```[\s\S]*?```', '', content)
        
        # 移除行内代码
        content = re.sub(r'`[^`]+`', '', content)
        
        # 移除图片
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        
        # 移除链接（保留文本）
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        
        # 移除双链标记（保留文本）
        content = re.sub(r'\[\[([^\]]+)\]\]', r'\1', content)
        
        # 移除标题标记
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        # 移除加粗/斜体
        content = re.sub(r'\*\*([^\*]+)\*\*', r'\1', content)
        content = re.sub(r'\*([^\*]+)\*', r'\1', content)
        
        # 移除引用标记
        content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)
        
        # 移除列表标记
        content = re.sub(r'^\s*[-*+]\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*\d+\.\s+', '', content, flags=re.MULTILINE)
        
        # 移除多余空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    
    @staticmethod
    def chunk_content(content: str, chunk_size: int = 300, overlap: int = 80, 
                      min_chunk_size: int = 100) -> List[Tuple[str, int, int]]:
        """
        混合策略分块：优先段落 + 智能句子边界 + 小文件保护
        
        策略：
        1. 【新增】若文档长度 < chunk_size，整体作为1个chunk（不分割）
        2. 优先按段落（双换行）分割
        3. 段落过大时，按句子边界细分
        4. 确保 chunk 大小在 [min_chunk_size, chunk_size] 范围
        5. 过滤过短的 chunk
        
        Args:
            content: 文档内容
            chunk_size: 目标块大小（字符数）
            overlap: 重叠字符数
            min_chunk_size: 最小分块大小（字符数）
        
        Returns:
            [(chunk_text, start_pos, end_pos), ...]
        """
        chunks = []
        
        # 🆕 小文件保护：若内容 < chunk_size，整体作为1个chunk
        if len(content) < chunk_size:
            if content.strip():  # 确保不是空内容
                return [(content, 0, len(content))]
            else:
                return []  # 空内容返回空列表
        
        # 第一步：按段落分割
        paragraphs = content.split('\n\n')
        
        current_pos = 0
        accumulated_text = ""
        accumulated_start = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                current_pos += 2  # 跳过 \n\n
                continue
            
            # 如果累积文本为空，开始新的累积
            if not accumulated_text:
                accumulated_text = paragraph
                accumulated_start = current_pos
            else:
                # 尝试加入当前段落
                test_text = accumulated_text + '\n\n' + paragraph
                
                # 如果加入后超过目标大小，处理累积的文本
                if len(test_text) > chunk_size:
                    # 处理之前累积的文本
                    if len(accumulated_text) >= min_chunk_size:
                        # 如果累积文本过大，需要细分
                        if len(accumulated_text) > chunk_size * 1.5:
                            sub_chunks = MarkdownParser._split_large_text(
                                accumulated_text, accumulated_start, 
                                chunk_size, overlap, min_chunk_size
                            )
                            chunks.extend(sub_chunks)
                        else:
                            chunks.append((accumulated_text, accumulated_start, 
                                         accumulated_start + len(accumulated_text)))
                    
                    # 开始新的累积
                    accumulated_text = paragraph
                    accumulated_start = current_pos
                else:
                    # 继续累积
                    accumulated_text = test_text
            
            current_pos += len(paragraph) + 2  # 包括 \n\n
        
        # 处理最后的累积文本
        if accumulated_text and len(accumulated_text) >= min_chunk_size:
            if len(accumulated_text) > chunk_size * 1.5:
                sub_chunks = MarkdownParser._split_large_text(
                    accumulated_text, accumulated_start, 
                    chunk_size, overlap, min_chunk_size
                )
                chunks.extend(sub_chunks)
            else:
                chunks.append((accumulated_text, accumulated_start, 
                             accumulated_start + len(accumulated_text)))
        
        return chunks
    
    @staticmethod
    def _split_large_text(text: str, start_offset: int, chunk_size: int, 
                         overlap: int, min_chunk_size: int) -> List[Tuple[str, int, int]]:
        """
        分割过大的文本（按句子边界）
        
        Args:
            text: 要分割的文本
            start_offset: 文本在原文档中的起始位置
            chunk_size: 目标块大小
            overlap: 重叠大小
            min_chunk_size: 最小块大小
        
        Returns:
            [(chunk_text, start_pos, end_pos), ...]
        """
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            # 理想的结束位置
            ideal_end = min(start + chunk_size, text_len)
            
            # 如果已到达末尾
            if ideal_end >= text_len:
                end = text_len
            else:
                # 在合理范围内查找句子边界
                # 搜索范围：[min_size, ideal_end]
                search_start = max(start + min_chunk_size, ideal_end - 200)
                search_end = ideal_end
                
                # 查找最佳分隔符位置
                best_pos = -1
                # 优先级：中文句号 > 中文标点 > 双换行 > 英文句号
                for delimiter in ['。', '！', '？', '\n\n', '.', '!', '?']:
                    pos = text.rfind(delimiter, search_start, search_end)
                    if pos > best_pos:
                        best_pos = pos
                
                # 如果找到合适的分隔符
                if best_pos != -1:
                    end = best_pos + 1
                else:
                    # 否则在空格处分割
                    space_pos = text.rfind(' ', search_start, search_end)
                    if space_pos != -1:
                        end = space_pos + 1
                    else:
                        # 实在找不到，强制分割
                        end = ideal_end
            
            # 提取 chunk
            chunk_text = text[start:end].strip()
            
            # 过滤过短的 chunk
            if len(chunk_text) >= min_chunk_size:
                chunks.append((
                    chunk_text,
                    start_offset + start,
                    start_offset + end
                ))
            
            # 计算下一个起始位置（带重叠）
            start = end - overlap
            
            # 防止死循环：确保至少前进
            if start <= (chunks[-1][1] - start_offset if chunks else -1):
                start = end
            
            # 如果下一次迭代不会产生足够大的 chunk，直接退出
            if text_len - start < min_chunk_size:
                break
        
        return chunks


class LogseqParser(MarkdownParser):
    """Logseq 专用解析器（扩展功能）"""
    
    @staticmethod
    def parse_properties(content: str) -> Dict:
        """
        解析 Logseq properties
        
        Example:
            - property:: value
            - tags:: #tag1 #tag2
        """
        properties = {}
        pattern = re.compile(r'^\s*-\s*(\w+)::\s*(.+)$', re.MULTILINE)
        
        for match in pattern.finditer(content):
            key = match.group(1)
            value = match.group(2).strip()
            properties[key] = value
        
        return properties
