"""官方文档爬虫"""
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from loguru import logger
from app.services.crawler.base import BaseCrawler


class OfficialCrawler(BaseCrawler):
    """官方文档爬虫"""

    PLATFORM_CONFIGS = {
        "zhipu": {
            "name": "智谱 AI",
            "base_url": "https://open.bigmodel.cn/dev",
            "paths": ["/api/paas/v4", "/api/paas/v4/chat/completions"],
        },
        "alibaba": {
            "name": "阿里云",
            "base_url": "https://help.aliyun.com",
            "paths": ["/zh/llm", "/zh/model-studio"],
        },
        "baidu": {
            "name": "百度千帆",
            "base_url": "https://cloud.baidu.com/doc",
            "paths": ["/WENXINWORKshop", "/WENXINWORKshop/Reference"],
        },
        "xunfei": {
            "name": "讯飞星火",
            "base_url": "https://www.xfyun.cn/doc",
            "paths": ["/spark-3.5", "/general/14.0.0"],
        },
        "tencent": {
            "name": "腾讯混元",
            "base_url": "https://cloud.tencent.com",
            "paths": ["/document/product/1697", "/api/xxx"],
        },
        "moonshot": {
            "name": "Moonshot Kimi",
            "base_url": "https://help.moonshot.cn",
            "paths": ["/docs", "/api-reference"],
        },
        "deepseek": {
            "name": "DeepSeek",
            "base_url": "https://platform.deepseek.com",
            "paths": ["/api-docs", "/zh"],
        },
        "minimax": {
            "name": "MiniMax",
            "base_url": "https://www.minimaxi.com",
            "paths": ["/document", "/api-reference"],
        },
    }

    async def crawl(self, platform: str, max_docs: int = 3) -> List[Dict[str, Any]]:
        """爬取官方文档"""
        config = self.PLATFORM_CONFIGS.get(platform)
        if not config:
            logger.warning(f"不支持的平台: {platform}")
            return []

        results = []
        base_url = config["base_url"]

        for path in config["paths"]:
            url = f"{base_url}{path}"

            try:
                docs = await self._crawl_docs(url, max_docs)
                results.extend(docs)
            except Exception as e:
                logger.error(f"爬取 {url} 失败: {e}")
                continue

            if len(results) >= max_docs:
                break

        await asyncio.sleep(0.5)
        return results[: max(1, max_docs)]

    async def _crawl_docs(self, url: str, max_docs: int) -> List[Dict[str, Any]]:
        """爬取文档页面"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # 提取标题
                title = ""
                h1 = soup.find("h1")
                if h1:
                    title = h1.text.strip()
                if not title:
                    title_tag = soup.find("title")
                    if title_tag:
                        title = title_tag.text.strip()

                # 提取内容
                content_sections = soup.find_all(["article", "section", "div"])
                content_parts = []

                for section in content_sections:
                    text = section.get_text().strip()
                    if text and len(text) > 100:
                        content_parts.append({
                            "title": f"{title} - 部分 {section.name}",
                            "content": text,
                            "url": url,
                            "source": "official",
                        })
                        if len(content_parts) >= max_docs:
                            break

                return content_parts
        except Exception as e:
            logger.error(f"解析文档失败 {url}: {e}")
            return []
