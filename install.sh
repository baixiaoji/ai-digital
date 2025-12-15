#!/bin/bash

# AI Digital 安装脚本

echo "📦 安装 AI Digital..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "   请安装 Python 3.10 或更高版本"
    exit 1
fi

echo "✅ Python 版本: $(python3 --version)"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到 Node.js"
    echo "   请安装 Node.js 18 或更高版本"
    exit 1
fi

echo "✅ Node.js 版本: $(node --version)"

# 安装后端依赖
echo ""
echo "📥 安装后端依赖..."
cd backend
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 后端依赖安装失败"
    exit 1
fi

cd ..

# 安装前端依赖
echo ""
echo "📥 安装前端依赖..."
cd frontend
npm install

if [ $? -ne 0 ]; then
    echo "❌ 前端依赖安装失败"
    exit 1
fi

cd ..

# 检查并加载 .env 文件
echo ""
if [ -f ".env" ]; then
    echo "📄 发现 .env 文件，正在加载..."
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$ARK_API_KEY" ]; then
    echo "⚠️  警告: 未设置环境变量 ARK_API_KEY"
    echo "   方式1: export ARK_API_KEY='your-api-key'"
    echo "   方式2: 创建 .env 文件并添加:"
    echo "          ARK_API_KEY=your-api-key"
else
    echo "✅ 环境变量已设置"
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "使用说明："
echo "1. 设置环境变量（如果还没设置）:"
echo "   export ARK_API_KEY='your-api-key'"
echo ""
echo "2. 启动服务:"
echo "   ./start.sh"
echo ""
echo "3. 访问 http://localhost:3000"
