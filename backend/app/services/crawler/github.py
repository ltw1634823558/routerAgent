"""GitHub repository README crawler."""

import asyncio
import base64
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

import httpx
from loguru import logger

from app.services.crawler.base import BaseCrawler


class GitHubCrawler(BaseCrawler):
    """Fetch and split a public GitHub repository README.

    ``repo`` accepts either ``owner/name`` or a regular GitHub repository URL.
    The crawler deliberately uses a bounded number of requests so a bad or
    rate-limited repository cannot keep an import job running indefinitely.
    """

    _README_NAMES = ("README.md", "readme.md", "README", "readme")

    @staticmethod
    def _normalise_repo(repo: str) -> Optional[Tuple[str, str]]:
        value = (repo or "").strip()
        if not value:
            return None
        if "://" in value:
            parsed = urlsplit(value)
            if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
                return None
            value = parsed.path
        else:
            # Also accept values copied with a leading github.com/.
            value = value.split("?", 1)[0].split("#", 1)[0]
            value = value.removeprefix("github.com/").removeprefix("www.github.com/")
        parts = [part for part in value.strip("/").split("/") if part]
        if len(parts) < 2:
            return None
        owner, name = parts[0], parts[1]
        if name.endswith(".git"):
            name = name[:-4]
        if not owner or not name or any(ch.isspace() for ch in (owner + name)):
            return None
        return owner, name

    @staticmethod
    def _split_readme(content: str) -> List[Tuple[str, str]]:
        """Split Markdown by ATX headings, retaining text before a heading."""

        sections: List[Tuple[str, str]] = []
        current_title: Optional[str] = None
        current_lines: List[str] = []
        heading = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
        for line in (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            match = heading.match(line)
            if match:
                if current_title is None and "\n".join(current_lines).strip():
                    sections.append(("README", "\n".join(current_lines).strip()))
                if current_title is not None:
                    sections.append((current_title, "\n".join(current_lines).strip()))
                current_title = match.group(1).rstrip("#").strip() or "README"
                current_lines = []
            else:
                current_lines.append(line)
        if current_title is not None:
            sections.append((current_title, "\n".join(current_lines).strip()))
        if not sections and (content or "").strip():
            sections.append(("README", content.strip()))
        elif sections and sections[0][0] != "README" and sections[0][1] == "":
            # Do not emit an empty preamble section.
            sections = sections
        return [(title, body) for title, body in sections if body]

    async def crawl(self, repo: str, max_files: int = 10) -> List[Dict[str, Any]]:
        parsed = self._normalise_repo(repo)
        if not parsed:
            logger.warning("无效的 GitHub 仓库地址: {}", repo)
            return []
        owner, name = parsed
        limit = max(1, int(max_files or 1))
        api_url = f"https://api.github.com/repos/{owner}/{name}"
        branch = "main"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={**self.headers, "Accept": "application/vnd.github+json"},
                follow_redirects=True,
            ) as client:
                # API is best-effort: unauthenticated API calls are commonly
                # rate-limited, so raw URL fallbacks must still work.
                try:
                    metadata = await client.get(api_url)
                    if metadata.status_code == 200:
                        payload = metadata.json()
                        branch = str(payload.get("default_branch") or branch)
                except Exception as exc:
                    logger.debug("GitHub 仓库信息请求失败，使用分支回退: {}", exc)

                response = None
                readme_url = ""
                # Probe at most three branches and four common README names.
                for candidate_branch in dict.fromkeys((branch, "main", "master")):
                    for filename in self._README_NAMES:
                        candidate_url = (
                            f"https://raw.githubusercontent.com/{owner}/{name}/"
                            f"{candidate_branch}/{filename}"
                        )
                        try:
                            candidate = await client.get(candidate_url)
                        except Exception as exc:
                            logger.debug("GitHub README 请求失败: {}", exc)
                            continue
                        if candidate.status_code == 200 and candidate.text.strip():
                            response = candidate
                            readme_url = candidate_url
                            break
                    if response is not None:
                        break
                if response is None:
                    # raw.githubusercontent.com 可能被网络策略拦截，使用
                    # GitHub README API 读取 base64 正文作为最后回退。
                    for candidate_branch in dict.fromkeys((branch, "main", "master")):
                        api_readme_url = f"{api_url}/readme?ref={candidate_branch}"
                        try:
                            candidate = await client.get(api_readme_url)
                            if candidate.status_code != 200:
                                continue
                            payload = candidate.json()
                            encoded = payload.get("content") if isinstance(payload, dict) else None
                            if not encoded:
                                continue
                            if str(payload.get("encoding", "")).lower() == "base64":
                                content = base64.b64decode("".join(str(encoded).split())).decode("utf-8", errors="replace")
                            else:
                                content = str(encoded)
                            if content.strip():
                                sections = self._split_readme(content)
                                readme_url = str(payload.get("html_url") or api_readme_url)
                                results = [
                                    {
                                        "title": f"{owner}/{name} - {title}",
                                        "content": body,
                                        "url": readme_url,
                                        "source": "github",
                                    }
                                    for title, body in sections
                                ]
                                await asyncio.sleep(0)
                                return results[:limit]
                        except Exception as exc:
                            logger.debug("GitHub README API 回退失败: {}", exc)
                    return []

                sections = self._split_readme(response.text)
                results = [
                    {
                        "title": f"{owner}/{name} - {title}",
                        "content": body,
                        "url": readme_url,
                        "source": "github",
                    }
                    for title, body in sections
                ]
                # Yield once so callers can schedule multiple import jobs
                # without monopolising the event loop.
                await asyncio.sleep(0)
                return results[:limit]
        except Exception as exc:
            logger.error("爬取 GitHub 失败: {}: {}", repo, exc)
            return []


# Keep the spelling exported by the original crawler API.
GithubCrawler = GitHubCrawler
