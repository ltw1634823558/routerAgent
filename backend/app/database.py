from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
from loguru import logger

from app.config import settings


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db():
    """初始化数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # 旧版 MySQL 初始化脚本只允许单选题；为已有数据库补充多选题类型。
        if conn.dialect.name == "mysql":
            result = await conn.execute(text("""
                SELECT COLUMN_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'quiz_questions'
                  AND COLUMN_NAME = 'question_type'
            """))
            column_type = result.scalar_one_or_none() or ""
            if "multiple_choice" not in column_type:
                await conn.execute(text("""
                    ALTER TABLE quiz_questions
                    MODIFY COLUMN question_type
                    ENUM('choice', 'multiple_choice', 'fill', 'code')
                    NOT NULL COMMENT '题型'
                """))
        logger.info("数据库表创建/检查完成")


async def get_db():
    """获取数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
