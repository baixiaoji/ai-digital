#!/bin/bash
# 导出所有 chunks 到文件进行审查
# 用法: bash scripts/export_all_chunks.sh [输出格式: json|csv|txt]

# 设置数据库路径
DB_PATH="./data/metadata.db"
OUTPUT_DIR="./data/chunks_export"

# 检查数据库是否存在
if [ ! -f "$DB_PATH" ]; then
    echo "❌ 数据库不存在: $DB_PATH"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 获取输出格式（默认为 json）
FORMAT="${1:-json}"

# 生成时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "📦 导出 Chunks 数据"
echo "数据库: $DB_PATH"
echo "输出目录: $OUTPUT_DIR"
echo "格式: $FORMAT"
echo "======================================"
echo ""

case "$FORMAT" in
    json)
        OUTPUT_FILE="$OUTPUT_DIR/chunks_${TIMESTAMP}.json"
        echo "📄 导出为 JSON 格式..."
        
        sqlite3 "$DB_PATH" << 'EOF' > "$OUTPUT_FILE"
.mode json
SELECT 
    c.chunk_id,
    d.title as document_title,
    d.file_path,
    c.chunk_index,
    LENGTH(c.content) as content_length,
    c.content,
    c.start_pos,
    c.end_pos
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
ORDER BY d.title, c.chunk_index;
EOF
        
        echo "✅ 导出完成: $OUTPUT_FILE"
        echo ""
        echo "📊 文件大小: $(du -h "$OUTPUT_FILE" | cut -f1)"
        echo ""
        echo "💡 查看前 3 个 chunks:"
        echo "   jq '.[0:3]' $OUTPUT_FILE"
        echo ""
        echo "💡 搜索特定文档:"
        echo "   jq '.[] | select(.document_title | contains(\"关键词\"))' $OUTPUT_FILE"
        ;;
        
    csv)
        OUTPUT_FILE="$OUTPUT_DIR/chunks_${TIMESTAMP}.csv"
        echo "📄 导出为 CSV 格式..."
        
        sqlite3 "$DB_PATH" << 'EOF' > "$OUTPUT_FILE"
.mode csv
.headers on
SELECT 
    c.chunk_id,
    d.title as document_title,
    d.file_path,
    c.chunk_index,
    LENGTH(c.content) as content_length,
    REPLACE(REPLACE(c.content, char(10), ' '), char(13), ' ') as content_preview,
    c.start_pos,
    c.end_pos
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
ORDER BY d.title, c.chunk_index;
EOF
        
        echo "✅ 导出完成: $OUTPUT_FILE"
        echo ""
        echo "📊 文件大小: $(du -h "$OUTPUT_FILE" | cut -f1)"
        echo ""
        echo "💡 使用 Excel 或 Numbers 打开此文件"
        echo "💡 或使用命令查看: head -20 $OUTPUT_FILE"
        ;;
        
    txt)
        OUTPUT_FILE="$OUTPUT_DIR/chunks_${TIMESTAMP}.txt"
        echo "📄 导出为文本格式..."
        
        sqlite3 "$DB_PATH" << 'EOF' > "$OUTPUT_FILE"
SELECT 
    '================================================================================'
    || char(10) || 'Chunk ID: ' || c.chunk_id
    || char(10) || '文档: ' || d.title
    || char(10) || '文件路径: ' || d.file_path
    || char(10) || 'Chunk 索引: ' || c.chunk_index
    || char(10) || '位置: ' || c.start_pos || ' - ' || c.end_pos
    || char(10) || '内容长度: ' || LENGTH(c.content) || ' 字符'
    || char(10) || '--------------------------------------------------------------------------------'
    || char(10) || c.content
    || char(10) || char(10)
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
ORDER BY d.title, c.chunk_index;
EOF
        
        echo "✅ 导出完成: $OUTPUT_FILE"
        echo ""
        echo "📊 文件大小: $(du -h "$OUTPUT_FILE" | cut -f1)"
        echo ""
        echo "💡 使用任意文本编辑器打开查看"
        echo "💡 或使用命令: less $OUTPUT_FILE"
        echo "💡 搜索关键词: grep -A 10 '关键词' $OUTPUT_FILE"
        ;;
        
    *)
        echo "❌ 不支持的格式: $FORMAT"
        echo "支持的格式: json, csv, txt"
        exit 1
        ;;
esac

echo ""
echo "======================================"
echo ""

# 显示统计信息
echo "📊 数据统计:"
sqlite3 "$DB_PATH" << 'EOF'
SELECT 
    '总文档数: ' || COUNT(DISTINCT doc_id) as stat
FROM chunks
UNION ALL
SELECT 
    '总 Chunks 数: ' || COUNT(*) 
FROM chunks
UNION ALL
SELECT 
    '平均 Chunk 长度: ' || ROUND(AVG(LENGTH(content)), 2) || ' 字符'
FROM chunks
UNION ALL
SELECT 
    '最短 Chunk: ' || MIN(LENGTH(content)) || ' 字符'
FROM chunks
UNION ALL
SELECT 
    '最长 Chunk: ' || MAX(LENGTH(content)) || ' 字符'
FROM chunks;
EOF

echo ""
echo "✅ 导出完成！"
