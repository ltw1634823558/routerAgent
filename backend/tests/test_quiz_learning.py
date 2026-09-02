"""题库错题本和薄弱点统计接口测试。"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_config import KnowledgeBase, QuizAttempt, QuizQuestion, QuizSession


@pytest.mark.api
@pytest.mark.asyncio
async def test_wrong_answers_include_knowledge_source(client: AsyncClient, db_session: AsyncSession):
    knowledge = KnowledgeBase(
        title="Python 官方文档",
        content="Python 内容",
        source="https://docs.python.org/",
        source_type="official",
        category="Python",
    )
    db_session.add(knowledge)
    await db_session.flush()
    question = QuizQuestion(
        knowledge_id=knowledge.id,
        question="Python 使用什么关键字定义函数？",
        question_type="choice",
        options=["def", "fn"],
        answer="0",
        explanation="def 用于定义函数。",
        difficulty="basic",
        category="Python",
    )
    session = QuizSession(category="Python", difficulty="basic", total_questions=1)
    db_session.add_all([question, session])
    await db_session.flush()
    db_session.add(QuizAttempt(session_id=session.id, question_id=question.id, user_answer="fn", is_correct=False))
    await db_session.commit()

    response = await client.get("/api/quiz/wrong-answers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["knowledge_id"] == knowledge.id
    assert data[0]["source_title"] == "Python 官方文档"
    assert data[0]["correct_answer"] == "def"


@pytest.mark.api
@pytest.mark.asyncio
async def test_weakness_stats_group_by_category(client: AsyncClient, db_session: AsyncSession):
    question = QuizQuestion(
        question="测试题",
        question_type="fill",
        answer="ok",
        difficulty="intermediate",
        category="Python",
    )
    session = QuizSession(category="Python", difficulty="intermediate", total_questions=2)
    db_session.add_all([question, session])
    await db_session.flush()
    db_session.add_all([
        QuizAttempt(session_id=session.id, question_id=question.id, user_answer="wrong", is_correct=False),
        QuizAttempt(session_id=session.id, question_id=question.id, user_answer="ok", is_correct=True),
    ])
    await db_session.commit()

    response = await client.get("/api/quiz/weaknesses")
    assert response.status_code == 200
    data = response.json()
    assert data["total_attempts"] == 2
    assert data["wrong_count"] == 1
    assert data["accuracy"] == 50.0
    assert data["categories"][0]["name"] == "Python"
    assert data["categories"][0]["weakness_score"] == 50.0
