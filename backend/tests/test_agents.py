"""
Agent 单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.base import BaseAgent
from app.agents.search import SearchAgent
from app.agents.prompt import PromptAgent
from app.agents.quiz import QuizAgent, normalize_question


class TestBaseAgent:
    """BaseAgent 测试"""

    def test_base_agent_is_abstract(self):
        """BaseAgent 应该是抽象类"""
        with pytest.raises(TypeError):
            BaseAgent({})

    def test_base_agent_abstract_method(self):
        """子类必须实现 run 方法"""

        class IncompleteAgent(BaseAgent):
            pass

        with pytest.raises(TypeError):
            IncompleteAgent({})


class TestSearchAgent:
    """SearchAgent 测试"""

    @pytest.fixture
    def model_config(self):
        """测试用模型配置"""
        return {
            "id": 1,
            "name": "测试模型",
            "provider": "zhipu",
            "model_name": "glm-4",
            "api_url": "https://open.bigmodel.cn/api/paas/v4",
            "api_key_env": "TEST_API_KEY",
        }

    @pytest.fixture
    def search_agent(self, model_config):
        """创建 SearchAgent 实例"""
        return SearchAgent(model_config, "duckduckgo", "")

    @pytest.mark.unit
    @pytest.mark.agent
    def test_search_agent_initialization(self, search_agent, model_config):
        """测试 SearchAgent 初始化"""
        assert search_agent.model_config == model_config
        assert search_agent.search_engine == "duckduckgo"

    @pytest.mark.unit
    @pytest.mark.agent
    @pytest.mark.asyncio
    async def test_search_agent_run_success(self, search_agent):
        """测试 SearchAgent 运行成功"""
        # Mock 搜索引擎
        mock_engine = AsyncMock()
        mock_engine.search.return_value = {
            "success": True,
            "results": [
                {"title": "测试结果", "url": "https://example.com", "snippet": "测试内容"}
            ],
            "engine": "mock",
        }
        search_agent.engine = mock_engine

        # Mock LLM 流式响应
        async def mock_stream(*args, **kwargs):
            yield "测试"
            yield "响应"

        with patch.object(search_agent, 'stream_response', mock_stream):
            results = []
            async for chunk in search_agent.run("测试查询"):
                results.append(chunk)

            assert len(results) > 0

    @pytest.mark.unit
    @pytest.mark.agent
    @pytest.mark.asyncio
    async def test_search_agent_run_search_failure(self, search_agent):
        """测试 SearchAgent 搜索失败"""
        mock_engine = AsyncMock()
        mock_engine.search.return_value = {
            "success": False,
            "error": "搜索失败",
            "results": [],
            "engine": "mock",
        }
        search_agent.engine = mock_engine

        results = []
        async for chunk in search_agent.run("测试查询"):
            results.append(chunk)

        assert "搜索出错" in "".join(results) or "搜索失败" in "".join(results)

    @pytest.mark.unit
    @pytest.mark.agent
    @pytest.mark.asyncio
    async def test_search_agent_run_exception(self, search_agent):
        """测试 SearchAgent 异常处理"""
        mock_engine = AsyncMock()
        mock_engine.search.side_effect = Exception("网络错误")
        search_agent.engine = mock_engine

        results = []
        async for chunk in search_agent.run("测试查询"):
            results.append(chunk)

        assert "搜索失败" in "".join(results) or "网络错误" in "".join(results)

    @pytest.mark.unit
    @pytest.mark.agent
    def test_search_agent_build_subqueries_keeps_original_and_is_bounded(self):
        queries = SearchAgent.build_subqueries("Python 异步编程", max_subqueries=3)
        assert queries[0] == "Python 异步编程"
        assert len(queries) == 3
        assert len(set(queries)) == 3

    @pytest.mark.unit
    @pytest.mark.agent
    def test_search_agent_prepare_sources_deduplicates_tracking_urls(self):
        sources = SearchAgent._prepare_sources([
            {
                "title": "文档",
                "url": "https://docs.example.com/a?utm_source=x",
                "snippet": "短摘要",
            },
            {
                "title": "文档（完整）",
                "url": "https://docs.example.com/a/",
                "snippet": "这是更长的摘要内容",
            },
            {
                "title": "官方文档",
                "url": "https://python.org/guide",
                "snippet": "内容",
            },
        ])
        assert len(sources) == 2
        assert sources[0]["citation_id"] == "S1"
        assert sources[0]["url"] == "https://python.org/guide"
        assert sources[1]["snippet"] == "这是更长的摘要内容"

    @pytest.mark.unit
    @pytest.mark.agent
    @pytest.mark.asyncio
    async def test_search_agent_deep_search_parallel_and_citations(self, search_agent):
        calls = []

        async def mock_search(query, max_results=10):
            calls.append(query)
            return {
                "success": True,
                "results": [{
                    "title": f"结果 {query}",
                    "url": "https://example.com/shared" if query != calls[0] else "https://example.com/one",
                    "snippet": f"关于 {query} 的内容",
                }],
            }

        async def mock_stream(prompt):
            assert "[S1]" in prompt
            assert "深度检索" in prompt
            yield "综合答案 [S1]"

        search_agent.engine.search = mock_search
        with patch.object(search_agent, "stream_response", mock_stream):
            chunks = []
            async for chunk in search_agent.run("测试主题", deep_search=True, max_subqueries=3):
                chunks.append(chunk)

        assert len(calls) == 3
        assert "综合答案 [S1]" in "".join(chunks)
        assert "深度检索来源" in "".join(chunks)
        assert len(search_agent.last_sources) == 2


class TestPromptAgent:
    """PromptAgent 测试"""

    @pytest.fixture
    def model_config(self):
        """测试用模型配置"""
        return {
            "id": 1,
            "name": "测试模型",
            "provider": "zhipu",
            "model_name": "glm-4",
            "api_url": "https://open.bigmodel.cn/api/paas/v4",
            "api_key_env": "TEST_API_KEY",
        }

    @pytest.fixture
    def prompt_agent(self, model_config):
        """创建 PromptAgent 实例"""
        return PromptAgent(model_config)

    @pytest.mark.unit
    @pytest.mark.agent
    def test_prompt_agent_initialization(self, prompt_agent, model_config):
        """测试 PromptAgent 初始化"""
        assert prompt_agent.model_config == model_config

    @pytest.mark.unit
    @pytest.mark.agent
    @pytest.mark.asyncio
    async def test_prompt_agent_run_success(self, prompt_agent):
        """测试 PromptAgent 运行成功"""
        # Mock LLM 流式响应
        async def mock_stream(*args, **kwargs):
            yield "# 优化后的提示词\n"
            yield "你是一个专业的助手"

        with patch.object(prompt_agent, 'stream_response', mock_stream):
            results = []
            async for chunk in prompt_agent.run("帮我写一个代码"):
                results.append(chunk)

            assert len(results) > 0
            full_response = "".join(results)
            assert "提示词" in full_response or "助手" in full_response

    @pytest.mark.unit
    @pytest.mark.agent
    @pytest.mark.asyncio
    async def test_prompt_agent_with_different_inputs(self, prompt_agent):
        """测试 PromptAgent 不同输入"""
        test_inputs = [
            "帮我分析数据",
            "写一个 Python 脚本",
            "生成一封邮件",
        ]

        async def mock_stream(*args, **kwargs):
            yield "测试响应"

        with patch.object(prompt_agent, 'stream_response', mock_stream):
            for user_input in test_inputs:
                results = []
                async for chunk in prompt_agent.run(user_input):
                    results.append(chunk)
                assert len(results) > 0


class TestQuizAgent:
    """QuizAgent 测试"""

    @pytest.fixture
    def model_config(self):
        """测试用模型配置"""
        return {
            "id": 1,
            "name": "测试模型",
            "provider": "zhipu",
            "model_name": "glm-4",
            "api_url": "https://open.bigmodel.cn/api/paas/v4",
            "api_key_env": "TEST_API_KEY",
        }

    @pytest.fixture
    def quiz_agent(self, model_config):
        """创建 QuizAgent 实例"""
        return QuizAgent(model_config)

    @pytest.mark.unit
    @pytest.mark.agent
    def test_quiz_agent_initialization(self, quiz_agent, model_config):
        """测试 QuizAgent 初始化"""
        assert quiz_agent.model_config == model_config

    @pytest.mark.unit
    @pytest.mark.agent
    @pytest.mark.asyncio
    async def test_quiz_agent_run_success(self, quiz_agent):
        """测试 QuizAgent 运行成功"""
        # Mock LLM 流式响应返回 JSON 格式试题
        quiz_json = '''
        [
            {
                "question": "Python 中什么是列表推导式？",
                "type": "choice",
                "options": ["一种循环", "一种创建列表的简洁方式", "一种函数", "一种类"],
                "answer": 1,
                "explanation": "列表推导式是 Python 中创建列表的简洁语法"
            }
        ]
        '''

        async def mock_stream(*args, **kwargs):
            yield quiz_json

        with patch.object(quiz_agent, 'stream_response', mock_stream):
            results = []
            async for chunk in quiz_agent.run("Python", "basic", 1, ""):
                results.append(chunk)

            assert len(results) > 0

    @pytest.mark.unit
    @pytest.mark.agent
    def test_quiz_agent_parse_questions(self, quiz_agent):
        """测试 QuizAgent 解析试题"""
        valid_json = '''
        [
            {
                "question": "测试问题",
                "type": "choice",
                "options": ["选项A", "选项B", "选项C", "选项D"],
                "answer": 0,
                "explanation": "测试解释"
            }
        ]
        '''
        questions = quiz_agent.parse_questions(valid_json)
        assert questions is not None
        assert len(questions) == 1
        assert questions[0]["question"] == "测试问题"

    @pytest.mark.unit
    @pytest.mark.agent
    def test_quiz_agent_parse_invalid_json(self, quiz_agent):
        """测试 QuizAgent 解析无效 JSON"""
        invalid_json = "不是有效的 JSON"
        questions = quiz_agent.parse_questions(invalid_json)
        assert questions is None

    @pytest.mark.unit
    @pytest.mark.agent
    def test_quiz_agent_parse_empty_json(self, quiz_agent):
        """测试 QuizAgent 解析空 JSON"""
        questions = quiz_agent.parse_questions("[]")
        assert questions == []

    @pytest.mark.unit
    @pytest.mark.agent
    def test_quiz_agent_parse_missing_fields(self, quiz_agent):
        """测试 QuizAgent 解析缺少字段的 JSON"""
        incomplete_json = '''
        [
            {
                "question": "测试问题"
            }
        ]
        '''
        questions = quiz_agent.parse_questions(incomplete_json)
        # 应该处理缺少字段的情况
        assert questions is not None or questions == []

    @pytest.mark.unit
    @pytest.mark.agent
    @pytest.mark.asyncio
    async def test_quiz_agent_different_difficulties(self, quiz_agent):
        """测试 QuizAgent 不同难度"""
        difficulties = ["basic", "intermediate", "advanced"]

        async def mock_stream(*args, **kwargs):
            yield '[{"question": "测试", "type": "choice", "options": ["A", "B"], "answer": 0}]'

        with patch.object(quiz_agent, 'stream_response', mock_stream):
            for difficulty in difficulties:
                results = []
                async for chunk in quiz_agent.run("Python", difficulty, 1, ""):
                    results.append(chunk)
                assert len(results) > 0

    @pytest.mark.unit
    @pytest.mark.agent
    @pytest.mark.asyncio
    async def test_quiz_agent_with_knowledge_context(self, quiz_agent):
        """测试 QuizAgent 使用知识库上下文"""
        knowledge_context = "Python 是一种解释型编程语言，支持面向对象编程。"

        async def mock_stream(*args, **kwargs):
            yield '[{"question": "Python 是什么类型的语言？", "type": "choice", "options": ["编译型", "解释型"], "answer": 1}]'

        with patch.object(quiz_agent, 'stream_response', mock_stream):
            results = []
            async for chunk in quiz_agent.run("Python", "basic", 1, knowledge_context):
                results.append(chunk)
            assert len(results) > 0


def test_quiz_normalize_python_class_code_answer():
    question = normalize_question({
        "question": "请编写一个 Python 类",
        "type": "python_class",
        "code_answer": "```python\nclass User:\n    pass\n```",
    })
    assert question["question_type"] == "code"
    assert question["answer"] == "class User:\n    pass"


def test_quiz_parse_legacy_code_fields():
    questions = QuizAgent({}).parse_questions(
        '{"questions":[{"text":"实现函数","question_type":"coding",'
        '"reference_code":"```python\\ndef f():\\n    return 1\\n```"}]}'
    )
    assert questions[0]["question"] == "实现函数"
    assert questions[0]["question_type"] == "code"
    assert questions[0]["answer"] == "def f():\n    return 1"
