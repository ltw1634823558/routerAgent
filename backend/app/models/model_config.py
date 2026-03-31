from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Enum, ForeignKey, DECIMAL
from sqlalchemy.sql import func
from app.database import Base
import enum


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


class SourceTypeEnum(enum.Enum):
    OFFICIAL = "official"
    CSDN = "csdn"
    ARXIV = "arxiv"
    GITHUB = "github"
    MANUAL = "manual"


class QuestionTypeEnum(enum.Enum):
    CHOICE = "choice"
    FILL = "fill"
    CODE = "code"


class DifficultyEnum(enum.Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ModelConfig(Base):
    """模型配置表"""
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="配置名称")
    provider = Column(String(50), nullable=False, comment="提供商")
    model_name = Column(String(100), nullable=False, comment="模型名称")
    api_url = Column(String(500), comment="API 地址")
    api_key_env = Column(String(100), nullable=False, comment="API KEY 环境变量名")
    is_default = Column(Boolean, default=False, comment="是否默认")
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
    model_config_id = Column(Integer, ForeignKey("model_configs.id"), comment="使用的模型配置")
    created_at = Column(DateTime, server_default=func.now())


class PromptRecord(Base):
    """提示词记录表"""
    __tablename__ = "prompt_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_input = Column(Text, nullable=False, comment="用户描述")
    generated_prompt = Column(Text, nullable=False, comment="生成的提示词")
    model_config_id = Column(Integer, ForeignKey("model_configs.id"), comment="使用的模型配置")
    created_at = Column(DateTime, server_default=func.now())


class KnowledgeBase(Base):
    """知识库表"""
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="内容")
    source = Column(String(500), comment="来源 URL")
    source_type = Column(String(20), comment="来源类型")
    category = Column(String(100), comment="技能分类")
    tags = Column(JSON, comment="标签列表")
    crawled_at = Column(DateTime, comment="爬取时间")
    created_at = Column(DateTime, server_default=func.now())


class QuizQuestion(Base):
    """试题表"""
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge_base.id"), comment="关联知识库")
    question = Column(Text, nullable=False, comment="题目")
    question_type = Column(String(20), nullable=False, comment="题型")
    options = Column(JSON, comment="选项（选择题）")
    answer = Column(Text, nullable=False, comment="答案")
    explanation = Column(Text, comment="解析")
    difficulty = Column(String(20), nullable=False, comment="难度")
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
    difficulty = Column(String(20), comment="难度")
    total_questions = Column(Integer, nullable=False, comment="总题数")
    correct_count = Column(Integer, default=0, comment="正确数")
    score = Column(DECIMAL(5, 2), comment="得分")
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, comment="完成时间")
