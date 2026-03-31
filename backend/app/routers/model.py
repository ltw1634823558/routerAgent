"""模型配置路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.model_config import ModelConfig
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigResponse,
)

router = APIRouter()


@router.get("/", response_model=List[ModelConfigResponse])
async def get_models(db: AsyncSession = Depends(get_db)):
    """获取所有模型配置"""
    result = await db.execute(select(ModelConfig).order_by(ModelConfig.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=ModelConfigResponse)
async def create_model(config: ModelConfigCreate, db: AsyncSession = Depends(get_db)):
    """创建模型配置"""
    # 如果设置为默认，先取消其他默认
    if config.is_default:
        result = await db.execute(select(ModelConfig).where(ModelConfig.is_default == True))
        for m in result.scalars().all():
            m.is_default = False

    new_config = ModelConfig(**config.model_dump())
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

    await db.commit()
    await db.refresh(existing)
    return existing


@router.delete("/{model_id}")
async def delete_model(model_id: int, db: AsyncSession = Depends(get_db)):
    """删除模型配置"""
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    await db.delete(config)
    await db.commit()
    return {"message": "删除成功"}


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
    return {"message": "设置成功"}


@router.get("/providers/list")
async def get_providers():
    """获取支持的模型提供商列表"""
    return {
        "providers": [
            {"value": "zhipu", "label": "智谱 AI", "default_url": "https://open.bigmodel.cn/api/paas/v4"},
            {"value": "alibaba", "label": "阿里通义", "default_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
            {"value": "baidu", "label": "百度文心", "default_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1"},
            {"value": "xunfei", "label": "讯飞星火", "default_url": "https://spark-api-open.xf-yun.com/v1"},
            {"value": "tencent", "label": "腾讯混元", "default_url": "https://hunyuan.tencentcloudapi.com"},
            {"value": "moonshot", "label": "月之暗面", "default_url": "https://api.moonshot.cn/v1"},
            {"value": "minimax", "label": "MiniMax", "default_url": "https://api.minimax.chat/v1"},
            {"value": "deepseek", "label": "DeepSeek", "default_url": "https://api.deepseek.com/v1"},
            {"value": "custom", "label": "自定义", "default_url": ""},
        ]
    }
