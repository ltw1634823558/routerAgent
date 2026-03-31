"""
搜索引擎服务
"""
import httpx
from typing import Dict, Any, List
from loguru import logger


class SearchEngine:
    """搜索引擎基类"""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """执行搜索"""
        raise NotImplementedError


class DuckDuckGoEngine(SearchEngine):
    """DuckDuckGo 搜索引擎（免费，无需 API Key）"""

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """执行搜索"""
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            return {
                "success": True,
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    }
                    for r in results
                ],
                "engine": "duckduckgo",
            }
        except Exception as e:
            logger.error(f"DuckDuckGo 搜索失败: {e}")
            return {"success": False, "error": str(e), "results": [], "engine": "duckduckgo"}


class TavilyEngine(SearchEngine):
    """Tavily 搜索引擎"""

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """执行搜索"""
        if not self.api_key:
            return {"success": False, "error": "缺少 Tavily API Key", "results": [], "engine": "tavily"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "search_depth": "advanced",
                        "max_results": max_results,
                        "include_answer": True,
                        "include_raw_content": False,
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = data.get("results", [])
            return {
                "success": True,
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("content", ""),
                    }
                    for r in results
                ],
                "answer": data.get("answer", ""),
                "engine": "tavily",
            }
        except Exception as e:
            logger.error(f"Tavily 搜索失败: {e}")
            return {"success": False, "error": str(e), "results": [], "engine": "tavily"}


class SerpAPIEngine(SearchEngine):
    """SerpAPI 搜索引擎（Google）"""

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """执行搜索"""
        if not self.api_key:
            return {"success": False, "error": "缺少 SerpAPI Key", "results": [], "engine": "serpapi"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "api_key": self.api_key,
                        "q": query,
                        "engine": "google",
                        "num": max_results,
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = data.get("organic_results", [])
            return {
                "success": True,
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("link", ""),
                        "snippet": r.get("snippet", ""),
                    }
                    for r in results
                ],
                "engine": "serpapi",
            }
        except Exception as e:
            logger.error(f"SerpAPI 搜索失败: {e}")
            return {"success": False, "error": str(e), "results": [], "engine": "serpapi"}


class BingEngine(SearchEngine):
    """Bing 搜索引擎"""

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """执行搜索"""
        if not self.api_key:
            return {"success": False, "error": "缺少 Bing API Key", "results": [], "engine": "bing"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.bing.microsoft.com/v7.0/search",
                    headers={"Ocp-Apim-Subscription-Key": self.api_key},
                    params={"q": query, "count": max_results},
                )
                response.raise_for_status()
                data = response.json()

            results = data.get("webPages", {}).get("value", [])
            return {
                "success": True,
                "results": [
                    {
                        "title": r.get("name", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("snippet", ""),
                    }
                    for r in results
                ],
                "engine": "bing",
            }
        except Exception as e:
            logger.error(f"Bing 搜索失败: {e}")
            return {"success": False, "error": str(e), "results": [], "engine": "bing"}


def get_search_engine(engine_type: str, api_key: str = "") -> SearchEngine:
    """获取搜索引擎实例"""
    engines = {
        "duckduckgo": DuckDuckGoEngine,
        "tavily": TavilyEngine,
        "serpapi": SerpAPIEngine,
        "google": SerpAPIEngine,  # Google 通过 SerpAPI
        "bing": BingEngine,
    }

    engine_class = engines.get(engine_type.lower())
    if not engine_class:
        raise ValueError(f"不支持的搜索引擎: {engine_type}")

    return engine_class(api_key)
