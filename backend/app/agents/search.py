"""搜索 Agent。

普通模式保持一次检索的轻量行为；深度模式会把问题拆成多个角度检索，
对结果去重和排序后再交给模型总结，并要求模型使用 ``[S1]`` 形式引用来源。
"""

import asyncio
import re
from typing import Any, AsyncGenerator, Dict, Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from loguru import logger

from app.agents.base import BaseAgent
from app.services.search import get_search_engine


class SearchAgent(BaseAgent):
    """搜索 Agent，支持普通检索和可选的深度检索。"""

    DEFAULT_MAX_RESULTS = 10
    DEFAULT_MAX_SUBQUERIES = 3
    MAX_DEEP_RESULTS = 20

    def __init__(
        self,
        model_config: Dict[str, Any],
        search_engine: str = "duckduckgo",
        search_api_key: str = "",
        deep_search: bool = False,
        max_subqueries: int = DEFAULT_MAX_SUBQUERIES,
        max_results: int = DEFAULT_MAX_RESULTS,
    ):
        super().__init__(model_config)
        self.engine = get_search_engine(search_engine, search_api_key)
        self.search_engine = search_engine
        self.search_api_key = search_api_key
        self.deep_search = bool(deep_search)
        self.max_subqueries = max(1, min(int(max_subqueries or self.DEFAULT_MAX_SUBQUERIES), 5))
        self.max_results = max(1, min(int(max_results or self.DEFAULT_MAX_RESULTS), self.MAX_DEEP_RESULTS))
        # WebSocket 层会在任务完成后读取该字段并保存到 SearchRecord。
        self.last_sources: List[Dict[str, Any]] = []
        self.last_queries: List[str] = []

    async def run(
        self,
        query: str,
        deep_search: Optional[bool] = None,
        *,
        max_subqueries: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """运行搜索 Agent。

        ``deep_search`` 为 ``None`` 时使用构造函数配置，因而兼容原来的
        ``run(query)`` 调用。运行结果的来源会写入 ``last_sources``。
        """
        query = (query or "").strip()
        self.last_sources = []
        self.last_queries = []
        if not query:
            yield "❌ 搜索出错: 搜索关键词不能为空"
            return

        use_deep_search = self.deep_search if deep_search is None else bool(deep_search)
        if use_deep_search:
            async for chunk in self._run_deep_search(query, max_subqueries=max_subqueries):
                yield chunk
            return

        search_result = await self._search_one(query, self.max_results)
        if not search_result.get("success"):
            yield f"❌ 搜索出错: {search_result.get('error', '未知错误')}"
            return

        sources = self._prepare_sources(search_result.get("results", []))
        self.last_sources = sources
        self.last_queries = [query]
        if not sources:
            yield "未找到相关搜索结果，请尝试换一个关键词。"
            return

        prompt = self._build_prompt(query, sources, deep=False)
        async for chunk in self.stream_response(prompt):
            yield chunk

        async for chunk in self._format_sources(sources, deep=False):
            yield chunk

    async def _run_deep_search(
        self,
        query: str,
        *,
        max_subqueries: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """执行多角度检索并生成带引用的答案。"""
        limit = max_subqueries or self.max_subqueries
        limit = max(1, min(int(limit), 5))
        queries = self.build_subqueries(query, limit)
        self.last_queries = queries

        # 每个子查询独立失败不应让整个研究任务失败。
        results = await asyncio.gather(
            *(self._search_one(subquery, self.max_results) for subquery in queries),
            return_exceptions=True,
        )
        merged: List[Dict[str, Any]] = []
        errors: List[str] = []
        for subquery, result in zip(queries, results):
            if isinstance(result, Exception):
                errors.append(str(result))
                logger.warning("深度搜索子查询失败（{}）: {}", subquery, result)
                continue
            if not result.get("success"):
                errors.append(str(result.get("error", "未知错误")))
                continue
            for item in result.get("results", []):
                enriched = dict(item)
                enriched["matched_query"] = subquery
                merged.append(enriched)

        sources = self._prepare_sources(merged)
        self.last_sources = sources
        if not sources:
            if errors:
                # 给用户一个可执行的提示，避免把底层库的长异常直接输出。
                yield "❌ 深度搜索失败: 所有子查询均未返回结果，请稍后重试或更换搜索引擎。"
            else:
                yield "未找到相关搜索结果，请尝试换一个关键词。"
            return

        prompt = self._build_prompt(query, sources, deep=True)
        async for chunk in self.stream_response(prompt):
            yield chunk

        async for chunk in self._format_sources(sources, deep=True):
            yield chunk

    async def _search_one(self, query: str, max_results: int) -> Dict[str, Any]:
        """调用搜索引擎并统一异常格式。"""
        try:
            result = await self.engine.search(query, max_results=max_results)
            if isinstance(result, dict):
                return result
            return {"success": False, "error": "搜索引擎返回格式无效", "results": []}
        except Exception as exc:
            logger.error("搜索失败（{}）: {}", query, exc)
            return {"success": False, "error": str(exc), "results": []}

    @classmethod
    def build_subqueries(cls, query: str, max_subqueries: int = DEFAULT_MAX_SUBQUERIES) -> List[str]:
        """将一个问题拆成互补角度，保证原问题始终位于第一位。

        这里采用确定性拆分，不额外消耗一次 LLM 调用，也不会因为模型输出
        不可解析而陷入重复重试。已有逗号、分号或换行的多问题会优先拆分。
        """
        query = (query or "").strip()
        if not query:
            return []
        limit = max(1, min(int(max_subqueries or cls.DEFAULT_MAX_SUBQUERIES), 5))
        queries: List[str] = [query]

        # 用户输入中已有多个问题时，优先使用用户明确给出的角度。
        parts = [part.strip() for part in re.split(r"[\n\r，,；;。！？!?]+", query) if part.strip()]
        for part in parts:
            if part.casefold() != query.casefold() and part not in queries:
                queries.append(part)

        # 单一问题补充基础、实践、风险三个常用研究角度。
        suffixes = ("原理", "实践案例", "优缺点与风险")
        if len(queries) < limit:
            for suffix in suffixes:
                candidate = f"{query} {suffix}"
                if candidate not in queries:
                    queries.append(candidate)
                if len(queries) >= limit:
                    break
        return queries[:limit]

    @classmethod
    def _prepare_sources(cls, results: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """规范化、去重并排序搜索结果。"""
        unique: Dict[str, Dict[str, Any]] = {}
        for raw in results:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or "").strip()
            url = str(raw.get("url") or raw.get("href") or "").strip()
            snippet = str(raw.get("snippet") or raw.get("body") or raw.get("content") or "").strip()
            if not title and not url and not snippet:
                continue
            key = cls._normalize_url(url) or f"{title.casefold()}|{snippet.casefold()[:160]}"
            if key in unique:
                # 同一 URL 可能由不同子查询命中，保留信息更完整的那条。
                current = unique[key]
                if len(snippet) > len(str(current.get("snippet", ""))):
                    current["snippet"] = snippet
                continue
            domain = cls._domain(url)
            score = cls._source_score(title, snippet, domain)
            unique[key] = {
                "title": title or url or "未命名来源",
                "url": url,
                "snippet": snippet,
                "domain": domain,
                "score": score,
                "matched_query": raw.get("matched_query", ""),
            }

        ordered = sorted(unique.values(), key=lambda item: item.get("score", 0), reverse=True)
        for index, source in enumerate(ordered, 1):
            source["citation_id"] = f"S{index}"
        return ordered

    @staticmethod
    def _normalize_url(url: str) -> str:
        if not url:
            return ""
        try:
            parts = urlsplit(url.strip())
            if not parts.netloc:
                return url.strip().rstrip("/").casefold()
            query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
                     if not key.lower().startswith(("utm_", "ref", "source"))]
            return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"),
                               urlencode(query), "")).casefold()
        except ValueError:
            return url.strip().rstrip("/").casefold()

    @staticmethod
    def _domain(url: str) -> str:
        try:
            return urlsplit(url).netloc.casefold().removeprefix("www.")
        except ValueError:
            return ""

    @staticmethod
    def _source_score(title: str, snippet: str, domain: str) -> float:
        """来源排序分：官方域名可信度 + 内容长度，保持可解释。"""
        score = 0.0
        if domain.endswith((".gov", ".gov.cn", ".edu", ".edu.cn")):
            score += 4
        elif domain.endswith("github.com") or domain.endswith("gitlab.com"):
            score += 2.5
        elif domain in {"docs.python.org", "developer.mozilla.org", "kubernetes.io", "fastapi.tiangolo.com"}:
            score += 3
        elif domain:
            score += 1
        score += min(len(snippet), 500) / 500
        score += min(len(title), 120) / 120 * 0.2
        return score

    @staticmethod
    def _build_prompt(query: str, sources: List[Dict[str, Any]], deep: bool) -> str:
        results_text = "\n\n".join(
            f"[{source['citation_id']}] {source['title']} ({source.get('domain', '')})\n"
            f"URL: {source['url']}\n摘要: {source['snippet']}"
            for source in sources
        )
        if deep:
            instructions = (
                "这是一次深度检索。请先综合不同来源，再给出分层、可核查的答案。"
                "每个关键事实后必须标注对应来源编号（如 [S1]）；没有来源支持的内容请明确说明。"
            )
        else:
            instructions = "请给出简洁、准确的答案，关键事实尽量标注来源编号。"
        return f"""请根据以下搜索结果回答用户问题。

用户问题：{query}

搜索结果：
{results_text}

{instructions}
不要编造搜索结果中没有的信息。"""

    @staticmethod
    async def _format_sources(sources: List[Dict[str, Any]], deep: bool) -> AsyncGenerator[str, None]:
        heading = "\n\n**深度检索来源:**\n" if deep else "\n\n**参考来源:**\n"
        yield heading
        max_sources = min(len(sources), 10 if deep else 5)
        for source in sources[:max_sources]:
            citation_id = source.get("citation_id", "S?")
            title = source.get("title", "未命名来源")
            url = source.get("url", "")
            if url:
                yield f"- [{citation_id}] [{title}]({url})\n"
            else:
                yield f"- [{citation_id}] {title}\n"
