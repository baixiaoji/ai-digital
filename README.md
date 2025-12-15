# 🧠 AI Digital - 智能笔记检索系统

本地 Markdown 笔记的智能检索与关联系统，支持自然语言提问、混合检索、上下文关联，帮你从海量笔记中快速找到想要的信息。

> 🚀 **第一次使用？** → 查看 [3 步快速开始](#-3-步快速开始) 指南

> 📖 **详细说明** → [完整功能介绍](#-核心特性) | [技术架构](#-技术架构) | [配置说明](#-配置说明)

> 🔧 **遇到问题？** → [故障排查](#-故障排查) | [常见问题](#-常见问题)


## ✨ 核心特性

### 🔍 智能检索
- **语义向量检索**: 基于文本嵌入的深度语义匹配
- **关键词匹配**: 精确的字符串匹配与正则搜索
- **混合排序**: 结合时间衰减、相关性、来源权重的智能排序
- **时间敏感**: 3个月内笔记权重 ×1.5，1年前笔记权重 ×0.8

### 🔗 关联分析
- **双链引用**: 自动识别笔记间的 [[ ]] 引用关系
- **标签系统**: 基于 # 标签的自动分类与关联
- **时间线**: 按创建/修改时间的上下文串联
- **网络补充**: 集成 DuckDuckGo 搜索，补充最新网络信息

### 💬 对话界面
- **Chat 交互**: 自然语言提问，类似 ChatGPT 的对话体验
- **流式输出**: 实时生成答案，无需等待
- **工具可视化**: 显示检索、搜索、生成的实时进度

### 📎 精准引用
- **来源标注**: 自动标注信息来自本地笔记或网络
- **Logseq 集成**: 点击本地笔记引用可直接跳转 Logseq 应用
- **网络跳转**: 网络资源支持直接打开浏览器访问


## 🏗️ 技术架构

```
AI Digital Snow
├── backend/          # FastAPI 后端服务
│   ├── services/     # 核心服务（索引、检索、向量化）
│   ├── models/       # 数据模型定义
│   └── database/     # SQLite 元数据存储
├── frontend/         # React + TypeScript 前端
│   └── src/
│       ├── components/  # UI 组件
│       └── services/    # API 服务
├── data/             # 运行时数据目录
│   ├── metadata.db   # SQLite 数据库
│   └── chunks_export/ # 分块导出文件
├── docs/             # 文档目录
├── scripts/          # 辅助脚本
├── config.yaml       # 配置文件
└── .env              # 环境变量
```

### 技术栈
- **前端**: React 18 + TypeScript + Tailwind CSS
- **后端**: Python 3.10 + FastAPI + Uvicorn
- **向量数据库**: FAISS
- **元数据存储**: SQLite
- **Embedding**: text-embedding-3-large (via ai-builders.com)


## 🚀 快速开始

### 前置要求
- ✅ Node.js 18+
- ✅ Python 3.10+
- ✅ API Key: [ai-builders.com](https://space.ai-builders.com) 获取
- ✅ 磁盘空间: 至少 1GB


### 🔖 3 步快速开始

#### 1. 克隆项目
```bash
git clone git@github.com:baixiaoji/ai-digital.git
cd ai-digital
```

#### 2. 安装依赖
```bash
# 一键安装所有依赖
./install.sh
```

#### 3. 设置 API Key 并启动
```bash
# 方式 1: 临时设置（当前终端有效）
export ARK_API_KEY="your-api-key"
./start.sh

# 方式 2: 永久设置（推荐）
echo "ARK_API_KEY=your-api-key" > .env
./start.sh
```

#### 4. 访问应用
打开浏览器访问: **http://localhost:3000**


### 📋 手动安装

```bash
# 1. 安装后端依赖
cd backend
pip install -r requirements.txt

# 2. 安装前端依赖
cd ../frontend
npm install

# 3. 设置 API Key
export ARK_API_KEY="your-api-key"

# 4. 启动后端（终端 1）
cd backend
python main.py

# 5. 启动前端（终端 2）
cd ../frontend
npm run dev
```


## ⚙️ 配置说明

编辑 `config.yaml` 自定义系统行为：

### 笔记目录
```yaml
notes:
  directory: /Users/AJ/logseq-file  # 笔记存放目录
  exclude_patterns:                        # 排除的文件/目录
    - "*.pdf"
    - "archive/*"
    - "drafts/*"
```

### 搜索配置
```yaml
search:
  local_ratio: 0.8  # 本地结果占比 (0-1)
  time_decay:
    recent_boost: 1.5  # 3个月内笔记权重
    old_penalty: 0.8    # 1年前笔记权重
```

### 索引配置
```yaml
indexing:
  chunk_size: 500       # 分块大小 (字符数)
  chunk_overlap: 50     # 块重叠大小
embedding:
  batch_size: 100       # 向量化批次大小
```


## 🛠️ 辅助脚本

### 分块管理工具
scripts 目录提供了用于查看和导出索引分块的工具：

#### 1. view_document_chunks.sh
查看特定文档或所有文档的分块内容：

```bash
# 查看所有文档的分块统计
bash scripts/view_document_chunks.sh

# 查看特定文档的详细分块
bash scripts/view_document_chunks.sh "向 AI 公司 blog 学习"
```

#### 2. export_all_chunks.sh
导出所有分块到文件，支持 JSON/CSV/TXT 格式：

```bash
# 导出为 JSON 格式（默认）
bash scripts/export_all_chunks.sh json

# 导出为 CSV 格式
bash scripts/export_all_chunks.sh csv

# 导出为 TXT 格式
bash scripts/export_all_chunks.sh txt
```

输出文件位置: `./data/chunks_export/`


## 📊 系统管理

### 查看系统状态
```bash
curl http://localhost:8000/api/status | jq
```

响应示例:
```json
{
  "indexed_files": 1234,
  "total_chunks": 5678,
  "last_update": "2024-12-07T12:00:00",
  "index_size_mb": 15.6
}
```

### 重建索引
```bash
# 方式 1: API 调用
curl -X POST http://localhost:8000/api/rebuild-index

# 方式 2: Web 界面
# 点击右上角 "重建索引" 按钮
```


## 🔧 故障排查

### 端口被占用
```bash
# 查找并杀死占用端口的进程
lsof -ti:8000 | xargs kill -9  # 后端
lsof -ti:3000 | xargs kill -9  # 前端
```

### API Key 错误
```bash
# 重新设置 API Key
echo "ARK_API_KEY=your-new-key" > .env
```

### 前端连接失败
```bash
# 检查后端是否正在运行
curl http://localhost:8000/

# 应该返回: {"service":"AI Digital Snow","status":"running","version":"1.0.0"}
```

### 向量化失败
```bash
# 测试 API 连接
cd backend && python tests/test_api.py

# 检查网络
curl -I https://space.ai-builders.com/backend/v1/models
```


## ❓ 常见问题

### Q1: 索引构建需要多长时间？
- 100 个文件: ~2-5 分钟
- 1000 个文件: ~10-20 分钟
- 10000 个文件: ~30-60 分钟

### Q2: 点击引用无法跳转 Logseq？
确保：
1. Logseq 正在运行
2. 执行 `open "logseq://file?path=/path/to/note.md"` 测试 URL Scheme

### Q3: 前端界面空白？
1. 检查后端是否启动: `curl http://localhost:8000`
2. 清除浏览器缓存并刷新: `Ctrl + Shift + R`


## 🎨 界面功能

### 工具栏
- **⚙️ 设置**: 调整本地/网络搜索比例
- **🔄 重建索引**: 更新索引以包含新笔记
- **📊 状态**: 查看已索引文件数和分块数

### 对话区域
- **问题输入**: 支持自然语言提问，Shift+Enter 换行
- **工具监控**: 实时显示本地检索、网络搜索、答案生成进度
- **答案输出**: 流式渲染答案，支持 Markdown 格式
- **引用卡片**: 显示信息来源，点击可跳转

### 引用卡片
- 📄 **本地笔记**: 显示笔记名、标签、创建时间
- 🌐 **网络资源**: 显示网页标题、URL
- **智能排序**: 按相关性和时间自动排序


## 💡 使用技巧

### 精确搜索
```
❌ "学习内容"
✅ "Python 性能优化方法"
```

### 时间查询
```
"最近学习了什么？"  # 自动提升近期笔记权重
"2024年学习的 AI 技术"
```

### 标签搜索
```
"标签 #机器学习 的内容"
"[[Python]] 相关的笔记"
```

### 混合检索
需要最新信息时，在设置中调高网络比例，例如:
```
设置 → 网络比例 50% → "2024年最新 AI 框架"
```




## 🆘 获得帮助

如果遇到问题，请提供以下信息反馈：
1. 操作系统版本
2. Python 和 Node.js 版本
3. 后端终端日志
4. 浏览器控制台截图
