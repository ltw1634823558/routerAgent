"""
搜索 Agent
"""
import os
import httpx
from typing import AsyncGenerator, Dict, Any, List
from loguru import logger
from app.agents.base import BaseAgent
from app.services.search import get_search_engine


class SearchAgent(BaseAgent):
    """搜索 Agent"""

    def __init__(
        self,
        model_config: Dict[str, Any],
        search_engine: str = "duckduckgo",
        search_api_key: str = "",
    ):
        super().__init__(model_config)
        self.engine = get_search_engine(search_engine, search_api_key)
        self.search_engine = search_engine
        self.search_api_key = search_api_key

    async def run(self, query: str) -> AsyncGenerator[str, None]:
        """运行搜索 Agent"""
        # 1. 执行搜索
        try:
            search_result = await self.engine.search(query, max_results=10)
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            yield f"❌ 搜索失败: {e}"
            return

        if not search_result.get("success"):
            yield f"❌ 搜索出错: {search_result.get('error')}"
            return

        # 2. 构建提示词
        results_text = ""
        sources = []

        for item in search_result.get("results", []):
            results_text += f"- {item.get('snippet', '')}\n"
            sources.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
            })

        prompt = f"""请根据以下搜索结果，提炼出结构化答案。

搜索内容： {query}

搜索结果:
{results_text}

请给出简洁、准确的答案,并在最后列出参考链接(最多5个)。"""

        # 3. 调用 LLM 生成答案
        async for chunk in self.stream_response(prompt):
            yield chunk

        # 4. 输出参考链接
        yield "\n\n**参考来源:**\n"
        for i in range(1, min(5, len(sources)) + 1):
            source = sources[i - 1]
            yield f"{i}. [{source['title']}]({source['url']})\n"
