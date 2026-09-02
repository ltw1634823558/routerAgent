"""搜索Agent路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.model_config import SearchRecord
from app.schemas.model_config import SearchRecordResponse

router = APIRouter()


@router.get("/records", response_model=List[SearchRecordResponse])
async def get_search_records(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """获取搜索历史"""
    result = await db.execute(
        select(SearchRecord).order_by(SearchRecord.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.delete("/records/{record_id}")
async def delete_search_record(record_id: int, db: AsyncSession = Depends(get_db)):
    """删除搜索记录"""
    result = await db.execute(select(SearchRecord).where(SearchRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="记录不存在")

    await db.delete(record)
    await db.commit()
    return {"message": "删除成功"}


@router.get("/engines/list")
async def get_engines():
    """获取支持的搜索引擎列表"""
    return [
            {"value": "bocha", "label": "Bocha（波查）", "need_key": True},
            {"value": "duckduckgo", "label": "DuckDuckGo（免费）", "need_key": False},
            {"value": "tavily", "label": "Tavily", "need_key": True},
            {"value": "serpapi", "label": "SerpAPI (Google)", "need_key": True},
            {"value": "google", "label": "Google", "need_key": True},
            {"value": "bing", "label": "Bing", "need_key": True},
    ]
