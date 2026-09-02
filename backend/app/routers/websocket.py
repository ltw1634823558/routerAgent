"""WebSocket 路由和处理器"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
import json
import os
import re
from textwrap import dedent
from loguru import logger
from datetime import datetime

from app.database import async_session_maker
from app.models.model_config import (
    ModelConfig, SearchRecord, PromptRecord,
    KnowledgeBase, QuizSession, QuizQuestion, QuizAttempt,
)
from app.models.prompt import PromptTemplate, PromptVersion
from app.agents import SearchAgent, PromptAgent, QuizAgent
from app.agents.quiz import normalize_question
from app.services.prompt import render_prompt_template


router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket 连接建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket 连接关闭, 当前连接数: {len(self.active_connections)}")

    async def send_json(self, data: dict, websocket: WebSocket):
        await websocket.send_json(data)


manager = ConnectionManager()


MULTIPLE_CHOICE_TYPES = {"multiple_choice", "multi_choice", "multiple"}


def _enum_value(value):
    """Return the wire value for either a legacy string or an Enum member."""

    return value.value if hasattr(value, "value") else value


def _choice_answer_index(answer, options):
    """将选择题答案统一解析为选项索引，无法解析时返回 None。"""
    if answer is None or not options:
        return None

    # 前端提交的选项索引可能是 int，也可能是字符串。
    if isinstance(answer, int) or (isinstance(answer, str) and answer.strip().isdigit()):
        index = int(answer)
        return index if 0 <= index < len(options) else None

    text = str(answer).strip()
    if len(text) == 1 and text.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        index = ord(text.upper()) - ord("A")
        return index if index < len(options) else None

    # 选择题文本答案（例如“解释型语言”）按选项内容匹配。
    for index, option in enumerate(options):
        if text.casefold() == str(option).strip().casefold():
            return index
    return None


_parse_choice_index = _choice_answer_index


def _choice_answer_indices(answer, options):
    """将单个或多个选择答案统一解析为排序后的选项索引。"""
    if answer is None or not options:
        return []
    if isinstance(answer, (list, tuple, set)):
        values = list(answer)
    elif isinstance(answer, str):
        text = answer.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            values = parsed if isinstance(parsed, list) else [parsed]
        except (TypeError, ValueError, json.JSONDecodeError):
            values = [part.strip() for part in text.replace("，", ",").split(",") if part.strip()]
    else:
        values = [answer]

    indices = []
    for value in values:
        index = _choice_answer_index(value, options)
        if index is not None and index not in indices:
            indices.append(index)
    return sorted(indices)


def _is_multiple_choice(question_type, answer):
    question_type = _enum_value(question_type)
    if question_type in MULTIPLE_CHOICE_TYPES or isinstance(answer, (list, tuple, set)):
        return True
    if isinstance(answer, str):
        text = answer.strip()
        if text.startswith("[") and text.endswith("]"):
            try:
                return isinstance(json.loads(text), list)
            except (TypeError, ValueError, json.JSONDecodeError):
                return False
    return False


def _serialize_question_answer(answer):
    """将多选答案转换为 TEXT 字段可保存的 JSON 字符串。"""
    if isinstance(answer, (list, tuple, set)):
        return json.dumps(list(answer), ensure_ascii=False)
    if isinstance(answer, dict):
        return json.dumps(answer, ensure_ascii=False)
    return "" if answer is None else str(answer)


def _normalize_code_text(value) -> str:
    """只做文本规范化，不执行用户提交的代码。"""
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    # 语言标记后的空格不能跨行，否则会误吃掉代码首行的缩进。
    match = re.fullmatch(r"```(?:[A-Za-z0-9_+.-]+)?[ \t]*\n?(.*?)[ \t]*\n?```", text, flags=re.DOTALL)
    if match:
        # 不要在 dedent 前 strip，首行缩进可能只是 Markdown 包装层。
        text = match.group(1)
    return "\n".join(line.rstrip() for line in dedent(text).expandtabs(4).split("\n")).strip()


def _normalize_text_answer(value) -> str:
    text = "" if value is None else str(value).strip()
    return re.sub(r"\s+", " ", text).casefold()


def _answers_match(question_type, user_answer, correct_answer) -> bool:
    """统一判题入口。代码题仅比较规范化文本，绝不执行代码。"""
    question_type = _enum_value(question_type)
    if question_type == "code":
        expected = _normalize_code_text(correct_answer)
        return bool(expected) and _normalize_code_text(user_answer) == expected
    expected = _normalize_text_answer(correct_answer)
    submitted = _normalize_text_answer(user_answer)
    return bool(expected) and bool(submitted) and submitted == expected


async def get_model_config(model_id: int) -> dict | None:
    """获取模型配置"""
    async with async_session_maker() as db:
        result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
        config = result.scalar_one_or_none()
        if not config or not getattr(config, "enabled", True):
            return None

        def serialize(item: ModelConfig) -> dict:
            provider = item.provider.value if hasattr(item.provider, "value") else item.provider
            return {
                "id": item.id,
                "name": item.name,
                "provider": provider,
                "model_name": item.model_name,
                "api_url": item.api_url,
                "api_key_env": item.api_key_env,
                "capabilities": item.capabilities or [],
            }

        selected = serialize(config)
        # 显式配置的备用模型优先；未配置时按优先级和创建时间自动选择其他启用模型。
        fallback_ids = [int(value) for value in (config.fallback_model_ids or []) if str(value).isdigit()]
        all_result = await db.execute(
            select(ModelConfig)
            .where(ModelConfig.id != model_id, ModelConfig.enabled == True)
            .order_by(ModelConfig.priority.asc(), ModelConfig.created_at.desc())
        )
        fallback_models = {item.id: item for item in all_result.scalars().all()}
        ordered = []
        seen_ids = set()
        for item_id in fallback_ids:
            if item_id in fallback_models and item_id not in seen_ids:
                ordered.append(fallback_models[item_id])
                seen_ids.add(item_id)
        for item_id, item in fallback_models.items():
            if item_id not in seen_ids:
                ordered.append(item)
                seen_ids.add(item_id)
        selected["fallbacks"] = [serialize(item) for item in ordered]
        return selected


@router.websocket("/ws/agent/{agent_type}")
async def websocket_endpoint(websocket: WebSocket, agent_type: str):
    """WebSocket 主入口"""
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # 路由到不同的 Agent
            if agent_type == "search":
                await handle_search_agent(websocket, message)
            elif agent_type == "prompt":
                await handle_prompt_agent(websocket, message)
            elif agent_type == "quiz":
                await handle_quiz_agent(websocket, message)
            else:
                await manager.send_json(
                    {"type": "error", "message": f"未知的 Agent 类型: {agent_type}"},
                    websocket,
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        try:
            await manager.send_json({"type": "error", "message": str(e)}, websocket)
        except Exception:
            pass
        manager.disconnect(websocket)


async def handle_search_agent(websocket: WebSocket, message: dict):
    """处理搜索 Agent"""
    try:
        query = message.get("query")
        engine = message.get("engine", "duckduckgo")
        api_key = message.get("api_key", "")
        model_id = message.get("model_id")
        deep_search = bool(message.get("deep_search", False))
        max_subqueries = message.get("max_subqueries")

        if not query:
            await manager.send_json({"type": "error", "message": "请输入搜索内容"}, websocket)
            return

        # 获取模型配置
        model_config = await get_model_config(model_id)
        if not model_config:
            await manager.send_json({"type": "error", "message": "模型配置不存在"}, websocket)
            return

        # 创建 Agent
        agent = SearchAgent(
            model_config,
            engine,
            api_key,
            deep_search=deep_search,
            max_subqueries=max_subqueries or 3,
        )

        full_result = ""
        async for chunk in agent.run(query):
            full_result += chunk
            await manager.send_json(
                {"type": "chunk", "content": chunk},
                websocket,
            )

        # 保存搜索记录
        async with async_session_maker() as db:
            record = SearchRecord(
                query=query,
                engine=engine,
                result=full_result,
                sources=agent.last_sources,
                model_config_id=model_id,
            )
            db.add(record)
            await db.commit()

        await manager.send_json({"type": "done", "record_id": record.id}, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"搜索 Agent 错误: {e}")
        try:
            await manager.send_json({"type": "error", "message": str(e)}, websocket)
        except Exception:
            pass
        manager.disconnect(websocket)


async def handle_prompt_agent(websocket: WebSocket, message: dict):
    """处理提示词优化 Agent"""
    try:
        user_input = message.get("user_input")
        original_user_input = user_input
        model_id = message.get("model_id")
        template_id = message.get("template_id")
        version_number = message.get("template_version")
        variables = message.get("variables") or {}

        if not user_input:
            await manager.send_json({"type": "error", "message": "请输入描述"}, websocket)
            return

        # Prompt IDE 可选地把模板渲染结果作为需求描述传给原有优化 Agent；
        # 未传模板的旧消息仍完全按原逻辑执行。
        if template_id is not None:
            async with async_session_maker() as db:
                template_result = await db.execute(
                    select(PromptTemplate).where(PromptTemplate.id == int(template_id))
                )
                template = template_result.scalar_one_or_none()
                if not template:
                    await manager.send_json({"type": "error", "message": "提示词模板不存在"}, websocket)
                    return
                template_content = template.content
                if version_number is not None:
                    version_result = await db.execute(
                        select(PromptVersion).where(
                            PromptVersion.template_id == template.id,
                            PromptVersion.version == int(version_number),
                        )
                    )
                    version = version_result.scalar_one_or_none()
                    if not version:
                        await manager.send_json({"type": "error", "message": "提示词版本不存在"}, websocket)
                        return
                    template_content = version.content
            try:
                rendered_input, _ = render_prompt_template(template_content, variables, strict=True)
            except ValueError as exc:
                await manager.send_json({"type": "error", "message": str(exc)}, websocket)
                return
            user_input = rendered_input

        # 获取模型配置
        model_config = await get_model_config(model_id)
        if not model_config:
            await manager.send_json({"type": "error", "message": "模型配置不存在"}, websocket)
            return

        # 创建 Agent
        agent = PromptAgent(model_config)
        full_result = ""
        async for chunk in agent.run(user_input):
            full_result += chunk
            await manager.send_json(
                {"type": "chunk", "content": chunk},
                websocket,
            )

        # 保存记录
        async with async_session_maker() as db:
            record = PromptRecord(
                user_input=original_user_input,
                generated_prompt=full_result,
                model_config_id=model_id,
            )
            db.add(record)
            await db.commit()

        # 发送完成信号
        await manager.send_json({"type": "done", "record_id": record.id}, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"提示词 Agent 错误: {e}")
        try:
            await manager.send_json({"type": "error", "message": str(e)}, websocket)
        except Exception:
            pass
        manager.disconnect(websocket)


async def handle_quiz_agent(websocket: WebSocket, message: dict):
    """处理问答 Agent"""
    action = message.get("action")

    if action == "generate":
        await generate_quiz(websocket, message)
    elif action == "submit":
        await submit_quiz(websocket, message)
    else:
        await manager.send_json({"type": "error", "message": "未知操作"}, websocket)


async def generate_quiz(websocket: WebSocket, message: dict):
    """生成试题"""
    try:
        category = message.get("category", "")
        difficulty = message.get("difficulty", "basic")
        count = message.get("count", 5)
        model_id = message.get("model_id")
        knowledge_context = message.get("knowledge_context", "")
        requested_knowledge_id = message.get("knowledge_id")

        if not model_id:
            await manager.send_json({"type": "error", "message": "请选择模型"}, websocket)
            return

        # 获取模型配置
        model_config = await get_model_config(model_id)
        if not model_config:
            await manager.send_json({"type": "error", "message": "模型配置不存在"}, websocket)
            return

        # 获取知识库上下文
        async with async_session_maker() as db:
            query = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
            if requested_knowledge_id is not None:
                try:
                    requested_knowledge_id = int(requested_knowledge_id)
                except (TypeError, ValueError):
                    await manager.send_json({"type": "error", "message": "知识库文档 ID 无效"}, websocket)
                    return
                query = query.where(KnowledgeBase.id == requested_knowledge_id)
            if category:
                query = query.where(KnowledgeBase.category == category)
            query = query.limit(3)
            result = await db.execute(query)
            knowledge_items = result.scalars().all()

        if requested_knowledge_id is not None and not knowledge_items:
            await manager.send_json({"type": "error", "message": "知识库文档不存在或分类不匹配"}, websocket)
            return

        context_parts = []
        for kb in knowledge_items:
            context_parts.append(f"标题: {kb.title}\n内容: {kb.content[:500]}")
        context_text = "\n\n".join(context_parts)

        if not knowledge_context:
            knowledge_context = context_text

        bound_knowledge = knowledge_items[0] if knowledge_items else None

        logger.info(f"知识库上下文: {len(knowledge_context)} 字符")

        # 创建 Agent 并生成试题
        agent = QuizAgent(model_config)
        full_response = ""
        async for chunk in agent.run(category, difficulty, count, knowledge_context):
            full_response += chunk
            await manager.send_json(
                {"type": "chunk", "content": chunk},
                websocket,
            )

        # 解析试题
        questions_data = agent.parse_questions(full_response)
        if not questions_data:
            await manager.send_json(
                {"type": "error", "message": "试题生成失败，请重试"},
                websocket,
            )
            return

        # 保存到数据库
        async with async_session_maker() as db:
            # 创建会话
            session = QuizSession(
                category=category,
                difficulty=difficulty,
                total_questions=len(questions_data),
            )
            db.add(session)
            await db.flush()

            # 保存试题
            saved_questions = []
            for q in questions_data:
                q = normalize_question(q)
                question_type = q.get("question_type", q.get("type", "choice"))
                question_answer = q.get("answer", "")
                if _is_multiple_choice(question_type, question_answer):
                    question_type = "multiple_choice"
                question_answer = _serialize_question_answer(question_answer)
                question = QuizQuestion(
                    knowledge_id=bound_knowledge.id if bound_knowledge else None,
                    question=q.get("question"),
                    question_type=question_type,
                    options=q.get("options") or None,
                    answer=question_answer,
                    explanation=q.get("explanation"),
                    difficulty=difficulty,
                    category=category,
                )
                db.add(question)
                await db.flush()
                saved_questions.append(question)

            await db.commit()

        # 返回会话ID和试题列表
        await manager.send_json({
            "type": "done",
            "session_id": session.id,
            "questions": [
                {
                    "id": q.id,
                    "question": q.question,
                    "question_type": _enum_value(q.question_type),
                    "options": q.options,
                    "difficulty": difficulty,
                    "category": category,
                    "knowledge_id": q.knowledge_id,
                    "source_title": bound_knowledge.title if bound_knowledge else None,
                    "source": bound_knowledge.source if bound_knowledge else None,
                }
                for q in saved_questions
            ],
        }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"生成试题错误: {e}")
        try:
            await manager.send_json({"type": "error", "message": str(e)}, websocket)
        except Exception:
            pass
        manager.disconnect(websocket)


async def submit_quiz(websocket: WebSocket, message: dict):
    """提交答案"""
    try:
        session_id = message.get("session_id")
        answers = message.get("answers", [])  # [{question_id, user_answer}, ...]

        if not session_id:
            await manager.send_json({"type": "error", "message": "会话不存在"}, websocket)
            return

        async with async_session_maker() as db:
            # 获取会话
            result = await db.execute(
                select(QuizSession).where(QuizSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if not session:
                await manager.send_json({"type": "error", "message": "会话不存在"}, websocket)
                return

            # 统计正确数
            correct_count = 0
            results = []

            for answer in answers:
                question_id = answer.get("question_id")
                user_answer = answer.get("user_answer")

                # 获取题目
                q_result = await db.execute(
                    select(QuizQuestion, KnowledgeBase)
                    .outerjoin(KnowledgeBase, KnowledgeBase.id == QuizQuestion.knowledge_id)
                    .where(QuizQuestion.id == question_id)
                )
                question_row = q_result.one_or_none()
                if not question_row:
                    continue
                question, knowledge = question_row
                question_type = _enum_value(question.question_type)

                # 判断是否正确 - 对于选择题，正确答案可能是索引或文本
                is_correct = False
                correct_answer_display = question.answer

                if question_type in {"choice", *MULTIPLE_CHOICE_TYPES} and question.options:
                    is_multiple = _is_multiple_choice(question_type, question.answer)
                    correct_idx = None
                    correct_indices = []
                    # 获取正确答案的选项文本
                    try:
                        if is_multiple:
                            correct_indices = _choice_answer_indices(question.answer, question.options)
                            correct_answer_display = [question.options[index] for index in correct_indices]
                        else:
                            correct_idx = _parse_choice_index(question.answer, question.options)
                            correct_answer_display = question.options[correct_idx] if correct_idx is not None else question.answer
                    except (ValueError, TypeError):
                        # answer 本身就是文本
                        correct_answer_display = question.answer

                    # 比较用户答案和正确答案（支持索引或文本）
                    submitted_answer = answer.get("user_answer_index", user_answer)
                    if is_multiple:
                        user_indices = _choice_answer_indices(submitted_answer, question.options)
                        is_correct = bool(correct_indices) and user_indices == correct_indices
                    else:
                        user_idx = _parse_choice_index(submitted_answer, question.options)
                        is_correct = (
                            correct_idx is not None and user_idx is not None
                            and correct_idx == user_idx
                        )
                        if not is_correct:
                            # 也尝试用原始索引比较
                            expected_text = str(question.answer or "").strip().casefold()
                            submitted_text = str(user_answer or "").strip().casefold()
                            is_correct = bool(expected_text and submitted_text) and submitted_text == expected_text
                else:
                    # 非选择题直接比较
                    if question_type == "code":
                        correct_answer_display = _normalize_code_text(question.answer)
                    is_correct = _answers_match(question_type, user_answer, question.answer)

                if is_correct:
                    correct_count += 1

                # 保存答题记录
                stored_user_answer = user_answer
                if isinstance(user_answer, (list, tuple, set)):
                    stored_user_answer = ", ".join(str(item) for item in user_answer)
                attempt = QuizAttempt(
                    session_id=session_id,
                    question_id=question_id,
                    user_answer=stored_user_answer,
                    is_correct=is_correct,
                )
                db.add(attempt)

                results.append({
                    "question_id": question_id,
                    "question": question.question,
                    "question_type": question_type,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer_display,
                    "explanation": question.explanation,
                    "is_correct": is_correct,
                    "knowledge_id": question.knowledge_id,
                    "source_title": knowledge.title if knowledge else None,
                    "source": knowledge.source if knowledge else None,
                })

            # 更新会话
            session.correct_count = correct_count
            valid_answer_count = len(results)
            session.score = round((correct_count / valid_answer_count) * 100, 2) if valid_answer_count else 0
            session.finished_at = datetime.now()

            await db.commit()

            # 发送结果
            await manager.send_json(
                {
                    "type": "result",
                    "score": float(session.score or 0),
                    "correct_count": correct_count,
                    "total": valid_answer_count,
                    "results": results,
                },
                websocket,
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"提交答案错误: {e}")
        try:
            await manager.send_json({"type": "error", "message": str(e)}, websocket)
        except Exception:
            pass
        manager.disconnect(websocket)
