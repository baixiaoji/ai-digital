#!/bin/bash
# 查看特定文档的所有 chunks
# 用法: bash scripts/view_document_chunks.sh [文档名关键词]

# 设置数据库路径
DB_PATH="./data/metadata.db"

# 检查数据库是否存在
if [ ! -f "$DB_PATH" ]; then
    echo "❌ 数据库不存在: $DB_PATH"
    exit 1
fi

# 获取搜索关键词（默认为空，显示所有文档）
SEARCH_KEYWORD="${1:-}"

echo "📊 查看文档的 Chunks 内容"
echo "数据库: $DB_PATH"
echo "======================================"
echo ""

if [ -z "$SEARCH_KEYWORD" ]; then
    # 如果没有提供关键词，显示所有文档的统计
    echo "📋 所有文档的 Chunks 统计:"
    echo ""
    
    sqlite3 "$DB_PATH" << 'EOF'
.mode column
.headers on
.width 50 12 12 12

SELECT 
    d.title as 文档名,
    COUNT(c.chunk_id) as Chunk数量,
    AVG(LENGTH(c.content)) as 平均长度,
    MIN(LENGTH(c.content)) as 最小长度
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
GROUP BY d.doc_id
ORDER BY COUNT(c.chunk_id) DESC;
EOF

    echo ""
    echo "💡 提示: 使用 'bash scripts/view_document_chunks.sh \"关键词\"' 查看具体文档的详细内容"
    
else
    # 显示匹配文档的详细 chunks
    echo "🔍 搜索关键词: '$SEARCH_KEYWORD'"
    echo ""
    
    sqlite3 "$DB_PATH" << EOF
.mode column
.headers on
.width 30 8 10 100

SELECT 
    c.chunk_id as ChunkID,
    c.chunk_index as 索引,
    LENGTH(c.content) as 长度,
    SUBSTR(c.content, 1, 150) || '...' as 内容预览
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
WHERE d.title LIKE '%${SEARCH_KEYWORD}%'
ORDER BY c.chunk_index;
EOF

    echo ""
    echo "======================================"
    
    # 显示完整内容（前 3 个 chunks）
    echo ""
    echo "📄 详细内容（前 3 个 chunks）:"
    echo ""
    
    sqlite3 "$DB_PATH" << EOF | head -100
SELECT 
    '========== Chunk #' || c.chunk_index || ' =========='
    || char(10) || 'Chunk ID: ' || c.chunk_id
    || char(10) || '文档: ' || d.title
    || char(10) || '长度: ' || LENGTH(c.content) || ' 字符'
    || char(10) || char(10) || '内容:'
    || char(10) || c.content
    || char(10) || char(10)
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
WHERE d.title LIKE '%${SEARCH_KEYWORD}%'
ORDER BY c.chunk_index
LIMIT 3;
EOF
fi

echo ""
echo "✅ 查询完成"
