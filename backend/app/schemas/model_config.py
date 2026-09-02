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
    capabilities: List[str] = Field(default_factory=list, description="模型能力标签")
    priority: int = Field(100, ge=0, le=10000, description="故障切换优先级")
    enabled: bool = Field(True, description="是否启用")
    fallback_model_ids: List[int] = Field(default_factory=list, description="备用模型 ID 列表")

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
    capabilities: Optional[List[str]] = None
    priority: Optional[int] = Field(None, ge=0, le=10000)
    enabled: Optional[bool] = None
    fallback_model_ids: Optional[List[int]] = None

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
    capabilities: List[str] = Field(default_factory=list)
    priority: int = 100
    enabled: bool = True
    fallback_model_ids: List[int] = Field(default_factory=list)
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
    sources: List[Dict[str, Any]]


class SearchRecordResponse(SchemaBase):
    id: int
    query: str
    engine: str
    result: Optional[str]
    sources: Optional[List[Dict[str, Any]]]
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
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
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
    crawled_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgeSearchResponse(SchemaBase):
    """A ranked chunk with its source document citation."""

    knowledge_id: int
    chunk_id: int
    title: str
    content: str
    source: Optional[str] = None
    source_type: Optional[str] = None
    category: Optional[str] = None
    score: float
    citation: Dict[str, str] = Field(default_factory=dict)


class KnowledgeImportRequest(SchemaBase):
    """Start a URL or built-in crawler import job."""

    source_type: str = Field("url", description="url、official、github、csdn 或 arxiv")
    target: str = Field(..., min_length=1, max_length=1000)
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    max_items: int = Field(10, ge=1, le=100)


class KnowledgeImportJobResponse(SchemaBase):
    id: int
    status: str
    source_type: str
    target: Optional[str]
    total_items: int
    imported_items: int
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============ Prompt IDE ============
class PromptTemplateCreate(SchemaBase):
    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    description: Optional[str] = None
    variables: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class PromptTemplateUpdate(SchemaBase):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    variables: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class PromptTemplateResponse(SchemaBase):
    id: int
    name: str
    description: Optional[str]
    content: str
    variables: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    current_version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptVersionCreate(SchemaBase):
    content: str = Field(..., min_length=1)
    variables: Optional[List[str]] = None
    change_note: Optional[str] = Field(None, max_length=500)


class PromptVersionResponse(SchemaBase):
    id: int
    template_id: int
    version: int
    content: str
    variables: List[str] = Field(default_factory=list)
    change_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PromptRenderRequest(SchemaBase):
    content: str = Field(..., min_length=1)
    values: Dict[str, Any] = Field(default_factory=dict)
    strict: bool = True


class PromptRenderResponse(SchemaBase):
    rendered: str
    variables: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class PromptDiffResponse(SchemaBase):
    from_version: int
    to_version: int
    diff: str


class PromptTestRequest(SchemaBase):
    prompt: Optional[str] = Field(None, min_length=1)
    template_id: Optional[int] = None
    version: Optional[int] = Field(None, ge=1)
    model_config_id: int = Field(..., description="模型配置ID")
    variables: Dict[str, Any] = Field(default_factory=dict)


class PromptTestResponse(SchemaBase):
    output: str
    model_config_id: int


# ============ 试题 ============
class QuizGenerateRequest(SchemaBase):
    category: Optional[str] = Field(None, description="技能分类")
    difficulty: str = Field("basic", description="难度")
    count: int = Field(5, ge=1, le=50, description="题数")
    model_config_id: int = Field(..., description="模型配置ID")
    # 可选地把题目绑定到指定知识文档；不传时由生成流程自动选择上下文。
    knowledge_id: Optional[int] = Field(None, description="知识库文档ID")


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
    knowledge_id: Optional[int] = None
    source_title: Optional[str] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True


class QuizAnswerResponse(SchemaBase):
    question_id: int
    question: str
    user_answer: Optional[Any]
    correct_answer: Any
    explanation: Optional[str]
    is_correct: bool
    knowledge_id: Optional[int] = None
    source_title: Optional[str] = None
    source: Optional[str] = None


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


class QuizWrongAnswerResponse(SchemaBase):
    """错题本中的一次错误作答记录。"""

    attempt_id: int
    session_id: Optional[int] = None
    question_id: int
    question: str
    question_type: str
    options: Optional[List[str]] = None
    user_answer: Optional[str] = None
    correct_answer: Any
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    category: Optional[str] = None
    knowledge_id: Optional[int] = None
    source_title: Optional[str] = None
    source: Optional[str] = None
    attempted_at: Optional[datetime] = None


class QuizWeaknessItem(SchemaBase):
    """按分类或难度聚合的薄弱点。"""

    name: str
    total_attempts: int
    wrong_count: int
    correct_count: int
    accuracy: float
    weakness_score: float


class QuizWeaknessStats(SchemaBase):
    total_attempts: int
    wrong_count: int
    correct_count: int
    accuracy: float
    categories: List[QuizWeaknessItem] = Field(default_factory=list)
    difficulties: List[QuizWeaknessItem] = Field(default_factory=list)
