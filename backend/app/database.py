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
            # 为已有安装补齐模型中心字段。CREATE TABLE 不会更新已经存在的表，
            # 因此这里按列检查，保证升级后旧数据仍能读取。
            result = await conn.execute(text("""
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'model_configs'
            """))
            existing_model_columns = {row[0] for row in result.fetchall()}
            model_column_definitions = {
                "capabilities": "JSON NULL",
                "priority": "INT NOT NULL DEFAULT 100",
                "enabled": "TINYINT(1) NOT NULL DEFAULT 1",
                "fallback_model_ids": "JSON NULL",
            }
            for column_name, definition in model_column_definitions.items():
                if column_name not in existing_model_columns:
                    await conn.execute(text(f"ALTER TABLE model_configs ADD COLUMN {column_name} {definition}"))
            await conn.execute(text(
                "UPDATE model_configs SET capabilities = JSON_ARRAY() WHERE capabilities IS NULL"
            ))
            await conn.execute(text(
                "UPDATE model_configs SET fallback_model_ids = JSON_ARRAY() WHERE fallback_model_ids IS NULL"
            ))

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

            # URL 导入是知识库流水线的合法来源；旧库的 ENUM 需要显式升级。
            result = await conn.execute(text("""
                SELECT COLUMN_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'knowledge_base'
                  AND COLUMN_NAME = 'source_type'
            """))
            source_column_type = result.scalar_one_or_none() or ""
            if source_column_type and "'url'" not in source_column_type.lower():
                await conn.execute(text("""
                    ALTER TABLE knowledge_base
                    MODIFY COLUMN source_type
                    ENUM('official', 'csdn', 'arxiv', 'github', 'url', 'manual')
                    NULL COMMENT '来源类型'
                """))
        logger.info("数据库表创建/检查完成")


async def get_db():
    """获取数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
