import re

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.model_config import ProviderEnum


API_KEY_ENV_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*_API_KEY$")


def validate_api_key_env_name(value: str) -> str:
    value = value.strip()
    if not API_KEY_ENV_NAME_PATTERN.fullmatch(value):
        raise ValueError("API Key 环境变量名必须为大写字母、数字和下划线，且以 _API_KEY 结尾")
    return value


class SchemaBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


# ============ 模型配置 ============
class ModelConfigCreate(SchemaBase):
    name: str = Field(..., description="配置名称")
    provider: str = Field(..., description="提供商")
    model_name: str = Field(..., description="模型名称")
    api_url: Optional[str] = Field(None, description="API 地址")
    api_key_env: str = Field(..., description="API KEY 环境变量名")
    is_default: bool = Field(False, description="是否默认")

    @field_validator("api_key_env")
    @classmethod
    def validate_api_key_env(cls, value: str) -> str:
        return validate_api_key_env_name(value)


class ModelConfigUpdate(SchemaBase):
    name: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_url: Optional[str] = None
    api_key_env: Optional[str] = None
    is_default: Optional[bool] = None

    @field_validator("api_key_env")
    @classmethod
    def validate_api_key_env(cls, value: Optional[str]) -> Optional[str]:
        return validate_api_key_env_name(value) if value is not None else value


class ModelConfigResponse(SchemaBase):
    id: int
    name: str
    provider: str
    model_name: str
    api_url: Optional[str]
    api_key_env: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 搜索记录 ============
class SearchRequest(SchemaBase):
    query: str = Field(..., description="搜索内容")
    engine: str = Field(..., description="搜索引擎")
    api_key: str = Field(..., description="搜索引擎 API KEY")


class SearchResult(SchemaBase):
    result: str
    sources: List[Dict[str, str]]


class SearchRecordResponse(SchemaBase):
    id: int
    query: str
    engine: str
    result: Optional[str]
    sources: Optional[List[Dict[str, str]]]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 提示词记录 ============
class PromptRequest(SchemaBase):
    user_input: str = Field(..., description="用户描述")
    model_config_id: int = Field(..., description="模型配置ID")


class PromptResponse(SchemaBase):
    generated_prompt: str


class PromptRecordResponse(SchemaBase):
    id: int
    user_input: str
    generated_prompt: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 知识库 ============
class KnowledgeCreate(SchemaBase):
    title: str
    content: str
    source: Optional[str] = None
    source_type: str = "manual"
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class KnowledgeResponse(SchemaBase):
    id: int
    title: str
    content: str
    source: Optional[str]
    source_type: Optional[str]
    category: Optional[str]
    tags: Optional[List[str]]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 试题 ============
class QuizGenerateRequest(SchemaBase):
    category: Optional[str] = Field(None, description="技能分类")
    difficulty: str = Field("basic", description="难度")
    count: int = Field(5, ge=1, le=50, description="题数")
    model_config_id: int = Field(..., description="模型配置ID")


class QuizSubmitRequest(SchemaBase):
    session_id: int
    answers: List[Dict[str, Any]]  # [{question_id, user_answer}]


class QuizQuestionResponse(SchemaBase):
    id: int
    question: str
    question_type: str
    options: Optional[List[str]]
    difficulty: str
    category: Optional[str]

    class Config:
        from_attributes = True


class QuizAnswerResponse(SchemaBase):
    question_id: int
    question: str
    user_answer: Optional[str]
    correct_answer: str
    explanation: Optional[str]
    is_correct: bool


class QuizSessionResponse(SchemaBase):
    id: int
    category: Optional[str]
    difficulty: Optional[str]
    total_questions: int
    correct_count: int
    score: Optional[float]
    started_at: datetime
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True
