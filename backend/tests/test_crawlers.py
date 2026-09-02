import base64
from types import SimpleNamespace

import httpx
import pytest

from app.services.crawler.csdn import CSDNCrawler
from app.services.crawler.github import GitHubCrawler


class _FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.get(url)
        if response is None:
            return SimpleNamespace(status_code=404, text="", json=lambda: {})
        return response


@pytest.mark.asyncio
async def test_github_crawler_accepts_url_and_default_branch(monkeypatch):
    api = "https://api.github.com/repos/acme/demo"
    raw = "https://raw.githubusercontent.com/acme/demo/master/README.md"
    fake = _FakeClient(
        {
            api: SimpleNamespace(status_code=200, text="", json=lambda: {"default_branch": "master"}),
            raw: SimpleNamespace(status_code=200, text="Intro without heading\n\n## Usage\nrun it"),
        }
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: fake)

    result = await GitHubCrawler().crawl("https://github.com/acme/demo.git", max_files=5)

    assert [item["title"] for item in result] == ["acme/demo - README", "acme/demo - Usage"]
    assert result[0]["url"] == raw
    assert any(call[0] == api for call in fake.calls)


@pytest.mark.asyncio
async def test_github_crawler_falls_back_to_readme_api(monkeypatch):
    api = "https://api.github.com/repos/acme/demo"
    readme_api = f"{api}/readme?ref=main"
    encoded = base64.b64encode(b"# API README\n\ncontent").decode()
    fake = _FakeClient(
        {
            api: SimpleNamespace(status_code=200, text="", json=lambda: {"default_branch": "main"}),
            readme_api: SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"encoding": "base64", "content": encoded, "html_url": "https://github.com/acme/demo/blob/main/README.md"},
            ),
        }
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: fake)

    result = await GitHubCrawler().crawl("acme/demo", max_files=1)

    assert len(result) == 1
    assert result[0]["title"] == "acme/demo - API README"
    assert result[0]["content"] == "content"
    assert result[0]["url"].startswith("https://github.com/")


@pytest.mark.asyncio
async def test_csdn_crawler_fetches_detail_when_api_has_no_content(monkeypatch):
    api = CSDNCrawler.SEARCH_URL
    article_url = "https://blog.csdn.net/user/article/details/1"
    fake = _FakeClient(
        {
            api: SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"result": {"list": [{"title": "教程", "url": article_url}]}},
            ),
            article_url: SimpleNamespace(
                status_code=200,
                text="<html><h1>教程正文</h1><div id='content_views'><p>代码内容</p></div></html>",
            ),
        }
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: fake)

    result = await CSDNCrawler().crawl("python", max_pages=1)

    assert len(result) == 1
    assert result[0]["title"] == "教程正文"
    assert "代码内容" in result[0]["content"]


@pytest.mark.asyncio
async def test_csdn_crawler_accepts_article_url(monkeypatch):
    article_url = "https://blog.csdn.net/user/article/details/2"
    fake = _FakeClient(
        {
            article_url: SimpleNamespace(
                status_code=200,
                text="<html><h1>单页文章</h1><main>正文内容</main></html>",
            )
        }
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: fake)

    result = await CSDNCrawler().crawl(article_url, max_pages=1)

    assert len(result) == 1
    assert result[0]["url"] == article_url
    assert "正文内容" in result[0]["content"]
