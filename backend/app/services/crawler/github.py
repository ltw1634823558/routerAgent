"""GitHub 爬虫"""
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from loguru import logger
from app.services.crawler.base import BaseCrawler


class GitHubCrawler(BaseCrawler):
    """GitHub 项目/教程爬虫"""

    async def crawl(self, repo: str, max_files: int = 10) -> List[Dict[str, Any]]:
        """爬取 GitHub 仓库文档"""
        readme_url = f"https://raw.githubusercontent.com/{repo}/main/README.md"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(readme_url)

                if response.status_code != 200:
                    # 尝试其他常见文件名
                    for filename in ["README.md", "readme.md", "README", "readme"]:
                        alt_url = f"https://raw.githubusercontent.com/{repo}/main/{filename}"
                        response = await client.get(alt_url)
                        if response.status_code == 200:
                            break
                    else:
                        return []

                content = response.text

                results = []

                # 解析 README 按标题分段
                sections = []
                current_section = None
                current_content = []

                for line in content.split('\n'):
                    if line.startswith('#'):
                        if current_section:
                            sections.append({
                                "title": current_section,
                                "content": '\n'.join(current_content)
                            })
                        current_section = line.strip('# ')
                        current_content = []
                    else:
                        current_content.append(line)

                # 添加最后一个部分
                if current_section:
                    sections.append({
                        "title": current_section,
                        "content": '\n'.join(current_content)
                    })

                for section in sections:
                    results.append({
                        "title": f"{repo} - {section['title']}",
                        "content": section["content"],
                        "url": readme_url,
                        "source": "github"
                    })

                await asyncio.sleep(0.5)
                return results
        except Exception as e:
            logger.error(f"爬取 GitHub 失败: {repo}: {e}")
            return []
