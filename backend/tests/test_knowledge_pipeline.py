import asyncio
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.knowledge import KnowledgeChunk, KnowledgeImportJob
from app.models.model_config import KnowledgeBase
from app.services.knowledge import split_text


@pytest.mark.unit
def test_split_text_keeps_overlap_and_content():
    text = "第一段内容。" * 120
    chunks = split_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert "第一段内容" in chunks[0]
    assert chunks[0][-20:] in chunks[1]


@pytest.mark.api
@pytest.mark.asyncio
async def test_create_indexes_and_searches_knowledge(client: AsyncClient, db_session):
    response = await client.post(
        "/api/knowledge/",
        json={
            "title": "异步 Python",
            "content": "asyncio 通过事件循环调度协程，适合 IO 密集任务。",
            "source": "https://example.com/asyncio",
            "source_type": "manual",
        },
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    chunks = (await db_session.execute(select(KnowledgeChunk))).scalars().all()
    assert len(chunks) == 1
    assert chunks[0].knowledge_id == document_id

    search = await client.get("/api/knowledge/search", params={"q": "事件循环"})
    assert search.status_code == 200
    result = search.json()
    assert result and result[0]["knowledge_id"] == document_id
    assert result[0]["source"] == "https://example.com/asyncio"


@pytest.mark.api
@pytest.mark.asyncio
async def test_import_job_status_can_be_queried(client: AsyncClient, db_session):
    job = KnowledgeImportJob(source_type="url", target="https://example.com", status="pending")
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    response = await client.get(f"/api/knowledge/crawl/tasks/{job.id}")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


@pytest.mark.api
@pytest.mark.asyncio
async def test_crawl_job_imports_items_and_finishes(client: AsyncClient, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.knowledge.crawl_items",
        AsyncMock(
            return_value=[
                {
                    "title": "GitHub README",
                    "content": "Python class example",
                    "url": "https://github.com/example/demo/blob/main/README.md",
                    "source": "github",
                }
            ]
        ),
    )

    response = await client.post(
        "/api/knowledge/crawl",
        json={"source_type": "github", "target": "example/demo", "max_items": 1},
    )
    assert response.status_code == 202
    job_id = response.json()["id"]

    job = None
    for _ in range(20):
        await asyncio.sleep(0.01)
        status = await client.get(f"/api/knowledge/crawl/tasks/{job_id}")
        job = status.json()
        if job["status"] in {"completed", "failed"}:
            break

    assert job is not None
    assert job["status"] == "completed"
    assert job["imported_items"] == 1
    documents = (await db_session.execute(select(KnowledgeBase))).scalars().all()
    assert len(documents) == 1
    assert documents[0].source_type.value == "github"
