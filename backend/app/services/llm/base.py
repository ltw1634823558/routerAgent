"""
LLM 服务 - 统一的 LLM 调用接口
"""
import os
import httpx
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from loguru import logger


class LLMService:
    """LLM 服务基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = os.getenv(config.get("api_key_env", ""), "")
        self.provider = config.get("provider", "")
        self.model_name = config.get("model_name", "")
        self.api_url = config.get("api_url", "")

    async def chat(
        self,
        messages: list,
        stream: bool = True,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """调用聊天接口"""
        if self.provider == "zhipu":
            async for chunk in self._chat_zhipu(messages, stream, **kwargs):
                yield chunk
        elif self.provider == "deepseek":
            async for chunk in self._chat_openai_compatible(messages, stream, **kwargs):
                yield chunk
        elif self.provider == "moonshot":
            async for chunk in self._chat_openai_compatible(messages, stream, **kwargs):
                yield chunk
        elif self.provider == "alibaba":
            async for chunk in self._chat_dashscope(messages, stream, **kwargs):
                yield chunk
        else:
            # 默认 OpenAI 兼容格式
            async for chunk in self._chat_openai_compatible(messages, stream, **kwargs):
                yield chunk

    async def _chat_openai_compatible(
        self,
        messages: list,
        stream: bool,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """OpenAI 兼容格式调用"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        url = self.api_url.rstrip("/")
        endpoint = f"{url}/chat/completions"

        logger.debug(f"调用 LLM: {endpoint}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            if stream:
                async with client.stream(
                    "POST",
                    endpoint,
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = line[6:]  # 去掉 "data: "
                                if data.strip():
                                    import json
                                    chunk_data = json.loads(data)
                                    if chunk_data.get("choices"):
                                        delta = chunk_data["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield content
                            except Exception as e:
                                logger.error(f"解析流式数据失败: {e}")
            else:
                response = await client.post(endpoint, headers=headers, json={**payload, "stream": False})
                response.raise_for_status()
                data = response.json()
                if data.get("choices"):
                    yield data["choices"][0]["message"]["content"]

    async def _chat_zhipu(
        self,
        messages: list,
        stream: bool,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """智谱 AI 调用"""
        try:
            from zhipuai import ZhipuAI

            client = ZhipuAI(api_key=self.api_key)

            if stream:
                response = client.chat.completions.create(
                    model=self.model_name or "glm-4",
                    messages=messages,
                    stream=True,
                    temperature=kwargs.get("temperature", 0.7),
                    max_tokens=kwargs.get("max_tokens", 4096),
                )
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                response = client.chat.completions.create(
                    model=self.model_name or "glm-4",
                    messages=messages,
                    stream=False,
                    temperature=kwargs.get("temperature", 0.7),
                    max_tokens=kwargs.get("max_tokens", 4096),
                )
                if response.choices:
                    yield response.choices[0].message.content
        except ImportError:
            logger.warning("zhipuai 未安装，使用 OpenAI 兼容模式")
            # 使用 OpenAI 兼容模式
            self.api_url = "https://open.bigmodel.cn/api/paas/v4"
            async for chunk in self._chat_openai_compatible(messages, stream, **kwargs):
                yield chunk

    async def _chat_dashscope(
        self,
        messages: list,
        stream: bool,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """阿里云通义千问调用"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 转换消息格式
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        payload = {
            "model": self.model_name or "qwen-turbo",
            "input": {"messages": formatted_messages},
            "parameters": {
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 4096),
            },
        }

        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

        async with httpx.AsyncClient(timeout=120.0) as client:
            if stream:
                payload["parameters"]["incremental_output"] = True
                async with client.stream(
                    "POST",
                    url,
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                import json
                                data = json.loads(line)
                                output = data.get("output", {})
                                text = output.get("text", "")
                                if text:
                                    yield text
                            except Exception as e:
                                logger.error(f"解析流式数据失败: {e}")
            else:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                output = data.get("output", {})
                yield output.get("text", "")
