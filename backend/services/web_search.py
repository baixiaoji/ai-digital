"""
网络搜索服务
使用 DuckDuckGo API (新版 ddgs SDK)
"""
import asyncio
from typing import List, Dict
from datetime import datetime

try:
    from ddgs import DDGS
except ImportError:
    # 兼容旧包名
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        from duckduckgo_search import AsyncDDGS as DDGS

import httpx
from bs4 import BeautifulSoup

from config import logger, settings


class WebSearchService:
    """网络搜索服务"""
    
    def __init__(self):
        self.cache_dir = settings.storage.cache_dir
        self.max_content_length = 1000  # 网页内容最大长度
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        搜索网络内容（使用新版 DuckDuckGo SDK）
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
        
        Returns:
            [{"title": ..., "url": ..., "snippet": ..., "content": ...}, ...]
        """
        try:
            # 输入验证
            if not query or not query.strip():
                logger.warning("搜索查询为空")
                return []
            
            # 限制查询长度和结果数
            query = query.strip()[:500]
            max_results = min(max(1, max_results), 10)
            
            logger.info(f"🌐 开始网络搜索: {query}")
            
            # 使用新版 DDGS API（同步转异步）
            results = await self._ddgs_search(query, max_results)
            
            if not results:
                logger.warning(f"网络搜索无结果: {query}")
                return []
            
            # 抓取页面内容（并发）
            tasks = [self._fetch_content(item) for item in results]
            results = await asyncio.gather(*tasks)
            
            logger.info(f"✅ 网络搜索完成，返回 {len(results)} 条结果")
            return results
        
        except Exception as e:
            logger.error(f"❌ 网络搜索失败: {str(e)}")
            return []
    
    async def _ddgs_search(self, query: str, max_results: int) -> List[Dict]:
        """
        调用 DuckDuckGo 搜索（同步 API 转异步）
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
        
        Returns:
            搜索结果列表
        """
        def _sync_search():
            """同步搜索逻辑"""
            results = []
            
            try:
                # 尝试全球搜索
                with DDGS() as ddgs:
                    search_results = ddgs.text(
                        query,
                        max_results=max_results,
                        region="wt-wt",
                        safesearch="moderate"
                    )
                    
                    # ddgs.text() 返回生成器，需要转为列表
                    for result in search_results:
                        results.append({
                            "title": result.get("title", ""),
                            "url": result.get("href", ""),
                            "snippet": result.get("body", ""),
                            "source": "web",
                            "fetched_at": datetime.now().isoformat()
                        })
                
                # 如果无结果，尝试美国区域
                if not results:
                    with DDGS() as ddgs:
                        search_results = ddgs.text(
                            query,
                            max_results=max_results,
                            region="us-en",
                            safesearch="moderate"
                        )
                        
                        for result in search_results:
                            results.append({
                                "title": result.get("title", ""),
                                "url": result.get("href", ""),
                                "snippet": result.get("body", ""),
                                "source": "web",
                                "fetched_at": datetime.now().isoformat()
                            })
            
            except Exception as e:
                logger.error(f"DuckDuckGo 搜索异常: {str(e)}")
            
            return results
        
        # 在线程池中运行同步代码（避免阻塞异步事件循环）
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _sync_search)
        
        return results
    
    async def _fetch_content(self, item: Dict) -> Dict:
        """
        抓取网页内容
        
        Args:
            item: 搜索结果项
        
        Returns:
            补充了 content 字段的结果
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(item["url"])
                response.raise_for_status()
                
                # 解析 HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 移除脚本和样式
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # 提取文本
                text = soup.get_text()
                
                # 清理文本
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                # 截断内容
                if len(text) > self.max_content_length:
                    text = text[:self.max_content_length] + "..."
                
                item["content"] = text
                logger.debug(f"✅ 抓取成功: {item['url']}")
        
        except Exception as e:
            logger.warning(f"⚠️ 抓取失败 {item['url']}: {str(e)}")
            # 失败时使用 snippet
            item["content"] = item.get("snippet", "")
        
        return item


# 测试代码
async def test_web_search():
    """测试网络搜索"""
    service = WebSearchService()
    
    query = "Python performance optimization"
    results = await service.search(query, max_results=3)
    
    print(f"搜索: {query}")
    print(f"结果数: {len(results)}\n")
    
    for idx, result in enumerate(results, 1):
        print(f"{idx}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   内容: {result['content'][:100]}...")
        print()


if __name__ == "__main__":
    asyncio.run(test_web_search())
