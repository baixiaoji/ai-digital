#!/bin/bash

# 测试流式输出的 curl 脚本

echo "============================================================"
echo "测试流式输出 JSON 格式"
echo "============================================================"
echo ""
echo "⚠️  请确保后端服务已启动: cd backend && python main.py"
echo ""
echo "正在发送请求..."
echo ""

# 使用 curl 测试流式输出
curl -N -X POST "http://localhost:8000/api/chat?query=如何使用git+worktree&local_ratio=0.8" \
  2>/dev/null | while IFS= read -r line; do
    # 跳过空行
    if [ -z "$line" ]; then
        continue
    fi
    
    # 解析 SSE 格式
    if [[ "$line" == data:* ]]; then
        # 提取 JSON 部分
        json_part="${line#data: }"
        
        # 尝试解析 JSON（使用 python 验证）
        if echo "$json_part" | python3 -m json.tool >/dev/null 2>&1; then
            # JSON 格式正确
            event_type=$(echo "$json_part" | python3 -c "import sys, json; print(json.load(sys.stdin).get('type', 'unknown'))")
            echo "✅ [${event_type}] JSON 格式正确"
            
            # 如果是文本块，显示内容预览
            if [ "$event_type" == "text" ]; then
                content=$(echo "$json_part" | python3 -c "import sys, json; print(json.load(sys.stdin).get('content', '')[:50])")
                echo "   内容: ${content}..."
            fi
        else
            # JSON 格式错误
            echo "❌ JSON 格式错误:"
            echo "   ${json_part:0:100}..."
        fi
    fi
done

echo ""
echo "============================================================"
echo "测试完成"
echo "============================================================"
