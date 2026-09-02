"""
问答 Agent - AI 岗位试题生成
"""
import json
import re
from textwrap import dedent
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.agents.base import BaseAgent


def _strip_code_fence(value: str) -> str:
    """去除答案外围 Markdown 代码围栏，保留代码本身。"""
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    # 保留围栏内容的首行缩进，后续由 dedent 统一移除包装层缩进。
    match = re.fullmatch(r"\s*```(?:[A-Za-z0-9_+.-]+)?[ \t]*\n?(.*?)[ \t]*\n?```\s*", text, flags=re.DOTALL)
    return match.group(1) if match else text.strip()


def _coerce_options(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                value = parsed
        except (TypeError, ValueError, json.JSONDecodeError):
            value = [line.strip() for line in text.splitlines() if line.strip()]
    if isinstance(value, (tuple, set)):
        value = list(value)
    if isinstance(value, list):
        return [str(item).strip() for item in value]
    return [str(value).strip()]


def _coerce_text(value: Any) -> str:
    """将题目和解析转换为文本，避免非字符串值写入 Text 字段。"""
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return "\n".join(_coerce_text(item) for item in value if item is not None).strip()
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _has_code_payload(value: Any) -> bool:
    """递归识别模型答案中的代码字段，用于缺少题型时的兜底判断。"""
    if isinstance(value, dict):
        if any(value.get(key) is not None for key in ("code", "code_answer", "reference_code", "solution_code")):
            return True
        return any(_has_code_payload(child) for child in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_code_payload(child) for child in value)
    return False


def _coerce_answer(value: Any, question_type: str) -> Any:
    """将 LLM 可能返回的对象答案转换为可持久化、可判题的值。"""
    # 不同模型可能返回 {solution: {code: ...}}，递归提取常见包装字段。
    while isinstance(value, dict):
        for key in ("code", "content", "solution", "answer", "value", "text"):
            if value.get(key) is not None:
                value = value[key]
                break
        else:
            value = json.dumps(value, ensure_ascii=False)
            break
    if question_type == "code":
        if isinstance(value, (list, tuple)):
            value = "\n".join(str(line) for line in value)
        return "\n".join(line.rstrip() for line in dedent(_strip_code_fence(str(value or ""))).strip().split("\n"))
    if isinstance(value, (tuple, set)):
        return list(value)
    return value


def normalize_question(raw: Dict[str, Any]) -> Dict[str, Any]:
    """统一不同模型输出的题目字段，供数据库和前端使用。"""
    item = dict(raw or {})
    raw_type = item.get("question_type", item.get("type", item.get("kind")))
    if raw_type is None:
        candidate_answer = item.get("answer")
        has_code_answer = _has_code_payload(item) or _has_code_payload(candidate_answer)
        raw_type = "code" if has_code_answer else "choice"
    raw_type = getattr(raw_type, "value", raw_type)
    type_text = str(raw_type or "choice").strip().lower().replace("-", "_").replace(" ", "_")
    type_aliases = {
        "single": "choice", "single_choice": "choice", "mcq": "choice", "select": "choice",
        "multiple": "multiple_choice", "multi_choice": "multiple_choice", "multiplechoice": "multiple_choice",
        "blank": "fill", "fill_blank": "fill", "short_answer": "fill",
        "coding": "code", "programming": "code", "python": "code", "python_code": "code", "python_class": "code", "python_function": "code",
        "class_code": "code", "code_snippet": "code",
        "编程": "code", "代码": "code", "代码题": "code", "多选": "multiple_choice", "单选": "choice",
    }
    question_type = type_aliases.get(type_text, type_text)
    if question_type not in {"choice", "multiple_choice", "fill", "code"}:
        question_type = "code" if any(token in type_text for token in ("code", "python", "编程", "代码")) else "choice"

    question = item.get("question") or item.get("text") or item.get("prompt") or item.get("title") or ""
    answer = item.get("answer")
    if answer is None:
        for key in ("correct_answer", "correct", "code_answer", "reference_answer", "solution", "reference_code", "solution_code"):
            if item.get(key) is not None:
                answer = item[key]
                break
    # 某些模型把参考代码放在 code 字段；仅代码题使用该回退，避免覆盖普通题的代码片段。
    if answer is None and question_type == "code":
        answer = item.get("code") or item.get("expected_output") or ""

    options = _coerce_options(item.get("options", item.get("choices")))
    if question_type in {"choice", "multiple_choice"} and options is None:
        options = []
    normalized = {
        "question": _coerce_text(question),
        "type": question_type,
        "question_type": question_type,
        "options": options,
        "answer": _coerce_answer(answer, question_type),
        "explanation": _coerce_text(item.get("explanation") or item.get("analysis") or item.get("explain")),
        "source": item.get("source") or item.get("source_url") or item.get("citation"),
    }
    for key in ("difficulty", "category"):
        if item.get(key) is not None:
            normalized[key] = item[key]
    return normalized


class QuizAgent(BaseAgent):
    """问答 Agent - AI 岗位试题生成"""

    SYSTEM_PROMPT = """你是一个专业的 AI 技术面试官。你的任务是根据知识库内容生成面试试题。

要求:
1. 试题必须基于真实的 AI 技术知识
2. 答案必须有实际出处,不能编造
3. 解析要清晰、准确
4. 代码题要给出完整可运行的代码，放在 answer 或 code_answer 字段中；不要执行用户代码

输出 JSON 格式:
{
  "questions": [
    {
      "question": "题目内容",
      "type": "choice|multiple_choice|fill|code",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "answer": "单选填一个答案，多选填答案数组，代码题填纯文本代码（可带 Markdown 围栏）",
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

    def parse_questions(self, response: str) -> Optional[List[Dict[str, Any]]]:
        """Parse documented object JSON and the legacy array shape."""
        if not response or not response.strip():
            return None

        text = response.strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
        candidates = [text]
        for match in (re.search(r"\[[\s\S]*\]", text), re.search(r"\{[\s\S]*\}", text)):
            if match and match.group() not in candidates:
                candidates.append(match.group())

        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if isinstance(data, list):
                return [item for item in (normalize_question(raw) for raw in data if isinstance(raw, dict)) if item.get("question")]
            if isinstance(data, dict):
                questions = data.get("questions", [])
                return [item for item in (normalize_question(raw) for raw in questions if isinstance(raw, dict)) if item.get("question")] if isinstance(questions, list) else []
        return None
