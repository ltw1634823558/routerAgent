from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用配置
    app_name: str = "RouterAgent"
    debug: bool = True

    # 数据库配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "root123"
    mysql_database: str = "router_agent"

    # LLM 默认配置（示例）
    default_llm_provider: str = "zhipu"
    default_llm_model: str = "glm-4"

    # 搜索引擎默认配置
    default_search_engine: str = "duckduckgo"

    @property
    def database_url(self) -> str:
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    @property
    def database_url_sync(self) -> str:
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
