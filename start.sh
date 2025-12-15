#!/bin/bash

# AI Digital 启动脚本

echo "🚀 启动 AI Digital..."

# 加载 .env 文件（如果存在）
if [ -f ".env" ]; then
    echo "📄 加载 .env 文件..."
    export $(grep -v '^#' .env | xargs)
fi

# 检查环境变量
if [ -z "$ARK_API_KEY" ]; then
    echo "❌ 错误: 请设置环境变量 ARK_API_KEY"
    echo ""
    echo "方式1: 命令行设置"
    echo "   export ARK_API_KEY='your-api-key'"
    echo ""
    echo "方式2: 创建 .env 文件"
    echo "   echo 'ARK_API_KEY=your-api-key' > .env"
    exit 1
fi

echo "✅ API Key 已加载"

# 启动后端
echo "📡 启动后端服务 (端口 8000)..."
cd backend
python main.py &
BACKEND_PID=$!

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 3

# 启动前端
echo "🎨 启动前端服务 (端口 3000)..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ 服务已启动！"
echo "   后端: http://localhost:8000"
echo "   前端: http://localhost:3000"
echo ""
echo "按 Ctrl+C 停止服务"

# 等待用户中断
trap "echo '🛑 停止服务...'; kill $BACKEND_PID $FRONTEND_PID; exit 0" INT

wait
