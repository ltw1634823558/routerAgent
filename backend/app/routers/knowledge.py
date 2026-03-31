"""知识库路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.database import get_db
from app.models.model_config import KnowledgeBase
from app.schemas.model_config import KnowledgeCreate, KnowledgeResponse

router = APIRouter()


@router.get("/", response_model=List[KnowledgeResponse])
async def get_knowledge(
    category: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """获取知识库列表"""
    query = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())

    if category:
        query = query.where(KnowledgeBase.category == category)
    if source_type:
        query = query.where(KnowledgeBase.source_type == source_type)

    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=KnowledgeResponse)
async def create_knowledge(data: KnowledgeCreate, db: AsyncSession = Depends(get_db)):
    """手动添加知识"""
    knowledge = KnowledgeBase(**data.model_dump())
    db.add(knowledge)
    await db.commit()
    await db.refresh(knowledge)
    return knowledge


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """获取知识库统计"""
    total = await db.execute(select(func.count(KnowledgeBase.id)))
    by_type = await db.execute(
        select(KnowledgeBase.source_type, func.count(KnowledgeBase.id))
        .group_by(KnowledgeBase.source_type)
    )
    by_category = await db.execute(
        select(KnowledgeBase.category, func.count(KnowledgeBase.id))
        .group_by(KnowledgeBase.category)
    )

    return {
        "total": total.scalar(),
        "by_type": {row[0]: row[1] for row in by_type.all() if row[0]},
        "by_category": {row[0]: row[1] for row in by_category.all() if row[0]},
    }


@router.delete("/{knowledge_id}")
async def delete_knowledge(knowledge_id: int, db: AsyncSession = Depends(get_db)):
    """删除知识条目"""
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_id))
    knowledge = result.scalar_one_or_none()
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识条目不存在")

    await db.delete(knowledge)
    await db.commit()
    return {"message": "删除成功"}


@router.get("/source-types")
async def get_source_types():
    """获取来源类型列表"""
    return {
        "source_types": [
            {"value": "official", "label": "官方文档"},
            {"value": "csdn", "label": "CSDN"},
            {"value": "arxiv", "label": "arXiv 论文"},
            {"value": "github", "label": "GitHub"},
            {"value": "manual", "label": "手动导入"},
        ]
    }
