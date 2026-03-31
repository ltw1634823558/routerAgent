from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.database import init_db
from app.routers import model, search, prompt, quiz, knowledge
from app.routers.websocket import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 RouterAgent 启动中...")
    await init_db()
    logger.info("✅ 数据库初始化完成")
    yield
    logger.info("👋 RouterAgent 关闭中...")


app = FastAPI(
    title="RouterAgent API",
    description="自定义 Agent 平台后端服务",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 REST API 路由
app.include_router(model.router, prefix="/api/models", tags=["模型配置"])
app.include_router(search.router, prefix="/api/search", tags=["搜索Agent"])
app.include_router(prompt.router, prefix="/api/prompt", tags=["提示词Agent"])
app.include_router(quiz.router, prefix="/api/quiz", tags=["问答Agent"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])

# 注册 WebSocket 路由
app.include_router(ws_router, tags=["WebSocket"])


@app.get("/")
async def root():
    return {"message": "RouterAgent API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
