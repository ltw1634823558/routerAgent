"""Prompt IDE API and helper tests."""

import pytest
from httpx import AsyncClient

from app.services.prompt import extract_template_variables, render_prompt_template


@pytest.mark.unit
def test_prompt_template_helpers_render_and_detect_variables():
    content = "你好 {{ name }}，请使用 {{language}}。再次使用 {{ name }}。"
    assert extract_template_variables(content) == ["name", "language"]
    rendered, missing = render_prompt_template(content, {"name": "小明"}, strict=False)
    assert rendered == "你好 小明，请使用 {{language}}。再次使用 小明。"
    assert missing == ["language"]


@pytest.mark.api
@pytest.mark.asyncio
async def test_prompt_template_lifecycle(client: AsyncClient):
    response = await client.post(
        "/api/prompt/templates",
        json={"name": "代码助手", "content": "请用 {{language}} 编写 {{task}}", "tags": ["dev"]},
    )
    assert response.status_code == 200
    template = response.json()
    assert template["current_version"] == 1
    assert template["variables"] == ["language", "task"]

    versions = await client.get(f"/api/prompt/templates/{template['id']}/versions")
    assert versions.status_code == 200
    assert [item["version"] for item in versions.json()] == [1]

    updated = await client.put(
        f"/api/prompt/templates/{template['id']}",
        json={"content": "请用 {{language}} 编写高质量的 {{task}}", "name": "代码助手"},
    )
    assert updated.status_code == 200
    assert updated.json()["current_version"] == 2

    rendered = await client.post(
        "/api/prompt/render",
        json={"content": "你好 {{name}}", "values": {"name": "小明"}},
    )
    assert rendered.status_code == 200
    assert rendered.json()["rendered"] == "你好 小明"

    diff = await client.get(
        f"/api/prompt/templates/{template['id']}/diff",
        params={"from_version": 1, "to_version": 2},
    )
    assert diff.status_code == 200
    assert "高质量" in diff.json()["diff"]
