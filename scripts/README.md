# Chunks 查看脚本使用说明

本目录包含用于查看和导出 cache 中 chunk 内容的脚本。

## 📁 脚本列表

### 1. view_document_chunks.sh
查看特定文档或所有文档的 chunks 内容

### 2. export_all_chunks.sh
导出所有 chunks 到文件以便详细审查

---

## 🔍 脚本 1: view_document_chunks.sh

### 功能
- 查看所有文档的 chunks 统计信息
- 查看特定文档的详细 chunks 内容

### 使用方法

#### 查看所有文档的统计（推荐先执行此命令）
```bash
bash scripts/view_document_chunks.sh
```

**输出示例**:
```
📋 所有文档的 Chunks 统计:

文档名                                             Chunk数量    平均长度     最小长度
------------------------------------------------  ----------  ----------  ----------
如何成为一名优秀的程序员.md                          25          285         120
向 AI 公司 blog 学习.md                              1           163         163
Python 最佳实践.md                                  18          312         98
```

#### 查看特定文档的详细内容
```bash
bash scripts/view_document_chunks.sh "向 AI 公司 blog 学习"
```

**输出内容**:
1. Chunks 列表（索引、长度、内容预览）
2. 前 3 个 chunks 的完整内容

---

## 📦 脚本 2: export_all_chunks.sh

### 功能
导出所有 chunks 到文件，支持三种格式：
- **JSON**: 适合程序处理和 jq 查询
- **CSV**: 适合 Excel/Numbers 打开查看
- **TXT**: 适合文本编辑器阅读

### 使用方法

#### 导出为 JSON 格式（默认，推荐）
```bash
bash scripts/export_all_chunks.sh json
```

**输出文件**: `./data/chunks_export/chunks_YYYYMMDD_HHMMSS.json`

**查看方式**:
```bash
# 查看前 3 个 chunks
jq '.[0:3]' ./data/chunks_export/chunks_*.json

# 搜索特定文档
jq '.[] | select(.document_title | contains("AI"))' ./data/chunks_export/chunks_*.json

# 查看某个文档的所有 chunks
jq '.[] | select(.document_title == "向 AI 公司 blog 学习.md")' ./data/chunks_export/chunks_*.json
```

#### 导出为 CSV 格式
```bash
bash scripts/export_all_chunks.sh csv
```

**输出文件**: `./data/chunks_export/chunks_YYYYMMDD_HHMMSS.csv`

**查看方式**:
- 使用 Excel、Numbers 或 Google Sheets 打开
- 命令行查看: `head -20 ./data/chunks_export/chunks_*.csv`

#### 导出为 TXT 格式
```bash
bash scripts/export_all_chunks.sh txt
```

**输出文件**: `./data/chunks_export/chunks_YYYYMMDD_HHMMSS.txt`

**查看方式**:
```bash
# 使用 less 浏览
less ./data/chunks_export/chunks_*.txt

# 搜索关键词
grep -A 10 "AI" ./data/chunks_export/chunks_*.txt

# 使用文本编辑器打开
code ./data/chunks_export/chunks_*.txt
```

---

## 💡 推荐工作流程

### 第一步: 查看统计
```bash
bash scripts/view_document_chunks.sh
```
→ 找到你想查看的文档名

### 第二步: 查看具体文档
```bash
bash scripts/view_document_chunks.sh "文档名关键词"
```
→ 查看该文档的 chunks 是否合理

### 第三步: 导出全部数据（可选）
```bash
bash scripts/export_all_chunks.sh json
```
→ 如果需要详细分析所有数据

---

## 🎯 常见使用场景

### 场景 1: 检查某个文档为什么搜索不到
```bash
# 1. 先看看这个文档有几个 chunks
bash scripts/view_document_chunks.sh "文档名"

# 2. 如果 chunk 太多或太短，可能是分块问题
# 查看详细内容确认
```

### 场景 2: 审查分块质量
```bash
# 导出所有数据
bash scripts/export_all_chunks.sh json

# 查看过短的 chunks
jq '.[] | select(.content_length < 100)' ./data/chunks_export/chunks_*.json

# 查看过长的 chunks
jq '.[] | select(.content_length > 500)' ./data/chunks_export/chunks_*.json
```

### 场景 3: 找出有问题的文档
```bash
# 查看哪些文档的 chunks 特别多
bash scripts/view_document_chunks.sh | head -20
```

---

## 📊 输出文件位置

所有导出的文件都保存在: `./data/chunks_export/`

文件命名格式:
- `chunks_YYYYMMDD_HHMMSS.json`
- `chunks_YYYYMMDD_HHMMSS.csv`
- `chunks_YYYYMMDD_HHMMSS.txt`

---

## ⚠️ 注意事项

1. **数据库路径**: 脚本默认使用 `./data/metadata.db`
2. **文件大小**: 导出的文件可能很大（几十 MB），请确保磁盘空间充足
3. **JSON 查询**: 需要安装 `jq` 工具（macOS: `brew install jq`）
4. **执行权限**: 脚本已设置可执行权限

---

## 🔧 故障排查

### 问题 1: 数据库不存在
```
❌ 数据库不存在: ./data/metadata.db
```

**解决**: 确保你在项目根目录执行脚本，且已经构建过索引

### 问题 2: jq 命令不存在
```
command not found: jq
```

**解决**: 
```bash
brew install jq
```

### 问题 3: 权限不足
```
Permission denied
```

**解决**:
```bash
chmod +x scripts/view_document_chunks.sh
chmod +x scripts/export_all_chunks.sh
```

---

## 📞 需要帮助?

如果脚本无法正常工作，请检查:
1. 是否在项目根目录执行
2. `./data/metadata.db` 是否存在
3. 是否有读取权限

---

**创建时间**: 2025-12-09  
**维护者**: Snow AI CLI
