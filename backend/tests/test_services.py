"""
服务层测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLLMService:
    """LLM 服务测试"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_service_initialization(self):
        """测试 LLM 服务初始化"""
        from app.services.llm.base import LLMService

        config = {
            "provider": "zhipu",
            "model_name": "glm-4",
            "api_url": "https://open.bigmodel.cn/api/paas/v4",
            "api_key_env": "TEST_API_KEY",
        }

        service = LLMService(config)
        assert service.config == config
        assert service.provider == "zhipu"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_service_invalid_provider(self):
        """测试 LLM 服务无效提供商"""
        from app.services.llm.base import LLMService

        config = {
            "provider": "invalid_provider",
            "model_name": "test-model",
            "api_url": "https://api.example.com",
            "api_key_env": "TEST_API_KEY",
        }

        service = LLMService(config)
        # 应该使用默认的 OpenAI 兼容格式

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_llm_service_missing_api_key_raises_clear_error(self, monkeypatch):
        """缺少密钥时不应构造无效的 Authorization 请求头。"""
        from app.services.llm.base import LLMService

        monkeypatch.delenv("TEST_API_KEY", raising=False)
        service = LLMService({
            "provider": "deepseek",
            "model_name": "deepseek-chat",
            "api_url": "https://api.deepseek.com/v1",
            "api_key_env": "TEST_API_KEY",
        })

        with pytest.raises(ValueError, match="未检测到 API Key"):
            await anext(service.chat([{"role": "user", "content": "测试"}]))

    @pytest.mark.unit
    def test_model_config_rejects_api_key_literal(self):
        """模型配置只能保存环境变量名，不允许保存 API Key。"""
        from pydantic import ValidationError
        from app.schemas.model_config import ModelConfigCreate

        with pytest.raises(ValidationError, match="API Key 环境变量名"):
            ModelConfigCreate(
                name="DeepSeek",
                provider="deepseek",
                model_name="deepseek-chat",
                api_url="https://api.deepseek.com/v1",
                api_key_env="sk-example-key",
            )


class TestSearchEngines:
    """搜索引擎测试"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_duckduckgo_engine_initialization(self):
        """测试 DuckDuckGo 搜索引擎初始化"""
        from app.services.search.engines import DuckDuckGoEngine

        engine = DuckDuckGoEngine()
        assert engine.api_key == ""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_tavily_engine_initialization(self):
        """测试 Tavily 搜索引擎初始化"""
        from app.services.search.engines import TavilyEngine

        engine = TavilyEngine(api_key="test_key")
        assert engine.api_key == "test_key"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_search_engine_factory(self):
        """测试搜索引擎工厂函数"""
        from app.services.search.engines import get_search_engine, DuckDuckGoEngine, TavilyEngine, BingEngine

        # DuckDuckGo
        engine = get_search_engine("duckduckgo")
        assert isinstance(engine, DuckDuckGoEngine)

        # Tavily
        engine = get_search_engine("tavily", api_key="test")
        assert isinstance(engine, TavilyEngine)

        # Bing
        engine = get_search_engine("bing", api_key="test")
        assert isinstance(engine, BingEngine)

    @pytest.mark.unit
    def test_invalid_search_engine(self):
        """测试无效搜索引擎"""
        from app.services.search.engines import get_search_engine

        with pytest.raises(ValueError):
            get_search_engine("invalid_engine")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_duckduckgo_search_success(self):
        """测试 DuckDuckGo 搜索成功"""
        from app.services.search.engines import DuckDuckGoEngine

        engine = DuckDuckGoEngine()

        # Mock DDGS
        with patch("app.services.search.engines.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {"title": "测试结果", "href": "https://example.com", "body": "测试内容"}
            ]
            mock_ddgs.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_ddgs.return_value.__exit__ = MagicMock(return_value=False)

            result = await engine.search("测试查询")

            assert result["success"] is True
            assert result["engine"] == "duckduckgo"
            assert len(result["results"]) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_tavily_search_missing_key(self):
        """测试 Tavily 搜索缺少 API Key"""
        from app.services.search.engines import TavilyEngine

        engine = TavilyEngine(api_key="")
        result = await engine.search("测试查询")

        assert result["success"] is False
        assert "API Key" in result["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bing_search_missing_key(self):
        """测试 Bing 搜索缺少 API Key"""
        from app.services.search.engines import BingEngine

        engine = BingEngine(api_key="")
        result = await engine.search("测试查询")

        assert result["success"] is False
        assert "API Key" in result["error"]


class TestCrawlerService:
    """爬虫服务测试"""

    @pytest.mark.unit
    def test_crawler_base_is_abstract(self):
        """测试爬虫基类是抽象类"""
        from app.services.crawler.base import BaseCrawler

        with pytest.raises(TypeError):
            BaseCrawler()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_arxiv_crawler_initialization(self):
        """测试 arXiv 爬虫初始化"""
        from app.services.crawler.arxiv import ArxivCrawler

        crawler = ArxivCrawler()
        assert crawler is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_github_crawler_initialization(self):
        """测试 GitHub 爬虫初始化"""
        from app.services.crawler.github import GithubCrawler

        crawler = GithubCrawler()
        assert crawler is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_csdn_crawler_initialization(self):
        """测试 CSDN 爬虫初始化"""
        from app.services.crawler.csdn import CSDNCrawler

        crawler = CSDNCrawler()
        assert crawler is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_official_crawler_initialization(self):
        """测试官方文档爬虫初始化"""
        from app.services.crawler.official import OfficialCrawler

        crawler = OfficialCrawler()
        assert crawler is not None


class TestModelEnums:
    """模型枚举测试"""

    @pytest.mark.unit
    def test_provider_enum_values(self):
        """测试提供商枚举值"""
        from app.models.model_config import ProviderEnum

        assert ProviderEnum.zhipu.value == "zhipu"
        assert ProviderEnum.alibaba.value == "alibaba"
        assert ProviderEnum.baidu.value == "baidu"

    @pytest.mark.unit
    def test_source_type_enum_values(self):
        """测试来源类型枚举值"""
        from app.models.model_config import SourceTypeEnum

        assert SourceTypeEnum.official.value == "official"
        assert SourceTypeEnum.csdn.value == "csdn"
        assert SourceTypeEnum.manual.value == "manual"

    @pytest.mark.unit
    def test_difficulty_enum_values(self):
        """测试难度枚举值"""
        from app.models.model_config import DifficultyEnum

        assert DifficultyEnum.basic.value == "basic"
        assert DifficultyEnum.intermediate.value == "intermediate"
        assert DifficultyEnum.advanced.value == "advanced"

    @pytest.mark.unit
    def test_question_type_enum_values(self):
        """测试题型枚举值"""
        from app.models.model_config import QuestionTypeEnum

        assert QuestionTypeEnum.choice.value == "choice"
        assert QuestionTypeEnum.fill.value == "fill"
        assert QuestionTypeEnum.code.value == "code"
