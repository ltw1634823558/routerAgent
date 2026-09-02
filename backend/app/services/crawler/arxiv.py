"""arXiv 论文爬虫"""
import asyncio
import httpx
from typing import List, Dict, Any
from loguru import logger
from app.services.crawler.base import BaseCrawler
import xml.etree.ElementTree as ET


import re


class ArxivCrawler(BaseCrawler):
    """arXiv 论文爬虫"""

    async def crawl(self, keyword: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """爬取 arXiv 论文"""
        base_url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{keyword}",
            "start": 0,
            "max_results": max_results
        }
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
                follow_redirects=True,
            ) as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                
                # 解析 XML
                root = ET.fromstring(response.content)
                entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                
                results = []
                for entry in entries:
                    try:
                        detail = await self._parse_entry(entry)
                        results.append(detail)
                    except Exception as e:
                        logger.error(f"解析 arXiv 论文失败: {e}")
                        continue
                    
                    await asyncio.sleep(1)
                    if len(results) >= max_results:
                        break
                return results
        except Exception as e:
            logger.error(f"爬取 arXiv 失败: {e}")
            return []
    
    async def _parse_entry(self, entry) -> Dict[str, Any]:
        """解析 arXiv 条目"""
        ns = "http://www.w3.org/2005/Atom"

        title = entry.find(f"{{{ns}}}title").text or ""
        summary = entry.find(f"{{{ns}}}summary").text or ""
        published = entry.find(f"{{{ns}}}published").text or ""
        link = entry.find(f"{{{ns}}}id").text or ""
        
        # 清理文本
        title = re.sub(r'\s+', ' ', title).strip()
        summary = re.sub(r'\s+', ' ', summary).strip()
        
        return {
            "title": title,
            "content": f"摘要: {summary}\n\n发布时间: {published}",
            "url": link,
            "source": "arxiv"
        }
