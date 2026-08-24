"""
数据库模型测试
"""
import pytest
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_config import (
    ModelConfig,
    SearchRecord,
    PromptRecord,
    KnowledgeBase,
    QuizQuestion,
    QuizAttempt,
    QuizSession,
    ProviderEnum,
    SourceTypeEnum,
    QuestionTypeEnum,
    DifficultyEnum,
)


# 使用 conftest.py 中的 fixtures
# db_session, sample_model


class TestModelConfig:
    """ModelConfig 模型测试"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_model_config(self, db_session: AsyncSession):
        """测试创建模型配置"""
        model = ModelConfig(
            name="测试模型",
            provider=ProviderEnum.zhipu,
            model_name="glm-4",
            api_url="https://api.example.com",
            api_key_env="TEST_KEY",
            is_default=True,
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        assert model.id is not None
        assert model.name == "测试模型"
        assert model.provider == ProviderEnum.zhipu
        assert model.created_at is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_model_config_default_false(self, db_session: AsyncSession):
        """测试模型配置默认值为 False"""
        model = ModelConfig(
            name="非默认模型",
            provider=ProviderEnum.deepseek,
            model_name="deepseek-chat",
            api_url="https://api.deepseek.com",
            api_key_env="DEEPSEEK_KEY",
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        assert model.is_default is False

    @pytest.mark.unit
    def test_provider_enum_values(self):
        """测试提供商枚举"""
        assert ProviderEnum.zhipu.value == "zhipu"
        assert ProviderEnum.alibaba.value == "alibaba"
        assert ProviderEnum.baidu.value == "baidu"
        assert ProviderEnum.xunfei.value == "xunfei"
        assert ProviderEnum.tencent.value == "tencent"
        assert ProviderEnum.moonshot.value == "moonshot"
        assert ProviderEnum.minimax.value == "minimax"
        assert ProviderEnum.deepseek.value == "deepseek"


class TestSearchRecord:
    """SearchRecord 模型测试"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_search_record(self, db_session: AsyncSession, sample_model: ModelConfig):
        """测试创建搜索记录"""
        record = SearchRecord(
            query="Python 教程",
            engine="duckduckgo",
            result="搜索结果内容",
            sources=[{"title": "Python 官网", "url": "https://python.org"}],
            model_config_id=sample_model.id,
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)

        assert record.id is not None
        assert record.query == "Python 教程"
        assert record.engine == "duckduckgo"
        assert len(record.sources) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_record_with_model_relation(self, db_session: AsyncSession, sample_model: ModelConfig):
        """测试搜索记录与模型的关联"""
        record = SearchRecord(
            query="测试查询",
            engine="tavily",
            result="结果",
            sources=[],
            model_config_id=sample_model.id,
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)

        assert record.model_config_id == sample_model.id


class TestPromptRecord:
    """PromptRecord 模型测试"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_prompt_record(self, db_session: AsyncSession, sample_model: ModelConfig):
        """测试创建提示词记录"""
        record = PromptRecord(
            user_input="帮我写一个数据分析脚本",
            generated_prompt="# 角色\n你是一个专业的数据分析师...",
            model_config_id=sample_model.id,
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)

        assert record.id is not None
        assert record.user_input == "帮我写一个数据分析脚本"
        assert "数据分析师" in record.generated_prompt


class TestKnowledgeBase:
    """KnowledgeBase 模型测试"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_knowledge(self, db_session: AsyncSession):
        """测试创建知识条目"""
        knowledge = KnowledgeBase(
            title="Python 基础",
            content="Python 是一种解释型编程语言...",
            source="https://python.org",
            source_type=SourceTypeEnum.official,
            category="编程语言",
            tags=["Python", "编程"],
        )
        db_session.add(knowledge)
        await db_session.commit()
        await db_session.refresh(knowledge)

        assert knowledge.id is not None
        assert knowledge.title == "Python 基础"
        assert knowledge.source_type == SourceTypeEnum.official

    @pytest.mark.unit
    def test_source_type_enum_values(self):
        """测试来源类型枚举"""
        assert SourceTypeEnum.official.value == "official"
        assert SourceTypeEnum.csdn.value == "csdn"
        assert SourceTypeEnum.arxiv.value == "arxiv"
        assert SourceTypeEnum.github.value == "github"
        assert SourceTypeEnum.manual.value == "manual"


class TestQuizModels:
    """试题相关模型测试"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_quiz_question(self, db_session: AsyncSession):
        """测试创建试题"""
        question = QuizQuestion(
            question="Python 中什么是列表推导式？",
            question_type=QuestionTypeEnum.choice,
            options=["一种循环", "一种创建列表的简洁方式", "一种函数", "一种类"],
            answer="1",
            explanation="列表推导式是 Python 中创建列表的简洁语法",
            difficulty=DifficultyEnum.basic,
            category="Python",
        )
        db_session.add(question)
        await db_session.commit()
        await db_session.refresh(question)

        assert question.id is not None
        assert question.question_type == QuestionTypeEnum.choice
        assert len(question.options) == 4

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_quiz_session(self, db_session: AsyncSession):
        """测试创建答题会话"""
        session = QuizSession(
            category="Python",
            difficulty=DifficultyEnum.intermediate,
            total_questions=10,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.id is not None
        assert session.total_questions == 10
        assert session.correct_count == 0
        assert session.score == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_quiz_attempt(self, db_session: AsyncSession):
        """测试创建答题记录"""
        # 先创建试题和会话
        question = QuizQuestion(
            question="测试问题",
            question_type=QuestionTypeEnum.choice,
            options=["A", "B", "C", "D"],
            answer="0",
            difficulty=DifficultyEnum.basic,
            category="测试",
        )
        db_session.add(question)
        await db_session.flush()

        session = QuizSession(
            category="测试",
            difficulty=DifficultyEnum.basic,
            total_questions=1,
        )
        db_session.add(session)
        await db_session.flush()

        # 创建答题记录
        attempt = QuizAttempt(
            session_id=session.id,
            question_id=question.id,
            user_answer="0",
            is_correct=True,
        )
        db_session.add(attempt)
        await db_session.commit()
        await db_session.refresh(attempt)

        assert attempt.id is not None
        assert attempt.is_correct is True

    @pytest.mark.unit
    def test_question_type_enum_values(self):
        """测试题型枚举"""
        assert QuestionTypeEnum.choice.value == "choice"
        assert QuestionTypeEnum.fill.value == "fill"
        assert QuestionTypeEnum.code.value == "code"

    @pytest.mark.unit
    def test_difficulty_enum_values(self):
        """测试难度枚举"""
        assert DifficultyEnum.basic.value == "basic"
        assert DifficultyEnum.intermediate.value == "intermediate"
        assert DifficultyEnum.advanced.value == "advanced"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_quiz_session_score_update(self, db_session: AsyncSession):
        """测试答题会话分数更新"""
        session = QuizSession(
            category="Python",
            difficulty=DifficultyEnum.basic,
            total_questions=5,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        # 更新分数
        session.correct_count = 4
        session.score = 80.0
        await db_session.commit()
        await db_session.refresh(session)

        assert session.correct_count == 4
        assert session.score == 80.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_quiz_code_question(self, db_session: AsyncSession):
        """测试代码类型试题"""
        question = QuizQuestion(
            question="写一个 Python 函数计算斐波那契数列",
            question_type=QuestionTypeEnum.code,
            options=None,
            answer="def fibonacci(n):\n    ...",
            explanation="使用递归或迭代实现",
            difficulty=DifficultyEnum.advanced,
            category="Python",
        )
        db_session.add(question)
        await db_session.commit()
        await db_session.refresh(question)

        assert question.question_type == QuestionTypeEnum.code
        assert question.options is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_quiz_fill_question(self, db_session: AsyncSession):
        """测试填空类型试题"""
        question = QuizQuestion(
            question="Python 中使用 _____ 关键字定义函数",
            question_type=QuestionTypeEnum.fill,
            options=None,
            answer="def",
            explanation="def 是 define 的缩写",
            difficulty=DifficultyEnum.basic,
            category="Python",
        )
        db_session.add(question)
        await db_session.commit()
        await db_session.refresh(question)

        assert question.question_type == QuestionTypeEnum.fill
        assert question.answer == "def"
