"""问答Agent路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.model_config import QuizSession, QuizQuestion
from app.schemas.model_config import QuizSessionResponse, QuizQuestionResponse

router = APIRouter()


@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """获取所有技能分类"""
    result = await db.execute(
        select(QuizQuestion.category).distinct().where(QuizQuestion.category.isnot(None))
    )
    categories = [row[0] for row in result.all()]
    return {"categories": categories}


@router.get("/history", response_model=List[QuizSessionResponse])
async def get_quiz_history(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """获取答题历史"""
    result = await db.execute(
        select(QuizSession).order_by(QuizSession.started_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.get("/session/{session_id}", response_model=QuizSessionResponse)
async def get_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """获取答题会话详情"""
    result = await db.execute(select(QuizSession).where(QuizSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@router.get("/difficulties")
async def get_difficulties():
    """获取难度级别"""
    return {
        "difficulties": [
            {"value": "basic", "label": "基础"},
            {"value": "intermediate", "label": "进阶"},
            {"value": "advanced", "label": "精通"},
        ]
    }
