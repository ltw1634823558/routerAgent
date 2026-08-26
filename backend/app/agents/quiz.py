"""
问答 Agent - AI 岗位试题生成
"""
import json
import re
from typing import AsyncGenerator, Dict, Any, List
from app.agents.base import BaseAgent
class QuizAgent(BaseAgent):
    """问答 Agent - AI 岗位试题生成"""

    SYSTEM_PROMPT = """你是一个专业的 AI 技术面试官。你的任务是根据知识库内容生成面试试题。

要求:
1. 试题必须基于真实的 AI 技术知识
2. 答案必须有实际出处,不能编造
3. 解析要清晰、准确
4. 代码题要给出完整可运行的代码

输出 JSON 格式:
{
  "questions": [
    {
      "question": "题目内容",
      "type": "choice|multiple_choice|fill|code",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "answer": "单选填一个答案，多选填答案数组",
      "explanation": "解析",
      "source": "出处"
    }
  ]
}
 """

    async def run(
        self,
        category: str,
        difficulty: str,
        count: int,
        knowledge_context: str = "",
    ) -> AsyncGenerator[str, None]:
        """运行问答 Agent,生成试题"""
        prompt = f"""{self.SYSTEM_PROMPT}

技能分类: {category}
难度: {difficulty}
数量: {count}

知识库参考:
{knowledge_context[:3000] if knowledge_context else "无"}

请生成 {count} 面试题(JSON 格式)。选择题中请混合生成单选题和多选题；多选题必须使用 type="multiple_choice"，answer 必须是包含多个正确选项的数组。"""

        async for chunk in self.stream_response(prompt):
            yield chunk

    def parse_questions(self, response: str) -> List[Dict[str, Any]]:
        """解析生成的试题"""
        try:
            # 提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("questions", [])
        except Exception as e:
            return []
