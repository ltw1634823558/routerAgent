"""提示词Agent路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.model_config import PromptRecord
from app.schemas.model_config import PromptRecordResponse

router = APIRouter()


@router.get("/records", response_model=List[PromptRecordResponse])
async def get_prompt_records(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """获取提示词历史"""
    result = await db.execute(
        select(PromptRecord).order_by(PromptRecord.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.delete("/records/{record_id}")
async def delete_prompt_record(record_id: int, db: AsyncSession = Depends(get_db)):
    """删除提示词记录"""
    result = await db.execute(select(PromptRecord).where(PromptRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="记录不存在")

    await db.delete(record)
    await db.commit()
    return {"message": "删除成功"}
