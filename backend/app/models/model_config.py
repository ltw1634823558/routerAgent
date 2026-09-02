from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Enum, ForeignKey, DECIMAL
from sqlalchemy.types import TypeDecorator
from sqlalchemy.sql import func
from app.database import Base
import enum


class EnumValueString(TypeDecorator):
    """Store enum values as strings while accepting legacy enum instances.

    The original schema uses VARCHAR/ENUM columns and existing callers pass
    both plain strings and enum members. Returning the enum member keeps those
    callers compatible without restricting custom provider values.
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int, enum_class: type[enum.Enum]):
        self.enum_class = enum_class
        super().__init__(length)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.value if isinstance(value, enum.Enum) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return self.enum_class(value)
        except ValueError:
            # Keep forward-compatible/custom values readable.
            return value


class ProviderEnum(enum.Enum):
    ZHIPU = "zhipu"
    ALIBABA = "alibaba"
    BAIDU = "baidu"
    XUNFEI = "xunfei"
    TENCENT = "tencent"
    MOONSHOT = "moonshot"
    MINIMAX = "minimax"
    DEEPSEEK = "deepseek"
    CUSTOM = "custom"
    # Backwards-compatible aliases used by the original public API/tests.
    zhipu = ZHIPU
    alibaba = ALIBABA
    baidu = BAIDU
    xunfei = XUNFEI
    tencent = TENCENT
    moonshot = MOONSHOT
    minimax = MINIMAX
    deepseek = DEEPSEEK
    custom = CUSTOM


class SourceTypeEnum(enum.Enum):
    OFFICIAL = "official"
    CSDN = "csdn"
    ARXIV = "arxiv"
    GITHUB = "github"
    URL = "url"
    MANUAL = "manual"
    official = OFFICIAL
    csdn = CSDN
    arxiv = ARXIV
    github = GITHUB
    url = URL
    manual = MANUAL


class QuestionTypeEnum(enum.Enum):
    CHOICE = "choice"
    MULTIPLE_CHOICE = "multiple_choice"
    FILL = "fill"
    CODE = "code"
    choice = CHOICE
    multiple_choice = MULTIPLE_CHOICE
    fill = FILL
    code = CODE


class DifficultyEnum(enum.Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    basic = BASIC
    intermediate = INTERMEDIATE
    advanced = ADVANCED


class ModelConfig(Base):
    """模型配置表"""
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="配置名称")
    provider = Column(EnumValueString(50, ProviderEnum), nullable=False, comment="提供商")
    model_name = Column(String(100), nullable=False, comment="模型名称")
    api_url = Column(String(500), comment="API 地址")
    api_key_env = Column(String(100), nullable=False, comment="API KEY 环境变量名")
    is_default = Column(Boolean, default=False, comment="是否默认")
    # 模型中心字段：用于能力展示、优先级排序和故障切换。
    capabilities = Column(JSON, default=list, nullable=False, comment="模型能力标签")
    priority = Column(Integer, default=100, nullable=False, comment="故障切换优先级，数值越小越优先")
    enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    fallback_model_ids = Column(JSON, default=list, nullable=False, comment="备用模型 ID 列表")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SearchRecord(Base):
    """搜索记录表"""
    __tablename__ = "search_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(500), nullable=False, comment="搜索内容")
    engine = Column(String(50), nullable=False, comment="搜索引擎")
    result = Column(Text, comment="结构化答案")
    sources = Column(JSON, comment="来源链接列表")
    model_config_id = Column(
        Integer,
        ForeignKey("model_configs.id", ondelete="SET NULL"),
        comment="使用的模型配置",
    )
    created_at = Column(DateTime, server_default=func.now())


class PromptRecord(Base):
    """提示词记录表"""
    __tablename__ = "prompt_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_input = Column(Text, nullable=False, comment="用户描述")
    generated_prompt = Column(Text, nullable=False, comment="生成的提示词")
    model_config_id = Column(
        Integer,
        ForeignKey("model_configs.id", ondelete="SET NULL"),
        comment="使用的模型配置",
    )
    created_at = Column(DateTime, server_default=func.now())


class KnowledgeBase(Base):
    """知识库表"""
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="内容")
    source = Column(String(500), comment="来源 URL")
    source_type = Column(EnumValueString(20, SourceTypeEnum), comment="来源类型")
    category = Column(String(100), comment="技能分类")
    tags = Column(JSON, comment="标签列表")
    crawled_at = Column(DateTime, comment="爬取时间")
    created_at = Column(DateTime, server_default=func.now())


class QuizQuestion(Base):
    """试题表"""
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(
        Integer,
        ForeignKey("knowledge_base.id", ondelete="SET NULL"),
        comment="关联知识库",
    )
    question = Column(Text, nullable=False, comment="题目")
    question_type = Column(EnumValueString(20, QuestionTypeEnum), nullable=False, comment="题型")
    options = Column(JSON, comment="选项（选择题）")
    answer = Column(Text, nullable=False, comment="答案")
    explanation = Column(Text, comment="解析")
    difficulty = Column(EnumValueString(20, DifficultyEnum), nullable=False, comment="难度")
    category = Column(String(100), comment="技能分类")
    created_at = Column(DateTime, server_default=func.now())


class QuizAttempt(Base):
    """答题记录表"""
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id"), comment="答题会话ID")
    question_id = Column(Integer, ForeignKey("quiz_questions.id"), nullable=False)
    user_answer = Column(Text, comment="用户答案")
    is_correct = Column(Boolean, comment="是否正确")
    created_at = Column(DateTime, server_default=func.now())


class QuizSession(Base):
    """答题会话表"""
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), comment="技能分类")
    difficulty = Column(EnumValueString(20, DifficultyEnum), comment="难度")
    total_questions = Column(Integer, nullable=False, comment="总题数")
    correct_count = Column(Integer, default=0, comment="正确数")
    score = Column(DECIMAL(5, 2), default=0, comment="得分")
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, comment="完成时间")
