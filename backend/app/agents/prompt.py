"""
提示词优化 Agent
"""
from typing import AsyncGenerator, Dict, Any
from app.agents.base import BaseAgent


class PromptAgent(BaseAgent):
    """提示词优化 Agent"""

    SYSTEM_PROMPT = """你是一个专业的提示词工程师。你的任务是根据用户的描述,生成高质量的系统提示词。

要求:
1. 理解用户想要完成的任务
2. 生成清晰、结构化的提示词
3. 包含角色定义、任务描述、输出格式等
4. 使用 Markdown 格式
5. 生成的提示词应该可以直接复制使用或导出

请生成提示词: """

    async def run(self, user_input: str) -> AsyncGenerator[str, None]:
        """运行提示词优化 Agent"""
        prompt = f"""{self.SYSTEM_PROMPT}

用户描述: {user_input}

请生成优化的系统提示词: """

        async for chunk in self.stream_response(prompt):
            yield chunk
