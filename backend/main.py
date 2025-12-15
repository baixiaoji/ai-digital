"""
AI Digital - 智能笔记检索系统
FastAPI 主入口
"""
import sys
from pathlib import Path
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from services.indexer import IndexerService
from services.retriever import RetrieverService
from config import settings, logger

# 加载环境变量
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 启动 AI Digital 后端服务...")
    
    # 初始化索引服务
    app.state.indexer = IndexerService()
    app.state.retriever = RetrieverService(app.state.indexer)
    
    # 检查是否需要构建索引
    if not app.state.indexer.is_index_exists():
        logger.info("📚 首次运行，开始构建索引...")
        await app.state.indexer.build_index()
        logger.info("✅ 索引构建完成")
    else:
        logger.info("✅ 加载现有索引")
        await app.state.indexer.load_index()
    
    yield
    
    # 关闭服务
    logger.info("🛑 关闭服务...")
    await app.state.indexer.close()


# 创建 FastAPI 应用
app = FastAPI(
    title="AI Digital API",
    description="智能笔记检索系统 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "AI Digital",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    indexer = app.state.indexer
    stats = await indexer.get_stats()
    
    return {
        "indexed_files": stats["total_files"],
        "total_chunks": stats["total_chunks"],
        "last_update": stats["last_update"],
        "index_size_mb": stats["index_size_mb"]
    }


@app.post("/api/search")
async def search(query: str, local_ratio: float = 0.8):
    """
    智能检索接口
    
    Args:
        query: 用户问题
        local_ratio: 本地结果占比 (0-1)
    """
    try:
        retriever = app.state.retriever
        results = await retriever.hybrid_search(query, local_ratio)
        
        return {
            "query": query,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/chat")
async def chat_stream(query: str, local_ratio: float = 0.8):
    """
    流式对话接口（暂时返回普通 JSON，后续改为 SSE）
    
    Args:
        query: 用户问题
        local_ratio: 本地结果占比
    """
    from fastapi.responses import StreamingResponse
    
    async def event_generator():
        # 必须在函数开头导入！
        import json
        from config import logger
        
        retriever = app.state.retriever
        
        logger.info(f"🔍 收到查询请求: '{query}' (local_ratio={local_ratio})")
        
        # 计算本地和网络的 top_k
        total_results = 20
        local_k = int(total_results * local_ratio)
        network_k = int(total_results * (1 - local_ratio))
        
        logger.info(f"📊 检索策略: 本地={local_k}条, 网络={network_k}条 (总计={total_results})")
        
        # Step 1: 工具调用 - 本地检索
        if local_k > 0:
            logger.info(f"🔎 开始本地检索 (top_k={local_k})")
            yield f'data: {json.dumps({"type": "tool_call", "tool": "local_search", "status": "running"})}\n\n'
            local_results = await retriever.local_search(query, top_k=local_k)
            logger.info(f"✅ 本地检索完成: {len(local_results)}条结果")
            # 打印前 5 条本地召回结果，包含内容与元数据预览（使用属性访问）
            logger.info(
                f"🔍 本地召回结果示例: "
                f"{[{'content': r.content[:50], 'metadata': {k: v for k, v in r.to_dict().items() if k != 'content'}} for r in local_results[:5]]}"
            )

            yield f'data: {json.dumps({"type": "tool_call", "tool": "local_search", "status": "completed", "count": len(local_results)})}\n\n'
        else:
            logger.info("⏭️  跳过本地检索 (local_k=0)")
            local_results = []
        
        # Step 2: 工具调用 - 网络搜索
        if network_k > 0:
            logger.info(f"🌐 开始网络搜索 (top_k={network_k})")
            yield f'data: {json.dumps({"type": "tool_call", "tool": "web_search", "status": "running"})}\n\n'
            web_results = await retriever.web_search_async(query, top_k=network_k)
            logger.info(f"✅ 网络搜索完成: {len(web_results)}条结果")
            yield f'data: {json.dumps({"type": "tool_call", "tool": "web_search", "status": "completed", "count": len(web_results)})}\n\n'
        else:
            logger.info("⏭️  跳过网络搜索 (network_k=0)")
            web_results = []
        
        # Step 3: 合并结果
        all_results = local_results + web_results
        logger.info(f"📦 结果汇总: 本地={len(local_results)}, 网络={len(web_results)}, 总计={len(all_results)}")
        
        # Step 4: 使用 LLM 流式生成答案并直接发送
        logger.info("🤖 开始流式生成答案...")
        async for chunk in retriever.format_answer(query, all_results):
            # 直接发送 LLM 生成的文本片段
            if chunk:
                yield f'data: {json.dumps({"type": "text", "content": chunk}, ensure_ascii=False)}\n\n'
        
        # Step 5: 发送引用
        citations = retriever.format_citations(all_results)
        logger.info(f"📚 发送引用数据: {len(citations)}个来源")
        yield f'data: {json.dumps({"type": "citations", "data": citations}, ensure_ascii=False)}\n\n'
        
        # Step 6: 结束标记
        logger.info("✅ 流式响应完成")
        yield f'data: {json.dumps({"type": "done"})}\n\n'
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@app.post("/api/rebuild-index")
async def rebuild_index():
    """重建索引"""
    try:
        indexer = app.state.indexer
        await indexer.build_index()
        return {"status": "success", "message": "索引重建完成"}
    except Exception as e:
        logger.error(f"索引重建失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.server.backend_port,
        reload=True,
        log_level="info"
    )
