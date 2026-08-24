"""CSDN 爬虫"""
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from loguru import logger
from app.services.crawler.base import BaseCrawler


import re


class CSDNCrawler(BaseCrawler):
    """CSDN 技术博客爬虫"""

    async def crawl(self, keyword: str, max_pages: int = 3) -> List[Dict[str, Any]]:
        """爬取 CSDN 技术博客"""
        url = "https://so.csdn.net/api/v1/article/getlistArticleListByKeyword"
        params = {
            "keyword": keyword,
            "page": 1,
            "pageSize": max_pages
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            articles = data.get("data", {}).get("list", [])
            results = []
            
            for article in articles:
                try:
                    detail = await self._parse_article(article)
                    results.append(detail)
                except Exception as e:
                    logger.error(f"解析 CSDN 文章失败: {article.get('articleTitle', e)}")
                
                await asyncio.sleep(1)  # 避免请求过快

                if len(results) >= max_pages * 3:
                    break

            return results

        except Exception as e:
            logger.error(f"爬取 CSDN 失败: {e}")
            return results

    async def _parse_article(self, article: dict) -> Dict[str, Any]:
        """解析 CSDN 文章"""
        soup = BeautifulSoup(article.get("articleContent", ""), "html.parser")
        
        # 提取标题
        title_tag = soup.find("h1")
        title = title_tag.get_text().strip() if title_tag else article.get("articleTitle", "")
        
        # 提取正文内容
        content_divs = soup.find_all("div", {"id": re.compile(r"article_content_\w+")})
        content_parts = []
        
        for div in content_divs:
            text = div.get_text().strip()
            # 过滤广告和无关内容
            if text and len(text) > 100 and not any(
                kw.lower() in text.lower()
                for kw in ["推荐", "关注", "点赞", "评论", "收藏", "分享"]
            ):
                content_parts.append(text)
        
        return {
            "title": title,
            "content": "\n\n".join(content_parts),
            "url": article.get("articleUrl", ""),
            "source": "csdn",
        }
