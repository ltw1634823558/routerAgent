"""
知识库爬虫服务
"""
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger


from abc import ABC, abstractmethod


class BaseCrawler(ABC):
    """知识库爬虫基类"""

    def __init__(self):
        self.timeout = 30.0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36"
        }

    
    @abstractmethod
    async def crawl(self, **kwargs) -> List[Dict[str, Any]]:
        """执行爬取"""
        pass

