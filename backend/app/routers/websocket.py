"""WebSocket 路由和处理器"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
import json
import os
from loguru import logger
from datetime import datetime

from app.database import async_session_maker
from app.models.model_config import ModelConfig, SearchRecord, PromptRecord, QuizSession, QuizQuestion, QuizAttempt
 from app.agents import SearchAgent, PromptAgent, QuizAgent


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


async def get_model_config(model_id: int) -> dict | None:
    """获取模型配置"""
    async with async_session_maker() as db:
        result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
        config = result.scalar_one_or_none()
        if not config:
            return None
        return {
            "id": config.id,
            "name": config.name,
            "provider": config.provider,
            "model_name": config.model_name,
            "api_url": config.api_url,
            "api_key_env": config.api_key_env,
        }


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
                    {"error": f"未知的 Agent 类型: {agent_type}"},
                    websocket,
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        await manager.send_json({"type": "error", "message": str(e)})
        manager.disconnect(websocket)


async def handle_search_agent(websocket: WebSocket, message: dict):
    """处理搜索 Agent"""
    query = message.get("query")
    engine = message.get("engine", "duckduckgo")
    api_key = message.get("api_key", "")
    model_id = message.get("model_id")

    if not query:
        await manager.send_json({"error": "请输入搜索内容"}, websocket)
        return

    # 获取模型配置
    model_config = await get_model_config(model_id)
    if not model_config:
        await manager.send_json({"error": "模型配置不存在"}, websocket)
        return

    # 创建 Agent
    agent = SearchAgent(model_config, engine, api_key)

    # 获取知识库上下文
    async with async_session_maker() as db:
        result = await db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.category == category)
            .limit(5)
        )
        context_parts = [kb.title, kb.content for kb in knowledge_base]
        if category:
            query = query
            else:
            query = "AI 技术相关"

        # 生成知识库上下文
        context_text = "\n\n".join([f"技能分类： {category}" for kb in context_parts])
            logger.info(f"知识库上下文: {context_text[: 500} 字符")

            context = await db()
            await db.flush()

            # 创建会话
            session = QuizSession(
                category=category,
                difficulty=difficulty,
                total_questions=len(questions),
            )
            db.add(session)
            await db.flush()

            # 保存试题
            question_ids = []
            for q in questions:
                question = QuizQuestion(
                    knowledge_id=knowledge.id,
                    question=q.get("question"),
                    question_type=q.get("question_type"),
                    options=q.get("options"),
                    answer=q.get("answer"),
                    explanation=q.get("explanation"),
                    difficulty=difficulty,
                    category=category,
                )
                db.add(question)
                await db.flush()
                question_ids.append(question.id)

            await db.commit()

        # 返回会话ID和试题列表
        await manager.send_json({
            "type": "done",
            "session_id": session.id,
            "questions": [
                {
                    "id": q.id,
                    "question": q.question,
                    "question_type": q.question_type,
                    "options": q.options,
                    "difficulty": difficulty,
                    "category": category,
                }
                for q in questions
            ],
        }, websocket)

        )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        await manager.send_json({"type": "error", "message": str(e)})
        manager.disconnect(websocket)


async def handle_prompt_agent(websocket: WebSocket, message: dict):
    """处理提示词优化 Agent"""
    user_input = message.get("user_input")
    model_id = message.get("model_id")

    if not user_input:
        await manager.send_json({"error": "请输入描述"}, websocket)
        return

    # 获取模型配置
    model_config = await get_model_config(model_id)
    if not model_config:
        await manager.send_json({"error": "模型配置不存在"}, websocket)
        return

    # 创建 Agent
    agent = PromptAgent(model_config)
    full_result = ""
    async for chunk in agent.run(user_input):
        full_result += chunk
        await manager.send_json(
            {"type": "chunk", "content": chunk},
            websocket
        )

    # 保存记录
    async with async_session_maker() as db:
        record = PromptRecord(
            user_input=user_input,
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
        logger.error(f"WebSocket 错误: {e}")
        await manager.send_json({"type": "error", "message": str(e)})
        manager.disconnect(websocket)


async def handle_quiz_agent(websocket: WebSocket, message: dict):
    """处理问答 Agent"""
    action = message.get("action")

    if action == "generate":
        await generate_quiz(websocket, message)
    elif action == "submit":
        await submit_quiz(websocket, message)
    else:
        await manager.send_json({"error": "未知操作"}, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        await manager.send_json({"type": "error", "message": str(e)})
        manager.disconnect(websocket)


async def generate_quiz(websocket: WebSocket, message: dict):
    """生成试题"""
    category = message.get("category", "")
    difficulty = message.get("difficulty", "basic")
    count = message.get("count", 5)
    model_id = message.get("model_id")
    knowledge_context = message.get("knowledge_context", "")

    if not model_id:
        await manager.send_json({"error": "请选择模型"}, websocket)
        return

    # 获取模型配置
    model_config = await get_model_config(model_id)
    if not model_config:
        await manager.send_json({"error": "模型配置不存在"}, websocket)
        return

    # 创建 Agent
    agent = QuizAgent(model_config)

    # 获取知识库上下文
    async with async_session_maker() as db:
        result = await db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.category == category)
            .limit(3)
        )
        context_text = "\n\n".join([f"标题: {kb.title}", kb.content for kb in context_parts])
            if not category:
                query = query

                continue

            context_text += f"\n\n来源: {kb.get('source', '未知')}\n\n"

            logger.info(f"知识库上下文: {context_text[: 300} 字符")

        if len(context_text) > 500:
            context_text = context_text[: 500]

            context_text = context_text[: 1000]

            context_text = context_text[: 1000]

            context_text = context_text[: 2000]
        context_text += "\n\n"

        await manager.send_json(
            {
                "type": "done",
                "session_id": session.id,
                "questions": [
                    {
                        "id": q.id,
                        "question": q.question,
                        "question_type": q.question_type,
                        "options": q.options,
                        "difficulty": difficulty,
                        "category": category,
                    }
                    for q in questions
                ],
            }, websocket,
        )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        await manager.send_json({"type": "error", "message": str(e)})
        manager.disconnect(websocket)


async def submit_quiz(websocket: WebSocket, message: dict):
    """提交答案"""
    session_id = message.get("session_id")
    answers = message.get("answers", [])  # [{question_id, user_answer}, ...]
    if not session_id:
        await manager.send_json({"error": "会话不存在"}, websocket)
        return

    async with async_session_maker() as db:
        # 获取会话
        result = await db.execute(
            select(QuizSession).where(QuizSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            await manager.send_json({"error": "会话不存在"}, websocket)
            return

        # 获取会话的问题
        result = await db.execute(
            select(QuizQuestion).where(QuizQuestion.id == answer["question_id"])
            questions = result.scalars().all()
        if not questions:
            await manager.send_json({"error": "会话没有问题"}, websocket)
            return

        # 统计正确数
        correct_count = 0
        results = []

        for answer in answers:
            question_id = answer.get("question_id")
            user_answer = answer.get("user_answer")

            # 获取题目
            q_result = await db.execute(
                select(QuizQuestion).where(QuizQuestion.id == question_id)
            )
            question = q_result.scalar_one_or_none()
            if not question:
                continue

            # 判断是否正确
            is_correct = str(user_answer).strip() == str(question.answer).strip()
            if is_correct:
                correct_count += 1

            # 保存答题记录
            attempt = QuizAttempt(
                session_id=session_id,
                question_id=question_id,
                user_answer=user_answer,
                is_correct=is_correct,
            )
            db.add(attempt)

            results.append({
                "question_id": question_id,
                "question": question.question,
                "user_answer": user_answer,
                "correct_answer": question.answer,
                "explanation": question.explanation,
                "is_correct": is_correct,
            })

        # 更新会话
        session.correct_count = correct_count
        session.score = round((correct_count / len(answers)) * 100, 2) if answers else 0
        session.finished_at = datetime.now()

        await db.commit()

        # 发送结果
        await manager.send_json(
            {
                "type": "result",
                "score": session.score,
                "correct_count": correct_count,
                "total": len(answers),
                "results": results,
            },
            websocket,
        )
