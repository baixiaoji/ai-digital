"""
LLM 服务
调用 AI Builders Chat Completions API
"""
from typing import List, Dict
import json

import httpx

from config import settings, logger


class LLMService:
    """LLM 服务"""
    
    def __init__(self):
        self.api_base = settings.llm.api_base
        self.model = settings.llm.model
        self.api_key = settings.api_key
        self.temperature = settings.llm.temperature
        self.max_tokens = settings.llm.max_tokens
        
        # 创建 HTTP 客户端
        self.client = httpx.AsyncClient(
            base_url=self.api_base,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=httpx.Timeout(
                connect=30.0,
                read=120.0,
                write=60.0,
                pool=10.0
            )
        )
    
    async def generate_answer_stream(
        self, 
        query: str, 
        local_results: List[Dict], 
        web_results: List[Dict]
    ):
        """
        流式生成答案 - 使用 SSE 流式返回
        
        Args:
            query: 用户问题
            local_results: 本地检索结果
            web_results: 网络检索结果
        
        Yields:
            str: 流式生成的文本片段
        """
        try:
            # 构建提示词
            prompt = self._build_prompt(query, local_results, web_results)
            
            logger.info(f"🤖 LLM 流式生成开始 (model={self.model})")
            
            # 调用 Chat Completions API（流式）
            async with self.client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个智能笔记助手，负责根据用户的笔记内容和网络资源回答用户的问题。请基于提供的检索结果生成准确、有用的答案。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "stream": True  # 启用流式响应
                }
            ) as response:
                # 检查状态码（如果失败，手动读取响应体并抛出异常）
                if response.status_code >= 400:
                    error_body = await response.aread()
                    logger.error(f"❌ LLM API 请求失败: {response.status_code}")
                    logger.error(f"❌ 响应体: {error_body.decode('utf-8')}")
                    raise httpx.HTTPStatusError(
                        f"HTTP {response.status_code}",
                        request=response.request,
                        response=response
                    )
                
                logger.info(f"✅ LLM API 连接成功，开始接收流式数据")
                
                # 逐行读取 SSE 流
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    
                    # 移除 "data: " 前缀
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    # 检查结束标记
                    if line == "[DONE]":
                        logger.info(f"✅ LLM 流式生成完成")
                        break
                    
                    try:
                        # 解析 JSON
                        chunk = json.loads(line)
                        
                        # 提取内容
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                yield content
                    
                    except json.JSONDecodeError:
                        logger.warning(f"⚠️ 无法解析 SSE 数据: {line}")
                        continue
        
        except httpx.HTTPStatusError as e:
            # 这个异常已经在上面处理过了（手动读取响应体）
            # 这里只会捕获其他 HTTP 错误
            logger.error(f"❌ LLM API 请求失败: {e}")
            # 降级方案：返回完整答案
            yield self._fallback_answer(query, local_results, web_results)
        
        except Exception as e:
            logger.error(f"❌ LLM 流式答案生成失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # 降级方案：返回完整答案
            yield self._fallback_answer(query, local_results, web_results)
    
    async def generate_answer(
        self, 
        query: str, 
        local_results: List[Dict], 
        web_results: List[Dict]
    ) -> str:
        """
        基于检索结果生成答案（非流式，保留用于兼容）
        
        Args:
            query: 用户问题
            local_results: 本地检索结果
            web_results: 网络检索结果
        
        Returns:
            LLM 生成的答案
        """
        try:
            # 构建提示词
            prompt = self._build_prompt(query, local_results, web_results)
            
            logger.info(f"🤖 LLM 请求开始 (model={self.model}, max_tokens={self.max_tokens})")
            logger.debug(f"📝 Prompt 长度: {len(prompt)} 字符")
            
            # 调用 Chat Completions API
            response = await self.client.post(
                "/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个智能笔记助手，负责根据用户的笔记内容和网络资源回答用户的问题。请基于提供的检索结果生成准确、有用的答案。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            # 提取生成的答案
            choice = data["choices"][0]
            answer = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "unknown")
            
            # 详细日志记录
            logger.info(f"✅ LLM 答案生成成功 (model={self.model})")
            logger.info(f"📊 响应统计: finish_reason={finish_reason}, 答案长度={len(answer)} 字符")
            
            # ⚠️ 重要：检查是否因为 max_tokens 限制而截断
            if finish_reason == "length":
                logger.warning(f"⚠️ 警告：答案因 max_tokens 限制被截断！")
                logger.warning(f"⚠️ 当前 max_tokens={self.max_tokens}，建议增加到至少 {self.max_tokens * 2}")
            
            # 记录 token 使用情况（如果 API 返回）
            if "usage" in data:
                usage = data["usage"]
                logger.info(f"🔢 Token 使用: prompt={usage.get('prompt_tokens', 'N/A')}, "
                          f"completion={usage.get('completion_tokens', 'N/A')}, "
                          f"total={usage.get('total_tokens', 'N/A')}")
            
            return answer
        
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ LLM API 请求失败: {e.response.status_code}")
            return self._fallback_answer(query, local_results, web_results)
        
        except Exception as e:
            logger.error(f"❌ LLM 答案生成失败: {str(e)}")
            return self._fallback_answer(query, local_results, web_results)
    
    def _build_prompt(
        self, 
        query: str, 
        local_results: List[Dict], 
        web_results: List[Dict]
    ) -> str:
        """
        构建 LLM 提示词
        
        Args:
            query: 用户问题
            local_results: 本地检索结果
            web_results: 网络检索结果
        
        Returns:
            提示词字符串
        """
        prompt_parts = [f"用户问题：{query}\n"]
        
        # 添加本地笔记内容
        if local_results:
            prompt_parts.append("\n## 本地笔记相关内容：\n")
            for idx, result in enumerate(local_results[:5], 1):
                title = result.get("title", "未知标题")
                content = result.get("content", "")[:500]  # 限制内容长度
                prompt_parts.append(f"\n{idx}. 【{title}】")
                prompt_parts.append(f"{content}...\n")
        
        # 添加网络资源内容
        if web_results:
            prompt_parts.append("\n## 网络资源相关内容：\n")
            for idx, result in enumerate(web_results[:3], 1):
                title = result.get("title", "未知标题")
                content = result.get("content", "")[:400]  # 限制内容长度
                prompt_parts.append(f"\n{idx}. 【{title}】")
                prompt_parts.append(f"{content}...\n")
        
        # 添加指导
        prompt_parts.append("""
\n## 回答要求：
1. 请基于上述检索结果回答用户的问题
2. 如果本地笔记有相关内容，优先使用本地笔记
3. 如果需要补充信息，可以参考网络资源
4. 回答要清晰、准确、有条理
5. 如果检索结果无法回答问题，请坦诚说明
""")
        
        return ''.join(prompt_parts)
    
    def _fallback_answer(
        self, 
        query: str, 
        local_results: List[Dict], 
        web_results: List[Dict]
    ) -> str:
        """
        降级方案：LLM 失败时返回简单格式化的答案
        
        Args:
            query: 用户问题
            local_results: 本地检索结果
            web_results: 网络检索结果
        
        Returns:
            格式化的答案
        """
        logger.warning("⚠️ LLM 服务不可用，使用降级方案")
        
        answer_parts = [f"关于「{query}」，我找到了以下相关内容：\n"]
        
        if local_results:
            answer_parts.append("\n📚 本地笔记：")
            for idx, result in enumerate(local_results[:5], 1):
                title = result.get("title", "未知标题")
                content = result.get("content", "")[:100]
                answer_parts.append(f"\n{idx}. {title}")
                answer_parts.append(f"   {content}...")
        
        if web_results:
            answer_parts.append("\n\n🌐 网络资源：")
            for idx, result in enumerate(web_results[:3], 1):
                title = result.get("title", "未知标题")
                content = result.get("content", "")[:100]
                answer_parts.append(f"\n{idx}. {title}")
                answer_parts.append(f"   {content}...")
        
        return '\n'.join(answer_parts)
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()


# 测试代码
async def test_llm_service():
    """测试 LLM 服务"""
    service = LLMService()
    
    # 模拟检索结果
    local_results = [
        {
            "title": "Python 性能优化技巧",
            "content": "使用列表推导式比普通循环更快。使用 NumPy 处理大数组。避免过度使用全局变量..."
        }
    ]
    
    web_results = [
        {
            "title": "Python Performance Tips",
            "content": "Use built-in functions and libraries. Profile your code. Use appropriate data structures..."
        }
    ]
    
    query = "如何优化 Python 代码性能？"
    answer = await service.generate_answer(query, local_results, web_results)
    
    print(f"问题: {query}")
    print(f"\n答案:\n{answer}")
    
    await service.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_llm_service())
