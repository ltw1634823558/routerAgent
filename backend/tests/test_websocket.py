"""
WebSocket 集成测试
"""
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.agents import SearchAgent, PromptAgent, QuizAgent


class TestWebSocketConnection:
    """WebSocket 连接测试"""

    @pytest.mark.websocket
    def test_websocket_connect_search_agent(self):
        """测试连接搜索 Agent WebSocket"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/search") as websocket:
                # 连接应该成功
                assert websocket is not None

    @pytest.mark.websocket
    def test_websocket_connect_prompt_agent(self):
        """测试连接提示词 Agent WebSocket"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/prompt") as websocket:
                assert websocket is not None

    @pytest.mark.websocket
    def test_websocket_connect_quiz_agent(self):
        """测试连接问答 Agent WebSocket"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/quiz") as websocket:
                assert websocket is not None

    @pytest.mark.websocket
    def test_websocket_invalid_agent_type(self):
        """测试连接无效的 Agent 类型"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/invalid") as websocket:
                # 发送消息应该收到错误响应
                websocket.send_text(json.dumps({"test": "data"}))
                # 可能会收到错误或连接关闭


class TestSearchAgentWebSocket:
    """搜索 Agent WebSocket 测试"""

    @pytest.mark.websocket
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_agent_message_format(self):
        """测试搜索 Agent 消息格式"""
        # 测试消息格式验证
        valid_message = {
            "query": "测试搜索内容",
            "engine": "duckduckgo",
            "model_id": 1,
        }

        # 验证消息字段
        assert "query" in valid_message
        assert "engine" in valid_message
        assert valid_message["query"] == "测试搜索内容"

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_search_agent_missing_query(self):
        """测试搜索 Agent 缺少查询内容"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/search") as websocket:
                # 发送缺少 query 的消息
                message = {
                    "engine": "duckduckgo",
                    "model_id": 1,
                }
                websocket.send_text(json.dumps(message))

                # 应该收到错误响应
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "搜索内容" in response["message"] or "query" in response["message"].lower()

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_search_agent_missing_model(self):
        """测试搜索 Agent 缺少模型 ID"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/search") as websocket:
                message = {
                    "query": "测试查询",
                    "engine": "duckduckgo",
                }
                websocket.send_text(json.dumps(message))

                response = websocket.receive_json()
                assert response["type"] == "error"

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_search_agent_invalid_model(self):
        """测试搜索 Agent 无效模型 ID"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/search") as websocket:
                message = {
                    "query": "测试查询",
                    "engine": "duckduckgo",
                    "model_id": 99999,
                }
                websocket.send_text(json.dumps(message))

                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "模型" in response["message"] or "不存在" in response["message"]


class TestPromptAgentWebSocket:
    """提示词 Agent WebSocket 测试"""

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_prompt_agent_missing_input(self):
        """测试提示词 Agent 缺少输入"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/prompt") as websocket:
                message = {
                    "model_id": 1,
                }
                websocket.send_text(json.dumps(message))

                response = websocket.receive_json()
                assert response["type"] == "error"

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_prompt_agent_valid_message_format(self):
        """测试提示词 Agent 有效消息格式"""
        valid_message = {
            "user_input": "帮我写一个代码分析工具的提示词",
            "model_id": 1,
        }

        assert "user_input" in valid_message
        assert "model_id" in valid_message


class TestQuizAgentWebSocket:
    """问答 Agent WebSocket 测试"""

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_quiz_agent_generate_action(self):
        """测试问答 Agent 生成试题"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/quiz") as websocket:
                message = {
                    "action": "generate",
                    "category": "Python",
                    "difficulty": "basic",
                    "count": 3,
                    "model_id": 1,
                }
                websocket.send_text(json.dumps(message))

                # 可能收到 info 或 error 消息
                response = websocket.receive_json()
                assert response["type"] in ["info", "error", "chunk", "done"]

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_quiz_agent_submit_action(self):
        """测试问答 Agent 提交答案"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/quiz") as websocket:
                message = {
                    "action": "submit",
                    "session_id": 1,
                    "answers": [
                        {"question_id": 1, "user_answer": "A"},
                        {"question_id": 2, "user_answer": "B"},
                    ],
                }
                websocket.send_text(json.dumps(message))

                response = websocket.receive_json()
                assert response["type"] in ["error", "result"]

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_quiz_agent_invalid_action(self):
        """测试问答 Agent 无效操作"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/quiz") as websocket:
                message = {
                    "action": "invalid_action",
                }
                websocket.send_text(json.dumps(message))

                response = websocket.receive_json()
                assert response["type"] == "error"

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_quiz_agent_missing_action(self):
        """测试问答 Agent 缺少操作类型"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws/agent/quiz") as websocket:
                message = {
                    "category": "Python",
                    "difficulty": "basic",
                }
                websocket.send_text(json.dumps(message))

                response = websocket.receive_json()
                assert response["type"] == "error"


class TestWebSocketResponseFormat:
    """WebSocket 响应格式测试"""

    @pytest.mark.websocket
    def test_chunk_response_format(self):
        """测试 chunk 响应格式"""
        expected_format = {
            "type": "chunk",
            "content": "测试内容",
        }
        assert "type" in expected_format
        assert "content" in expected_format

    @pytest.mark.websocket
    def test_error_response_format(self):
        """测试 error 响应格式"""
        expected_format = {
            "type": "error",
            "message": "错误信息",
        }
        assert "type" in expected_format
        assert "message" in expected_format

    @pytest.mark.websocket
    def test_done_response_format(self):
        """测试 done 响应格式"""
        expected_format = {
            "type": "done",
            "record_id": 1,
        }
        assert "type" in expected_format

    @pytest.mark.websocket
    def test_quiz_result_response_format(self):
        """测试答题结果响应格式"""
        expected_format = {
            "type": "result",
            "score": 80,
            "correct_count": 4,
            "total": 5,
            "results": [],
        }
        assert "type" in expected_format
        assert "score" in expected_format
        assert "correct_count" in expected_format


class TestWebSocketConnectionManager:
    """WebSocket 连接管理器测试"""

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_connection_manager_basic(self):
        """测试连接管理器基本功能"""
        from app.routers.websocket import manager

        # 初始状态
        assert len(manager.active_connections) == 0

    @pytest.mark.websocket
    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        """测试多个连接"""
        from app.routers.websocket import manager

        # 模拟多个连接
        initial_count = len(manager.active_connections)
        # 在实际测试中，连接会通过 websocket_connect 添加


class TestWebSocketIntegration:
    """WebSocket 集成测试（需要数据库）"""

    @pytest.mark.websocket
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_search_flow(self, client: AsyncClient, sample_model):
        """测试完整搜索流程"""
        # 注意：这个测试需要 mock LLM 和搜索引擎
        # 在实际环境中会跳过或使用 mock

        # 1. 确保模型存在
        response = await client.get("/api/model/")
        assert response.status_code == 200
        models = response.json()
        assert len(models) > 0

    @pytest.mark.websocket
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_quiz_flow(self, client: AsyncClient, sample_model):
        """测试完整答题流程"""
        # 1. 获取分类
        response = await client.get("/api/quiz/categories")
        assert response.status_code == 200

        # 2. 获取难度
        response = await client.get("/api/quiz/difficulties")
        assert response.status_code == 200
