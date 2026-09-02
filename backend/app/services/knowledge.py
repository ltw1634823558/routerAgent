"""Knowledge ingestion, chunking and lightweight retrieval.

The service deliberately keeps retrieval dependency-free.  A small token
overlap scorer is predictable in local SQLite tests and provides a clean seam
for replacing it with embeddings later.
"""

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy import delete, select

from app.database import async_session_maker
from app.models.knowledge import KnowledgeChunk, KnowledgeImportJob
from app.models.model_config import KnowledgeBase
from app.services.crawler import (
    ArxivCrawler,
    CSDNCrawler,
    GitHubCrawler,
    OfficialCrawler,
)


_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def split_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    """Split text on paragraph/sentence boundaries with a bounded overlap."""

    text = re.sub(r"\r\n?", "\n", (text or "")).strip()
    if not text:
        return []
    if chunk_size < 1:
        raise ValueError("chunk_size 必须大于 0")
    overlap = max(0, min(overlap, chunk_size - 1))
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    chunks: List[str] = []
    current = ""
    for paragraph in paragraphs:
        # Very large paragraphs are hard-split while preserving overlap.
        while len(paragraph) > chunk_size:
            prefix = paragraph[:chunk_size]
            chunks.append((current + "\n" + prefix).strip() if current else prefix)
            paragraph = paragraph[max(0, chunk_size - overlap) :]
            current = ""
        candidate = f"{current}\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n{paragraph}".strip() if tail else paragraph
    if current:
        chunks.append(current)
    return chunks


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_RE.findall(value or "")}


def _score(query: str, content: str, title: str = "") -> float:
    query_text = query.strip().casefold()
    content_text = (content or "").casefold()
    title_text = (title or "").casefold()
    # Chinese text often has no whitespace; substring matching keeps the
    # dependency-free scorer useful for short Chinese queries.
    if query_text and query_text in content_text:
        return round(1.0 + (0.25 if query_text in title_text else 0.0), 6)
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    body_tokens = _tokens(content)
    title_tokens = _tokens(title)
    matched = query_tokens & body_tokens
    title_matched = query_tokens & title_tokens
    # Title hits receive a modest boost; normalize for long documents.
    return round((len(matched) / len(query_tokens)) + (0.25 * len(title_matched)), 6)


async def index_document(db, document: KnowledgeBase) -> int:
    """Create searchable chunks for one document and return their count."""

    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.knowledge_id == document.id))
    chunks = split_text(document.content)
    for index, content in enumerate(chunks):
        db.add(
            KnowledgeChunk(
                knowledge_id=document.id,
                chunk_index=index,
                content=content,
                source=document.source,
                metadata_json={"title": document.title, "source_type": document.source_type},
            )
        )
    return len(chunks)


async def search_knowledge(db, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Return ranked keyword matches with source citation fields."""

    query = (query or "").strip()
    if not query:
        return []
    rows = await db.execute(
        select(KnowledgeChunk, KnowledgeBase)
        .join(KnowledgeBase, KnowledgeBase.id == KnowledgeChunk.knowledge_id)
    )
    matches = []
    indexed_document_ids: set[int] = set()
    for chunk, document in rows.all():
        indexed_document_ids.add(document.id)
        score = _score(query, chunk.content, document.title)
        if score > 0:
            matches.append(
                {
                    "knowledge_id": document.id,
                    "chunk_id": chunk.id,
                    "title": document.title,
                    "content": chunk.content,
                    "source": chunk.source or document.source,
                    "source_type": document.source_type,
                    "category": document.category,
                    "score": score,
                    "citation": {"title": document.title, "url": chunk.source or document.source or ""},
                }
            )
    # Documents created before the chunk table was introduced are still
    # searchable until they are edited and re-indexed.
    documents = await db.execute(select(KnowledgeBase))
    for document in documents.scalars().all():
        if document.id in indexed_document_ids:
            continue
        score = _score(query, document.content, document.title)
        if score > 0:
            matches.append(
                {
                    "knowledge_id": document.id,
                    "chunk_id": 0,
                    "title": document.title,
                    "content": document.content,
                    "source": document.source,
                    "source_type": document.source_type,
                    "category": document.category,
                    "score": score,
                    "citation": {"title": document.title, "url": document.source or ""},
                }
            )
    matches.sort(key=lambda item: (-item["score"], item["knowledge_id"], item["chunk_id"]))
    return matches[: max(1, min(limit, 100))]


async def _fetch_url(url: str) -> Dict[str, str]:
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "RouterAgent/1.0 knowledge importer"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    title = (soup.find("h1") or soup.find("title"))
    title_text = title.get_text(" ", strip=True) if title else url
    content = soup.get_text("\n", strip=True)
    if not content:
        raise ValueError("网页没有可导入的正文内容")
    return {"title": title_text[:200], "content": content, "url": url, "source": "url"}


async def crawl_items(source_type: str, target: str, max_items: int) -> List[Dict[str, Any]]:
    """Dispatch to a built-in crawler or generic URL importer."""

    if source_type == "url":
        return [await _fetch_url(target)]
    if source_type == "official":
        return await OfficialCrawler().crawl(platform=target, max_docs=max_items)
    if source_type == "github":
        return await GitHubCrawler().crawl(repo=target, max_files=max_items)
    if source_type == "csdn":
        return await CSDNCrawler().crawl(keyword=target, max_pages=max_items)
    if source_type == "arxiv":
        return await ArxivCrawler().crawl(keyword=target, max_results=max_items)
    raise ValueError(f"不支持的导入来源类型: {source_type}")


async def process_import_job(job_id: int, session_factory=None) -> None:
    """Run an import job in the background and persist progress/errors."""

    session_factory = session_factory or async_session_maker
    try:
        session_context = session_factory()
    except Exception as exc:
        logger.error("无法创建知识库任务会话: {}", exc)
        return
    async with session_context as db:
        result = await db.execute(select(KnowledgeImportJob).where(KnowledgeImportJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return
        job.status = "running"
        job.started_at = datetime.utcnow()
        await db.commit()
        try:
            options = job.options or {}
            items = await crawl_items(job.source_type, job.target or "", int(options.get("max_items", 10)))
            job.total_items = len(items)
            await db.commit()
            for item in items:
                content = (item.get("content") or "").strip()
                if not content:
                    continue
                document = KnowledgeBase(
                    title=(item.get("title") or job.target or "导入文档")[:200],
                    content=content,
                    source=item.get("url") or item.get("source_url") or job.target,
                    source_type=item.get("source") or job.source_type,
                    category=options.get("category"),
                    tags=options.get("tags") or [],
                    crawled_at=datetime.utcnow(),
                )
                db.add(document)
                await db.flush()
                await index_document(db, document)
                job.imported_items += 1
                await db.commit()
            job.status = "completed"
            job.finished_at = datetime.utcnow()
            await db.commit()
        except Exception as exc:  # job errors must be queryable by the UI
            logger.exception("知识库导入任务失败: {}", exc)
            job.status = "failed"
            job.error = str(exc)[:2000]
            job.finished_at = datetime.utcnow()
            await db.commit()


def schedule_import_job(job_id: int) -> asyncio.Task:
    """Schedule processing on the current event loop."""

    return asyncio.create_task(process_import_job(job_id))
