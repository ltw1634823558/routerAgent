"""模型配置路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
import time
from app.services.llm import LLMService

from app.database import get_db
from app.models.model_config import ModelConfig, PromptRecord, SearchRecord
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigResponse,
)

router = APIRouter()


PROVIDER_CAPABILITIES = {
    "zhipu": ["chat", "stream", "vision"],
    "alibaba": ["chat", "stream", "vision"],
    "baidu": ["chat", "stream"],
    "xunfei": ["chat", "stream"],
    "tencent": ["chat", "stream"],
    "moonshot": ["chat", "stream"],
    "minimax": ["chat", "stream", "vision"],
    "deepseek": ["chat", "stream", "reasoning"],
    "custom": ["chat", "stream"],
}


@router.get("/", response_model=List[ModelConfigResponse])
async def get_models(db: AsyncSession = Depends(get_db)):
    """获取所有模型配置"""
    result = await db.execute(select(ModelConfig).order_by(ModelConfig.created_at.desc()))
    models = result.scalars().all()
    for item in models:
        provider = item.provider.value if hasattr(item.provider, "value") else item.provider
        if not item.capabilities:
            item.capabilities = list(PROVIDER_CAPABILITIES.get(provider, ["chat"]))
        if item.fallback_model_ids is None:
            item.fallback_model_ids = []
    return models


@router.get("/providers/list")
async def get_providers():
    """获取支持的模型提供商及其常见能力。"""
    providers = [
        ("zhipu", "智谱 AI", "https://open.bigmodel.cn/api/paas/v4"),
        ("alibaba", "阿里通义", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        ("baidu", "百度文心", "https://aip.baidubce.com/rpc/2.0/ai_custom/v1"),
        ("xunfei", "讯飞星火", "https://spark-api-open.xf-yun.com/v1"),
        ("tencent", "腾讯混元", "https://hunyuan.tencentcloudapi.com"),
        ("moonshot", "月之暗面", "https://api.moonshot.cn/v1"),
        ("minimax", "MiniMax", "https://api.minimax.chat/v1"),
        ("deepseek", "DeepSeek", "https://api.deepseek.com/v1"),
        ("custom", "自定义", ""),
    ]
    return [
            {"value": value, "label": label, "default_url": url, "capabilities": PROVIDER_CAPABILITIES[value]}
            for value, label, url in providers
        ]


@router.post("/", response_model=ModelConfigResponse)
async def create_model(config: ModelConfigCreate, db: AsyncSession = Depends(get_db)):
    """创建模型配置"""
    # 如果设置为默认，先取消其他默认
    if config.is_default:
        result = await db.execute(select(ModelConfig).where(ModelConfig.is_default == True))
        for m in result.scalars().all():
            m.is_default = False

    payload = config.model_dump()
    provider = payload.get("provider", "custom")
    if not payload.get("capabilities"):
        payload["capabilities"] = list(PROVIDER_CAPABILITIES.get(provider, ["chat"]))
    new_config = ModelConfig(**payload)
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    return new_config


@router.get("/{model_id}", response_model=ModelConfigResponse)
async def get_model(model_id: int, db: AsyncSession = Depends(get_db)):
    """获取单个模型配置"""
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    if not config.capabilities:
        provider = config.provider.value if hasattr(config.provider, "value") else config.provider
        config.capabilities = list(PROVIDER_CAPABILITIES.get(provider, ["chat"]))
    if config.fallback_model_ids is None:
        config.fallback_model_ids = []
    return config


@router.put("/{model_id}", response_model=ModelConfigResponse)
async def update_model(model_id: int, config: ModelConfigUpdate, db: AsyncSession = Depends(get_db)):
    """更新模型配置"""
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    # 如果设置为默认，先取消其他默认
    if config.is_default:
        result = await db.execute(
            select(ModelConfig).where(ModelConfig.id != model_id, ModelConfig.is_default == True)
        )
        for m in result.scalars().all():
            m.is_default = False

    for key, value in config.model_dump(exclude_unset=True).items():
        setattr(existing, key, value)

    if not existing.capabilities:
        provider = existing.provider.value if hasattr(existing.provider, "value") else existing.provider
        existing.capabilities = list(PROVIDER_CAPABILITIES.get(provider, ["chat"]))

    await db.commit()
    await db.refresh(existing)
    if not existing.capabilities:
        provider = existing.provider.value if hasattr(existing.provider, "value") else existing.provider
        existing.capabilities = list(PROVIDER_CAPABILITIES.get(provider, ["chat"]))
    if existing.fallback_model_ids is None:
        existing.fallback_model_ids = []
    return existing


@router.delete("/{model_id}")
async def delete_model(model_id: int, db: AsyncSession = Depends(get_db)):
    """删除模型配置"""
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    # 历史记录应保留；先解除引用，兼容旧库中未配置 ON DELETE SET NULL 的外键。
    await db.execute(
        update(SearchRecord)
        .where(SearchRecord.model_config_id == model_id)
        .values(model_config_id=None)
    )
    await db.execute(
        update(PromptRecord)
        .where(PromptRecord.model_config_id == model_id)
        .values(model_config_id=None)
    )
    await db.delete(config)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/{model_id}/test")
async def test_model_connection(model_id: int, db: AsyncSession = Depends(get_db)):
    """测试模型连接，只返回状态和短预览，不暴露 API Key。"""
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    if not config.enabled:
        return {"success": False, "model_id": model_id, "message": "模型已停用"}

    service = LLMService({
        "id": config.id,
        "name": config.name,
        "provider": config.provider.value if hasattr(config.provider, "value") else config.provider,
        "model_name": config.model_name,
        "api_url": config.api_url,
        "api_key_env": config.api_key_env,
    })
    started = time.perf_counter()
    try:
        preview = "".join([chunk async for chunk in service.chat(
            [{"role": "user", "content": "请只回复：连接成功"}], stream=False, max_tokens=32
        )])
    except Exception as exc:
        return {
            "success": False,
            "model_id": model_id,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "message": str(exc),
        }
    return {
        "success": True,
        "model_id": model_id,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "message": "连接成功",
        "response_preview": preview[:100],
    }


@router.put("/{model_id}/default")
async def set_default(model_id: int, db: AsyncSession = Depends(get_db)):
    """设为默认模型"""
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    # 取消其他默认
    result = await db.execute(select(ModelConfig).where(ModelConfig.is_default == True))
    for m in result.scalars().all():
        m.is_default = False

    config.is_default = True
    await db.commit()
    return {"message": "设置成功", "id": config.id, "is_default": config.is_default}
