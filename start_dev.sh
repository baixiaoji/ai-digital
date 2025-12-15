#!/bin/bash

# AI Digital 开发模式启动脚本（前后台分离，方便查看日志）

echo "🚀 启动 AI Digital (开发模式)..."
echo ""

# 加载 .env 文件
if [ -f ".env" ]; then
    echo "📄 加载 .env 文件..."
    export $(grep -v '^#' .env | xargs)
fi

# 检查环境变量
if [ -z "$ARK_API_KEY" ]; then
    echo "❌ 错误: 请设置环境变量 ARK_API_KEY"
    exit 1
fi

echo "✅ API Key 已加载"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  启动说明"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "后端将在终端 1 启动（端口 8000）"
echo "前端将在终端 2 启动（端口 3000）"
echo ""
echo "📊 首次启动会自动构建索引："
echo "   - 扫描笔记目录"
echo "   - 解析 Markdown 文件"
echo "   - 分块处理"
echo "   - 向量化（这一步可能需要 5-30 分钟）"
echo "   - 存储到数据库"
echo ""
echo "💡 提示："
echo "   - 索引完成前，前端可能显示连接失败"
echo "   - 请耐心等待后端日志显示 '✅ 索引构建完成'"
echo "   - 然后刷新浏览器页面"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 询问用户
read -p "是否继续？[Y/n] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "📡 请在新终端运行以下命令启动后端："
echo ""
echo "    cd backend && python main.py"
echo ""
echo "⏳ 等待后端索引构建完成后，再启动前端："
echo ""
echo "    cd frontend && npm run dev"
echo ""
echo "访问: http://localhost:3000"
echo ""
