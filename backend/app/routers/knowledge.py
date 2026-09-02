"""Knowledge base CRUD, ingestion jobs and lightweight retrieval APIs."""

import asyncio
from datetime import datetime
from typing import List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import get_db
from app.models.knowledge import KnowledgeChunk, KnowledgeImportJob
from app.models.model_config import KnowledgeBase, QuizQuestion
from app.schemas.model_config import (
    KnowledgeCreate,
    KnowledgeImportJobResponse,
    KnowledgeImportRequest,
    KnowledgeResponse,
    KnowledgeSearchResponse,
)
from app.services.knowledge import index_document, process_import_job, search_knowledge

router = APIRouter()
_running_tasks: Set[asyncio.Task] = set()


def _keep_task(task: asyncio.Task) -> None:
    """Keep a reference until completion and consume unexpected exceptions."""

    _running_tasks.add(task)

    def _done(done: asyncio.Task) -> None:
        _running_tasks.discard(done)
        try:
            done.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            # ``process_import_job`` persists normal errors; this is only a
            # guard for database/connectivity failures before a job is loaded.
            pass

    task.add_done_callback(_done)


def _schedule_job(job_id: int, db: AsyncSession) -> None:
    """Run on the same engine as the request (also works with test DB overrides)."""

    bind = db.bind
    factory = async_sessionmaker(bind=bind, class_=AsyncSession, expire_on_commit=False) if bind else None
    _keep_task(asyncio.create_task(process_import_job(job_id, factory)))


async def _create_document(db: AsyncSession, data: KnowledgeCreate, *, crawled: bool = False) -> KnowledgeBase:
    document = KnowledgeBase(**data.model_dump())
    if crawled and not document.crawled_at:
        document.crawled_at = datetime.utcnow()
    db.add(document)
    await db.flush()
    await index_document(db, document)
    await db.commit()
    await db.refresh(document)
    return document


@router.get("/", response_model=List[KnowledgeResponse])
async def get_knowledge(
    category: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    query = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
    if category:
        query = query.where(KnowledgeBase.category == category)
    if source_type:
        query = query.where(KnowledgeBase.source_type == source_type)
    result = await db.execute(query.limit(limit))
    return result.scalars().all()


@router.post("/", response_model=KnowledgeResponse)
async def create_knowledge(data: KnowledgeCreate, db: AsyncSession = Depends(get_db)):
    """Create a document and index its text chunks."""

    return await _create_document(db, data)


@router.get("/search", response_model=List[KnowledgeSearchResponse])
async def search_knowledge_endpoint(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await search_knowledge(db, q, limit)


@router.post("/import-url", response_model=KnowledgeImportJobResponse, status_code=202)
async def import_url(data: KnowledgeImportRequest, db: AsyncSession = Depends(get_db)):
    """Queue a generic URL import; use ``GET /crawl/tasks/{id}`` for status."""

    if data.source_type != "url":
        raise HTTPException(status_code=400, detail="import-url 的 source_type 必须为 url")
    job = KnowledgeImportJob(
        source_type="url",
        target=data.target,
        options={"category": data.category, "tags": data.tags or [], "max_items": 1},
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    _schedule_job(job.id, db)
    return job


@router.post("/crawl", response_model=KnowledgeImportJobResponse, status_code=202)
async def start_crawl(data: KnowledgeImportRequest, db: AsyncSession = Depends(get_db)):
    """Queue an official/GitHub/CSDN/arXiv crawler import."""

    if data.source_type not in {"official", "github", "csdn", "arxiv"}:
        raise HTTPException(status_code=400, detail="不支持的爬取来源类型")
    job = KnowledgeImportJob(
        source_type=data.source_type,
        target=data.target,
        options={
            "category": data.category,
            "tags": data.tags or [],
            "max_items": data.max_items,
        },
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    _schedule_job(job.id, db)
    return job


@router.get("/crawl/tasks", response_model=List[KnowledgeImportJobResponse])
async def list_import_jobs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeImportJob).order_by(KnowledgeImportJob.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.get("/crawl/tasks/{task_id}", response_model=KnowledgeImportJobResponse)
async def get_import_job(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeImportJob).where(KnowledgeImportJob.id == task_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    return job


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = await db.execute(select(func.count(KnowledgeBase.id)))
    by_type = await db.execute(
        select(KnowledgeBase.source_type, func.count(KnowledgeBase.id)).group_by(KnowledgeBase.source_type)
    )
    by_category = await db.execute(
        select(KnowledgeBase.category, func.count(KnowledgeBase.id)).group_by(KnowledgeBase.category)
    )
    return {
        "total": total.scalar() or 0,
        "by_type": {row[0]: row[1] for row in by_type.all() if row[0]},
        "by_category": {row[0]: row[1] for row in by_category.all() if row[0]},
    }


@router.get("/source-types")
async def get_source_types():
    return [
        {"value": "official", "label": "官方文档"},
        {"value": "csdn", "label": "CSDN"},
        {"value": "arxiv", "label": "arXiv 论文"},
        {"value": "github", "label": "GitHub"},
        {"value": "url", "label": "网页 URL"},
        {"value": "manual", "label": "手动导入"},
    ]


@router.delete("/{knowledge_id}")
async def delete_knowledge(knowledge_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id))
    knowledge = result.scalar_one_or_none()
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    # 题目保留在题库中，但不再指向已删除的知识来源；这样即使旧库的
    # 外键没有配置 ON DELETE SET NULL，也不会阻塞知识条目删除。
    await db.execute(
        update(QuizQuestion)
        .where(QuizQuestion.knowledge_id == knowledge_id)
        .values(knowledge_id=None)
    )
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.knowledge_id == knowledge_id))
    await db.delete(knowledge)
    await db.commit()
    return {"message": "删除成功"}
