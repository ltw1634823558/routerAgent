"""
搜索引擎服务
"""
import asyncio
import os
from typing import Dict, Any, List

import httpx
from loguru import logger

try:
    # 放在模块级便于测试替换；依赖缺失时由 search() 返回明确提示。
    from duckduckgo_search import DDGS
except ImportError:  # pragma: no cover - depends on the runtime environment
    DDGS = None


class SearchEngine:
    """搜索引擎基类"""

    def __init__(self, api_key: str = "", proxy: str = ""):
        self.api_key = api_key
        self.proxy = proxy or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """执行搜索"""
        raise NotImplementedError


class DuckDuckGoEngine(SearchEngine):
    """DuckDuckGo 搜索引擎（免费，无需 API Key）"""

    # API 后端会访问经常触发限流的 links.duckduckgo.com/d.js；HTML 和 lite
    # 使用不同的接口，可作为同一 DDGS 客户端的备用后端。
    _BACKENDS = ("html", "lite", "api")
    _TIMEOUT = 30

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """执行搜索"""
        if not query or not query.strip():
            return {
                "success": False,
                "error": "搜索关键词不能为空",
                "results": [],
                "engine": "duckduckgo",
            }

        if DDGS is None:
            return {
                "success": False,
                "error": "未安装 DuckDuckGo 搜索依赖，请执行 pip install duckduckgo-search",
                "results": [],
                "engine": "duckduckgo",
            }

        errors: List[str] = []
        saw_empty_result = False
        for backend in self._BACKENDS:
            try:
                # duckduckgo-search 是同步库，放到线程中避免阻塞 FastAPI/WebSocket
                # 使用的事件循环。
                results = await asyncio.to_thread(
                    self._search_sync,
                    DDGS,
                    query.strip(),
                    max_results,
                    backend,
                )
                if results:
                    return self._format_success(results)
                # 某些后端被拦截时可能不会抛异常，而是返回空列表；继续
                # 尝试其他端点，避免把临时故障误报为“没有结果”。
                saw_empty_result = True
                logger.warning(f"DuckDuckGo {backend} 后端返回空结果，将尝试下一个后端")
            except Exception as e:
                error_msg = str(e)
                errors.append(error_msg)
                logger.warning(
                    f"DuckDuckGo {backend} 后端搜索失败，将尝试下一个后端: {error_msg}"
                )

        if saw_empty_result and not errors:
            return self._format_success([])

        error_msg = errors[-1] if errors else "未知错误"
        if any(self._is_rate_limit_error(error) for error in errors):
            friendly_msg = (
                "DuckDuckGo 请求过于频繁，已自动切换备用接口但仍被限流。"
                "请稍后重试、配置代理，或改用 Tavily、Bing 等搜索引擎"
            )
        elif any(
            "timeout" in error.lower() or "timed out" in error.lower()
            for error in errors
        ):
            friendly_msg = (
                "DuckDuckGo 连接超时，可能是网络问题。建议配置代理或使用其他"
                "搜索引擎（如 Tavily、Bing）"
            )
        elif any("connection" in error.lower() for error in errors):
            friendly_msg = "无法连接到 DuckDuckGo，请检查网络连接或配置代理"
        else:
            friendly_msg = f"DuckDuckGo 搜索出错: {error_msg}"

        logger.error(f"DuckDuckGo 搜索失败（所有后端）: {error_msg}")
        return {
            "success": False,
            "error": friendly_msg,
            "results": [],
            "engine": "duckduckgo",
        }

    def _search_sync(
        self,
        ddgs_class: Any,
        query: str,
        max_results: int,
        backend: str,
    ) -> List[Dict[str, Any]]:
        """使用一个 DDG 后端执行同步搜索。"""
        proxies = None
        if self.proxy:
            proxies = {"http": self.proxy, "https": self.proxy}
            logger.info(f"DuckDuckGo 使用代理: {self.proxy}")

        # duckduckgo-search 4.x 使用 ``proxies``，较新版本改名为 ``proxy``；
        # 两种参数都支持，避免升级依赖后在降级逻辑之前直接失败。
        try:
            client = ddgs_class(proxies=proxies, timeout=self._TIMEOUT)
        except TypeError:
            client = ddgs_class(proxy=self.proxy or None, timeout=self._TIMEOUT)

        with client as ddgs:
            return list(
                ddgs.text(
                    query,
                    backend=backend,
                    max_results=max_results,
                )
            )

    @staticmethod
    def _format_success(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not results:
            return {
                "success": True,
                "results": [],
                "engine": "duckduckgo",
                "message": "搜索完成，但未找到相关结果",
            }

        return {
            "success": True,
            "results": [
                {
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                }
                for result in results
            ],
            "engine": "duckduckgo",
        }

    @staticmethod
    def _is_rate_limit_error(error: str) -> bool:
        normalized = error.lower()
        return any(
            marker in normalized
            for marker in (
                "ratelimit",
                "rate limit",
                "too many requests",
                "429",
                "status code: 202",
            )
        )


class TavilyEngine(SearchEngine):
    """Tavily 搜索引擎 - 推荐，搜索质量高"""

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """执行搜索"""
        if not self.api_key:
            return {
                "success": False,
                "error": "缺少 Tavily API Key，请访问 https://tavily.com 获取免费 Key",
                "results": [],
                "engine": "tavily",
            }

        try:
            proxy_config = {}
            if self.proxy:
                proxy_config = {"proxies": {"http://": self.proxy, "https://": self.proxy}}

            async with httpx.AsyncClient(timeout=30.0, **proxy_config) as client:
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
            return {
                "success": False,
                "error": "缺少 SerpAPI Key，请访问 https://serpapi.com 获取",
                "results": [],
                "engine": "serpapi",
            }

        try:
            proxy_config = {}
            if self.proxy:
                proxy_config = {"proxies": {"http://": self.proxy, "https://": self.proxy}}

            async with httpx.AsyncClient(timeout=30.0, **proxy_config) as client:
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
    """Bing 搜索引擎 - 国内访问较稳定"""

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """执行搜索"""
        if not self.api_key:
            return {
                "success": False,
                "error": "缺少 Bing API Key，请访问 https://azure.microsoft.com/services/cognitive-services/bing-web-search-api/ 获取",
                "results": [],
                "engine": "bing",
            }

        try:
            proxy_config = {}
            if self.proxy:
                proxy_config = {"proxies": {"http://": self.proxy, "https://": self.proxy}}

            async with httpx.AsyncClient(timeout=30.0, **proxy_config) as client:
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


class BochaEngine(SearchEngine):
    """Bocha (波查) 搜索引擎 - 国内可访问"""

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """执行搜索"""
        if not self.api_key:
            return {
                "success": False,
                "error": "缺少 Bocha API Key",
                "results": [],
                "engine": "bocha",
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.bocha.io/v1/search",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "count": max_results,
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = data.get("data", {}).get("results", [])
            return {
                "success": True,
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("snippet", r.get("content", "")),
                    }
                    for r in results
                ],
                "engine": "bocha",
            }
        except Exception as e:
            logger.error(f"Bocha 搜索失败: {e}")
            return {"success": False, "error": str(e), "results": [], "engine": "bocha"}


def get_search_engine(engine_type: str, api_key: str = "", proxy: str = "") -> SearchEngine:
    """获取搜索引擎实例

    Args:
        engine_type: 搜索引擎类型 (duckduckgo, tavily, serpapi, google, bing, bocha)
        api_key: API Key（部分引擎需要）
        proxy: 代理地址（可选，如 http://127.0.0.1:7890）

    Returns:
        SearchEngine 实例
    """
    engines = {
        "duckduckgo": DuckDuckGoEngine,
        "tavily": TavilyEngine,
        "serpapi": SerpAPIEngine,
        "google": SerpAPIEngine,  # Google 通过 SerpAPI
        "bing": BingEngine,
        "bocha": BochaEngine,
    }

    engine_class = engines.get(engine_type.lower())
    if not engine_class:
        raise ValueError(f"不支持的搜索引擎: {engine_type}，支持的引擎: {list(engines.keys())}")

    return engine_class(api_key, proxy)


# 搜索引擎说明
SEARCH_ENGINE_INFO = {
    "duckduckgo": {
        "name": "DuckDuckGo",
        "free": True,
        "requires_key": False,
        "description": "免费搜索引擎，国内可能需要代理",
        "get_key": None,
    },
    "tavily": {
        "name": "Tavily",
        "free": False,
        "requires_key": True,
        "description": "专业 AI 搜索，搜索质量高，推荐使用",
        "get_key": "https://tavily.com",
    },
    "serpapi": {
        "name": "SerpAPI (Google)",
        "free": False,
        "requires_key": True,
        "description": "Google 搜索结果，需要 SerpAPI Key",
        "get_key": "https://serpapi.com",
    },
    "bing": {
        "name": "Bing",
        "free": False,
        "requires_key": True,
        "description": "微软 Bing 搜索，国内访问较稳定",
        "get_key": "https://azure.microsoft.com/services/cognitive-services/bing-web-search-api/",
    },
    "bocha": {
        "name": "Bocha (波查)",
        "free": False,
        "requires_key": True,
        "description": "国内可访问的搜索服务",
        "get_key": "https://bocha.io",
    },
}
