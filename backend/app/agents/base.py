"""
Agent 娡块 - 基类
"""
import os
import httpx
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any
from loguru import logger


from app.services.llm import LLMService


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(self, model_config: Dict[str, Any]):
        self.model_config = model_config
        self.llm = LLMService(model_config)

    @abstractmethod
    async def run(self, *args, **kwargs) -> AsyncGenerator[str, None]:
        """运行 Agent"""
        pass

    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """流式响应"""
        async for chunk in self.llm.chat([{"role": "user", "content": prompt}], stream=True):
            yield chunk
