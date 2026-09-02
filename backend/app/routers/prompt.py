"""提示词 Agent 与 Prompt IDE 路由。"""
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.model_config import ModelConfig, PromptRecord
from app.models.prompt import PromptTemplate, PromptVersion
from app.schemas.model_config import (
    PromptDiffResponse,
    PromptRecordResponse,
    PromptRenderRequest,
    PromptRenderResponse,
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTemplateUpdate,
    PromptTestRequest,
    PromptTestResponse,
    PromptVersionCreate,
    PromptVersionResponse,
)
from app.services.prompt import (
    normalize_variables,
    render_prompt_template,
    unified_prompt_diff,
)
from app.services.llm import LLMService

router = APIRouter()


def _template_payload(template: PromptTemplate) -> dict[str, Any]:
    """Ensure legacy/null JSON values are serialized consistently."""

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "content": template.content,
        "variables": template.variables or [],
        "tags": template.tags or [],
        "current_version": template.current_version or 1,
        "created_at": template.created_at,
        "updated_at": template.updated_at or template.created_at,
    }


def _version_payload(version: PromptVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "template_id": version.template_id,
        "version": version.version,
        "content": version.content,
        "variables": version.variables or [],
        "change_note": version.change_note,
        "created_at": version.created_at,
    }


async def _get_template(template_id: int, db: AsyncSession) -> PromptTemplate:
    result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="提示词模板不存在")
    return template


async def _get_version(template_id: int, version_number: int, db: AsyncSession) -> PromptVersion:
    result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.template_id == template_id,
            PromptVersion.version == version_number,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="提示词版本不存在")
    return version


async def _model_payload(model_id: int, db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    config = result.scalar_one_or_none()
    if not config or not getattr(config, "enabled", True):
        raise HTTPException(status_code=404, detail="模型配置不存在或已停用")

    def serialize(item: ModelConfig) -> dict[str, Any]:
        provider = item.provider.value if hasattr(item.provider, "value") else item.provider
        return {
            "id": item.id,
            "name": item.name,
            "provider": provider,
            "model_name": item.model_name,
            "api_url": item.api_url,
            "api_key_env": item.api_key_env,
            "capabilities": item.capabilities or [],
        }

    selected = serialize(config)
    fallback_ids = [int(value) for value in (config.fallback_model_ids or []) if str(value).isdigit()]
    if fallback_ids:
        fallback_result = await db.execute(
            select(ModelConfig).where(
                ModelConfig.id.in_(fallback_ids),
                ModelConfig.id != config.id,
                ModelConfig.enabled == True,
            )
        )
        by_id = {item.id: item for item in fallback_result.scalars().all()}
        selected["fallbacks"] = []
        seen_ids = set()
        for item_id in fallback_ids:
            if item_id in by_id and item_id not in seen_ids:
                selected["fallbacks"].append(serialize(by_id[item_id]))
                seen_ids.add(item_id)
    else:
        selected["fallbacks"] = []
    return selected


@router.get("/templates", response_model=List[PromptTemplateResponse])
async def get_prompt_templates(
    limit: int = Query(50, ge=1, le=200),
    q: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db),
):
    """获取可复用提示词模板。"""

    statement = select(PromptTemplate).order_by(PromptTemplate.updated_at.desc(), PromptTemplate.id.desc()).limit(limit)
    if q and q.strip():
        keyword = f"%{q.strip()}%"
        statement = statement.where(
            PromptTemplate.name.ilike(keyword) | PromptTemplate.description.ilike(keyword)
        )
    result = await db.execute(statement)
    return [_template_payload(item) for item in result.scalars().all()]


@router.post("/templates", response_model=PromptTemplateResponse)
async def create_prompt_template(
    payload: PromptTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建模板并写入初始版本。"""

    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="模板名称不能为空")
    variables = normalize_variables(payload.content, payload.variables)
    template = PromptTemplate(
        name=payload.name.strip(),
        description=payload.description,
        content=payload.content,
        variables=variables,
        tags=payload.tags or [],
        current_version=1,
    )
    db.add(template)
    await db.flush()
    db.add(PromptVersion(
        template_id=template.id,
        version=1,
        content=payload.content,
        variables=variables,
        change_note="初始版本",
    ))
    await db.commit()
    await db.refresh(template)
    return _template_payload(template)


@router.get("/templates/{template_id}", response_model=PromptTemplateResponse)
async def get_prompt_template(template_id: int, db: AsyncSession = Depends(get_db)):
    template = await _get_template(template_id, db)
    return _template_payload(template)


@router.put("/templates/{template_id}", response_model=PromptTemplateResponse)
async def update_prompt_template(
    template_id: int,
    payload: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新模板；正文变化时自动创建递增版本。"""

    template = await _get_template(template_id, db)
    changes = payload.model_dump(exclude_unset=True)
    new_content = changes.pop("content", None)
    if "name" in changes and changes["name"] is not None:
        changes["name"] = changes["name"].strip()
        if not changes["name"]:
            raise HTTPException(status_code=422, detail="模板名称不能为空")
    if new_content is not None and new_content != template.content:
        variables = normalize_variables(new_content, changes.get("variables", template.variables))
        next_version = int(template.current_version or 1) + 1
        db.add(PromptVersion(
            template_id=template.id,
            version=next_version,
            content=new_content,
            variables=variables,
            change_note="更新模板正文",
        ))
        template.content = new_content
        template.variables = variables
        template.current_version = next_version
    elif "variables" in changes:
        template.variables = normalize_variables(template.content, changes["variables"])
    for key, value in changes.items():
        if key != "variables":
            setattr(template, key, value)
    await db.commit()
    await db.refresh(template)
    return _template_payload(template)


@router.delete("/templates/{template_id}")
async def delete_prompt_template(template_id: int, db: AsyncSession = Depends(get_db)):
    template = await _get_template(template_id, db)
    # SQLite test/dev databases may not enable FK cascades.
    await db.execute(
        PromptVersion.__table__.delete().where(PromptVersion.template_id == template_id)
    )
    await db.delete(template)
    await db.commit()
    return {"message": "删除成功"}


@router.get("/templates/{template_id}/versions", response_model=List[PromptVersionResponse])
async def get_prompt_versions(template_id: int, db: AsyncSession = Depends(get_db)):
    await _get_template(template_id, db)
    result = await db.execute(
        select(PromptVersion)
        .where(PromptVersion.template_id == template_id)
        .order_by(PromptVersion.version.desc())
    )
    return [_version_payload(item) for item in result.scalars().all()]


@router.post("/templates/{template_id}/versions", response_model=PromptVersionResponse)
async def create_prompt_version(
    template_id: int,
    payload: PromptVersionCreate,
    db: AsyncSession = Depends(get_db),
):
    """从编辑器显式保存一个新版本。"""

    template = await _get_template(template_id, db)
    next_version = int(template.current_version or 1) + 1
    variables = normalize_variables(payload.content, payload.variables)
    version = PromptVersion(
        template_id=template.id,
        version=next_version,
        content=payload.content,
        variables=variables,
        change_note=payload.change_note,
    )
    db.add(version)
    template.content = payload.content
    template.variables = variables
    template.current_version = next_version
    await db.commit()
    await db.refresh(version)
    return _version_payload(version)


@router.get("/templates/{template_id}/versions/{version_number}", response_model=PromptVersionResponse)
async def get_prompt_version(template_id: int, version_number: int, db: AsyncSession = Depends(get_db)):
    await _get_template(template_id, db)
    return _version_payload(await _get_version(template_id, version_number, db))


@router.get("/templates/{template_id}/diff", response_model=PromptDiffResponse)
async def compare_prompt_versions(
    template_id: int,
    from_version: int = Query(..., ge=1),
    to_version: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    await _get_template(template_id, db)
    old = await _get_version(template_id, from_version, db)
    new = await _get_version(template_id, to_version, db)
    return {
        "from_version": from_version,
        "to_version": to_version,
        "diff": unified_prompt_diff(old.content, new.content),
    }


@router.post("/render", response_model=PromptRenderResponse)
async def render_prompt(payload: PromptRenderRequest):
    """预览模板变量替换结果。"""

    try:
        rendered, missing = render_prompt_template(payload.content, payload.values, strict=payload.strict)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "rendered": rendered,
        "variables": normalize_variables(payload.content),
        "missing": missing,
    }


@router.post("/test", response_model=PromptTestResponse)
async def test_prompt(payload: PromptTestRequest, db: AsyncSession = Depends(get_db)):
    """一键调用模型测试当前提示词，使用非流式响应便于编辑器预览。"""

    content = payload.prompt
    if not content and payload.template_id is not None:
        template = await _get_template(payload.template_id, db)
        content = template.content
        if payload.version is not None:
            content = (await _get_version(payload.template_id, payload.version, db)).content
    if not content:
        raise HTTPException(status_code=422, detail="请提供要测试的提示词")
    return await _run_prompt_test(content, payload.model_config_id, payload.variables, db)


async def _run_prompt_test(
    prompt_content: str,
    model_config_id: int,
    variables: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    try:
        prompt, _ = render_prompt_template(prompt_content, variables, strict=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    config = await _model_payload(model_config_id, db)
    service = LLMService(config)
    try:
        output = "".join([
            chunk async for chunk in service.chat(
                [{"role": "user", "content": prompt}], stream=False
            )
        ])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"模型测试失败: {exc}") from exc
    return {"output": output, "model_config_id": model_config_id}


@router.post("/templates/{template_id}/test", response_model=PromptTestResponse)
async def test_prompt_template(
    template_id: int,
    payload: PromptTestRequest,
    db: AsyncSession = Depends(get_db),
):
    """直接测试模板当前版本或指定历史版本。"""

    template = await _get_template(template_id, db)
    content = template.content
    if payload.version is not None:
        version = await _get_version(template_id, payload.version, db)
        content = version.content
    if payload.prompt:
        # 允许编辑器传入临时正文，同时仍保留 template_id 路由的语义。
        content = payload.prompt
    return await _run_prompt_test(content, payload.model_config_id, payload.variables, db)


@router.get("/records", response_model=List[PromptRecordResponse])
async def get_prompt_records(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """获取提示词历史"""
    result = await db.execute(
        select(PromptRecord).order_by(PromptRecord.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.delete("/records/{record_id}")
async def delete_prompt_record(record_id: int, db: AsyncSession = Depends(get_db)):
    """删除提示词记录"""
    result = await db.execute(select(PromptRecord).where(PromptRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="记录不存在")

    await db.delete(record)
    await db.commit()
    return {"message": "删除成功"}
