"""问答 Agent 路由及题库学习闭环接口。"""
import json
from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.model_config import KnowledgeBase, QuizAttempt, QuizQuestion, QuizSession
from app.schemas.model_config import (
    QuizQuestionResponse,
    QuizSessionResponse,
    QuizWeaknessStats,
    QuizWrongAnswerResponse,
)

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
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


def _answer_display(answer: Any, options: Optional[List[str]]) -> Any:
    """把选择题答案索引转换成可读文本，兼容旧数据的字符串答案。"""
    if not options:
        return answer
    values: Any = answer
    if isinstance(answer, str):
        text = answer.strip()
        try:
            values = json.loads(text) if text.startswith(("[", "{")) else answer
        except (TypeError, ValueError, json.JSONDecodeError):
            values = answer

    def one(value: Any) -> Any:
        try:
            index = int(value)
        except (TypeError, ValueError):
            index = None
        if index is not None and 0 <= index < len(options):
            return options[index]
        if isinstance(value, str):
            text = value.strip()
            if len(text) == 1 and text.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                index = ord(text.upper()) - ord("A")
                if index < len(options):
                    return options[index]
            for option in options:
                if text.casefold() == str(option).strip().casefold():
                    return option
        return value

    if isinstance(values, list):
        return [one(value) for value in values]
    return one(values)


def _wrong_answer_payload(
    attempt: QuizAttempt,
    question: QuizQuestion,
    knowledge: Optional[KnowledgeBase],
) -> Dict[str, Any]:
    return {
        "attempt_id": attempt.id,
        "session_id": attempt.session_id,
        "question_id": question.id,
        "question": question.question,
        "question_type": question.question_type.value
        if hasattr(question.question_type, "value")
        else question.question_type,
        "options": question.options,
        "user_answer": attempt.user_answer,
        "correct_answer": _answer_display(question.answer, question.options),
        "explanation": question.explanation,
        "difficulty": question.difficulty.value if hasattr(question.difficulty, "value") else question.difficulty,
        "category": question.category,
        "knowledge_id": question.knowledge_id,
        "source_title": knowledge.title if knowledge else None,
        "source": knowledge.source if knowledge else None,
        "attempted_at": attempt.created_at,
    }


@router.get("/wrong-answers", response_model=List[QuizWrongAnswerResponse])
async def get_wrong_answers(
    limit: int = 50,
    category: Optional[str] = None,
    knowledge_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取错题本记录，按最近作答时间倒序。"""
    limit = max(1, min(limit, 200))
    query = (
        select(QuizAttempt, QuizQuestion, KnowledgeBase)
        .join(QuizQuestion, QuizQuestion.id == QuizAttempt.question_id)
        .outerjoin(KnowledgeBase, KnowledgeBase.id == QuizQuestion.knowledge_id)
        .where(QuizAttempt.is_correct.is_(False))
        .order_by(QuizAttempt.created_at.desc(), QuizAttempt.id.desc())
        .limit(limit)
    )
    if category:
        query = query.where(QuizQuestion.category == category)
    if knowledge_id is not None:
        query = query.where(QuizQuestion.knowledge_id == knowledge_id)
    result = await db.execute(query)
    return [_wrong_answer_payload(attempt, question, knowledge) for attempt, question, knowledge in result.all()]


def _group_weakness(rows: List[Any], index: int) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "wrong": 0})
    for _attempt, question in rows:
        raw_name = question.category if index == 0 else question.difficulty
        if hasattr(raw_name, "value"):
            raw_name = raw_name.value
        name = raw_name or "未分类"
        grouped[name]["total"] += 1
        if _attempt.is_correct is False:
            grouped[name]["wrong"] += 1

    items = []
    for name, values in grouped.items():
        total = values["total"]
        wrong = values["wrong"]
        correct = total - wrong
        accuracy = round(correct / total * 100, 2) if total else 0.0
        items.append(
            {
                "name": name,
                "total_attempts": total,
                "wrong_count": wrong,
                "correct_count": correct,
                "accuracy": accuracy,
                "weakness_score": round(100 - accuracy, 2),
            }
        )
    return sorted(items, key=lambda item: (-item["weakness_score"], -item["wrong_count"], item["name"]))


@router.get("/weaknesses", response_model=QuizWeaknessStats)
@router.get("/weakness-stats", response_model=QuizWeaknessStats, include_in_schema=False)
async def get_weakness_stats(db: AsyncSession = Depends(get_db)):
    """统计分类和难度维度的薄弱点，供错题复习使用。"""
    result = await db.execute(
        select(QuizAttempt, QuizQuestion)
        .join(QuizQuestion, QuizQuestion.id == QuizAttempt.question_id)
        .where(QuizAttempt.is_correct.isnot(None))
    )
    rows = result.all()
    total = len(rows)
    wrong = sum(1 for attempt, _question in rows if attempt.is_correct is False)
    correct = total - wrong
    accuracy = round(correct / total * 100, 2) if total else 0.0
    return {
        "total_attempts": total,
        "wrong_count": wrong,
        "correct_count": correct,
        "accuracy": accuracy,
        "categories": _group_weakness(rows, 0),
        "difficulties": _group_weakness(rows, 1),
    }


@router.get("/difficulties")
async def get_difficulties():
    """获取难度级别"""
    return [
            {"value": "basic", "label": "基础"},
            {"value": "intermediate", "label": "进阶"},
            {"value": "advanced", "label": "精通"},
    ]
