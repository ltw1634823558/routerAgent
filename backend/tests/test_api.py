"""
API Endpoint 测试
"""
import pytest
from httpx import AsyncClient

from app.models.model_config import ModelConfig, ProviderEnum, SourceTypeEnum


class TestHealthEndpoint:
    """健康检查端点测试"""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """测试健康检查端点"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestModelConfigAPI:
    """模型配置 API 测试"""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_all_models_empty(self, client: AsyncClient):
        """测试获取空模型列表"""
        response = await client.get("/api/model/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_model(self, client: AsyncClient):
        """测试创建模型配置"""
        model_data = {
            "name": "测试模型",
            "provider": "zhipu",
            "model_name": "glm-4",
            "api_url": "https://open.bigmodel.cn/api/paas/v4",
            "api_key_env": "TEST_API_KEY",
            "is_default": True,
        }
        response = await client.post("/api/model/", json=model_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "测试模型"
        assert data["provider"] == "zhipu"
        assert data["is_default"] is True

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_all_models_with_data(self, client: AsyncClient, sample_model: ModelConfig):
        """测试获取模型列表（有数据）"""
        response = await client.get("/api/model/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "测试模型"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_model_by_id(self, client: AsyncClient, sample_model: ModelConfig):
        """测试获取单个模型"""
        response = await client.get(f"/api/model/{sample_model.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_model.id
        assert data["name"] == "测试模型"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_model_not_found(self, client: AsyncClient):
        """测试获取不存在的模型"""
        response = await client.get("/api/model/999")
        assert response.status_code == 404

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_update_model(self, client: AsyncClient, sample_model: ModelConfig):
        """测试更新模型配置"""
        update_data = {
            "name": "更新后的模型",
            "provider": "deepseek",
            "model_name": "deepseek-chat",
            "api_url": "https://api.deepseek.com/v1",
            "api_key_env": "DEEPSEEK_API_KEY",
            "is_default": False,
        }
        response = await client.put(f"/api/model/{sample_model.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新后的模型"
        assert data["provider"] == "deepseek"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_delete_model(self, client: AsyncClient, sample_model: ModelConfig):
        """测试删除模型配置"""
        # 先创建一个模型
        response = await client.get(f"/api/model/{sample_model.id}")
        assert response.status_code == 200

        # 删除模型
        delete_response = await client.delete(f"/api/model/{sample_model.id}")
        assert delete_response.status_code == 200

        # 确认已删除
        get_response = await client.get(f"/api/model/{sample_model.id}")
        assert get_response.status_code == 404

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_set_default_model(self, client: AsyncClient, multiple_models: list[ModelConfig]):
        """测试设置默认模型"""
        # 获取非默认模型
        non_default_model = multiple_models[1]
        assert non_default_model.is_default is False

        # 设置为默认
        response = await client.put(f"/api/model/{non_default_model.id}/default")
        assert response.status_code == 200

        # 验证已设为默认
        data = response.json()
        assert data["is_default"] is True

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_providers_list(self, client: AsyncClient):
        """测试获取提供商列表"""
        response = await client.get("/api/model/providers/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # 检查是否包含常见提供商
        providers = [p["value"] for p in data]
        assert "zhipu" in providers
        assert "deepseek" in providers


class TestKnowledgeAPI:
    """知识库 API 测试"""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_knowledge_list_empty(self, client: AsyncClient):
        """测试获取空知识库列表"""
        response = await client.get("/api/knowledge/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_knowledge(self, client: AsyncClient):
        """测试创建知识条目"""
        knowledge_data = {
            "title": "Python 基础知识",
            "content": "Python 是一种解释型编程语言...",
            "source": "https://example.com/python",
            "source_type": "manual",
            "category": "编程语言",
            "tags": ["Python", "编程"],
        }
        response = await client.post("/api/knowledge/", json=knowledge_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Python 基础知识"
        assert data["source_type"] == "manual"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_knowledge_stats(self, client: AsyncClient):
        """测试获取知识库统计"""
        response = await client.get("/api/knowledge/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_type" in data

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_source_types(self, client: AsyncClient):
        """测试获取来源类型列表"""
        response = await client.get("/api/knowledge/source-types")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_filter_knowledge_by_category(self, client: AsyncClient):
        """测试按分类筛选知识"""
        # 先创建一些知识条目
        for i in range(3):
            await client.post("/api/knowledge/", json={
                "title": f"知识{i+1}",
                "content": f"内容{i+1}",
                "source_type": "manual",
                "category": "分类A" if i < 2 else "分类B",
            })

        # 按分类筛选
        response = await client.get("/api/knowledge/?category=分类A")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestSearchAPI:
    """搜索 API 测试"""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_search_records_empty(self, client: AsyncClient):
        """测试获取空搜索记录"""
        response = await client.get("/api/search/records")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_engines_list(self, client: AsyncClient):
        """测试获取搜索引擎列表"""
        response = await client.get("/api/search/engines/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestPromptAPI:
    """提示词 API 测试"""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_prompt_records_empty(self, client: AsyncClient):
        """测试获取空提示词记录"""
        response = await client.get("/api/prompt/records")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestQuizAPI:
    """试题 API 测试"""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_categories(self, client: AsyncClient):
        """测试获取技能分类"""
        response = await client.get("/api/quiz/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_difficulties(self, client: AsyncClient):
        """测试获取难度级别"""
        response = await client.get("/api/quiz/difficulties")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_history_empty(self, client: AsyncClient):
        """测试获取空答题历史"""
        response = await client.get("/api/quiz/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
