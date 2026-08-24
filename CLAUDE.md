# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

RouterAgent 是一个自定义 AI 智能体平台，支持多种国内 LLM 模型（智谱、DeepSeek、通义千问、讯飞星火、腾讯混元、月之暗面、MiniMax 等）和搜索引擎。前端 Vue 3 + TypeScript + Element Plus，后端 FastAPI + SQLAlchemy 2.0 异步架构，MySQL 8.0 数据库。

## 常用命令

### 后端开发
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload    # 启动开发服务器 (localhost:8000)
```

### 前端开发
```bash
cd frontend
npm install
npm run dev                      # 启动 Vite 开发服务器 (localhost:5173)
npm run build                    # 生产构建
```

### 测试
```bash
cd backend
python -m pytest tests/ -v                    # 运行所有测试
python -m pytest tests/ -v -m unit            # 只运行单元测试
python -m pytest tests/ -v -m api             # 只运行 API 测试
python -m pytest tests/ -v --cov=app --cov-report=html  # 生成覆盖率报告
```

### Docker 一键启动
```bash
docker-compose up -d             # 启动 MySQL + 后端 + 前端
```

### 环境配置
```bash
cp .env.example .env             # 复制并填写 API KEY
```

## 架构

### 通信模式
- **REST API** (`/api/...`): CRUD 操作（模型配置、历史记录、知识库管理）
- **WebSocket** (`ws://localhost:8000/ws/agent/{agent_type}`): Agent 流式交互，`agent_type` 为 `search`/`prompt`/`quiz`

### Agent 架构 (`backend/app/agents/`)
所有 Agent 继承 `BaseAgent`，接收 `model_config` dict，通过 `LLMService` 调用模型，返回 `AsyncGenerator[str, None]` 流式输出。
- `SearchAgent`: 搜索引擎查询 → 搜索结果 → LLM 提炼结构化答案
- `PromptAgent`: 用户描述 → LLM 生成优化提示词
- `QuizAgent`: 技能分类/难度 → 知识库上下文 + LLM 生成试题(JSON)

### LLM 服务 (`backend/app/services/llm/base.py`)
`LLMService` 统一封装多家 LLM 调用：智谱(zhipuai SDK)、阿里(DashScope API)、DeepSeek/Moonshot/OpenAI 兼容格式。API Key 从环境变量读取，key 名存在 `model_config.api_key_env` 中。

### 搜索引擎 (`backend/app/services/search/engines.py`)
工厂模式 `get_search_engine(engine_type, api_key)` 返回搜索引擎实例。
- **Bocha 波查**: 国内可用，推荐
- **Tavily**: 专业 AI 搜索，推荐
- **DuckDuckGo**: 免费无需 key，国内需代理
- **SerpAPI**: Google 搜索
- **Bing**: 微软搜索

### 数据层
- **Models**: `backend/app/models/model_config.py`，所有 SQLAlchemy 模型集中在一个文件
- **数据库**: SQLAlchemy 2.0 异步 (`aiomysql`)，启动时自动建表 (`init_db`)
- **Schemas**: `backend/app/schemas/` Pydantic 模型
- **路由**: `backend/app/routers/` 按 Agent 模块拆分

### 前端结构
- `src/views/`: 五个主要页面
  - `ModelConfig.vue` - 模型配置管理
  - `SearchAgent.vue` - 智能搜索
  - `PromptAgent.vue` - 提示词优化
  - `QuizAgent.vue` - 试题生成与答题
  - `Knowledge.vue` - 知识库管理
- `src/api/`: HTTP 请求 (`request.ts`) 和 WebSocket 封装 (`websocket.ts`)
- UI 框架: Element Plus + 自定义渐变主题

### 测试模块 (`backend/tests/`)
- `conftest.py` - 测试配置和 fixtures
- `test_agents.py` - Agent 单元测试
- `test_api.py` - API 端点测试
- `test_models.py` - 数据库模型测试
- `test_services.py` - 服务层测试
- `test_websocket.py` - WebSocket 集成测试

### Docker 服务
- MySQL 映射到宿主机 3307 端口（避免与本地 MySQL 冲突）
- 后端和前端通过 Docker Compose 的 `router-agent-network` 网络互联

## 前端设计规范

### 色彩方案
- 侧边栏: 深色渐变 `#0f0c29` → `#302b63` → `#24243e`
- 主题色: 渐变紫色 `#667eea` → `#764ba2`
- 功能色:
  - 搜索: 蓝色 `#3b82f6`
  - 提示词: 紫色 `#a855f7`
  - 问答: 橙色 `#f97316`
  - 知识库: 粉色 `#ec4899`
  - 模型配置: 绿色 `#10b981`

### 组件样式
- 卡片圆角: 16px
- 按钮圆角: 10-12px
- 阴影: `0 4px 20px rgba(0, 0, 0, 0.05)`
- 悬停效果: `transform: translateY(-2px)`

## 代码规范

### 语言
- 所有代码注释和日志使用中文
- 回复使用中文

### 数据库模型
- 所有 SQLAlchemy 模型集中在 `backend/app/models/model_config.py`
- 枚举类型定义在同一文件中

### Agent 开发
- 继承 `BaseAgent` 基类
- 实现 `run()` 方法返回异步生成器
- 使用 `stream_response()` 方法调用 LLM

### 测试规范
- 单元测试: `@pytest.mark.unit`
- 集成测试: `@pytest.mark.integration`
- API 测试: `@pytest.mark.api`
- WebSocket 测试: `@pytest.mark.websocket`
- Agent 测试: `@pytest.mark.agent`
