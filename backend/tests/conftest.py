"""
测试配置和 fixtures
"""
import asyncio
import os
import sys
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import Base, get_db
from app.models.model_config import ModelConfig, ProviderEnum

# 使用 SQLite 内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def sample_model(db_session: AsyncSession) -> ModelConfig:
    """创建示例模型配置"""
    model = ModelConfig(
        name="测试模型",
        provider=ProviderEnum.zhipu,
        model_name="glm-4",
        api_url="https://open.bigmodel.cn/api/paas/v4",
        api_key_env="TEST_API_KEY",
        is_default=True,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture(scope="function")
async def multiple_models(db_session: AsyncSession) -> list[ModelConfig]:
    """创建多个示例模型配置"""
    models = [
        ModelConfig(
            name="智谱 GLM-4",
            provider=ProviderEnum.zhipu,
            model_name="glm-4",
            api_url="https://open.bigmodel.cn/api/paas/v4",
            api_key_env="ZHIPU_API_KEY",
            is_default=True,
        ),
        ModelConfig(
            name="DeepSeek",
            provider=ProviderEnum.deepseek,
            model_name="deepseek-chat",
            api_url="https://api.deepseek.com/v1",
            api_key_env="DEEPSEEK_API_KEY",
            is_default=False,
        ),
        ModelConfig(
            name="阿里通义",
            provider=ProviderEnum.alibaba,
            model_name="qwen-turbo",
            api_url="https://dashscope.aliyuncs.com/api/v1",
            api_key_env="ALIBABA_API_KEY",
            is_default=False,
        ),
    ]
    db_session.add_all(models)
    await db_session.commit()
    for model in models:
        await db_session.refresh(model)
    return models


# Pytest markers 配置
def pytest_configure(config):
    """配置自定义 markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "websocket: WebSocket tests")
    config.addinivalue_line("markers", "agent: Agent tests")


# Mock LLM 响应
class MockLLMService:
    """模拟 LLM 服务"""

    @staticmethod
    async def stream_chat(*args, **kwargs):
        """模拟流式响应"""
        responses = ["这是", "一个", "测试", "响应"]
        for text in responses:
            yield text

    @staticmethod
    async def chat(*args, **kwargs):
        """模拟非流式响应"""
        return "这是一个测试响应"


# Mock 搜索引擎响应
class MockSearchEngine:
    """模拟搜索引擎"""

    async def search(self, query: str, max_results: int = 10):
        """模拟搜索"""
        return {
            "success": True,
            "results": [
                {
                    "title": "测试结果1",
                    "url": "https://example.com/1",
                    "snippet": "这是测试搜索结果1的内容",
                },
                {
                    "title": "测试结果2",
                    "url": "https://example.com/2",
                    "snippet": "这是测试搜索结果2的内容",
                },
            ],
            "engine": "mock",
        }
