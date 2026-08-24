# 测试模块

本目录包含 RouterAgent 后端的完整测试套件。

## 测试结构

```
tests/
├── __init__.py           # 模块初始化
├── conftest.py           # Pytest 配置和 fixtures
├── run_tests.py          # 测试运行脚本
├── test_agents.py        # Agent 单元测试
├── test_api.py           # API 端点测试
├── test_models.py        # 数据库模型测试
├── test_services.py      # 服务层测试
└── test_websocket.py     # WebSocket 集成测试
```

## 安装测试依赖

```bash
cd backend
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

测试依赖已包含在 `requirements.txt` 中:
- pytest==7.4.0
- pytest-asyncio==0.23.3
- pytest-cov==4.1.0
- aiosqlite==0.19.0
- httpx==0.26.0

## 运行测试

### 运行所有测试
```bash
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/ -v
```

### 运行特定类型的测试
```bash
# 单元测试
pytest tests/ -v -m unit

# 集成测试
pytest tests/ -v -m integration

# API 测试
pytest tests/ -v -m api

# Agent 测试
pytest tests/ -v -m agent

# WebSocket 测试
pytest tests/ -v -m websocket
```

### 运行特定文件
```bash
pytest tests/test_agents.py -v
pytest tests/test_api.py -v
pytest tests/test_websocket.py -v
```

### 生成覆盖率报告
```bash
pytest tests/ -v --cov=app --cov-report=html --cov-report=term
```

覆盖率报告将生成在 `htmlcov/` 目录中。

### 使用测试脚本
```bash
cd backend
python tests/run_tests.py --type all --verbose --coverage
```

## 测试分类

### 1. 单元测试 (Unit Tests)
- 测试独立的函数和类方法
- 使用 mock 隔离外部依赖
- 快速执行，无副作用

### 2. 集成测试 (Integration Tests)
- 测试多个组件的协作
- 使用测试数据库（SQLite 内存数据库）
- 测试完整的业务流程

### 3. API 测试 (API Tests)
- 测试 REST API 端点
- 测试请求/响应格式
- 测试错误处理

### 4. WebSocket 测试
- 测试 WebSocket 连接
- 测试消息格式
- 测试 Agent 流式响应

## 测试覆盖范围

### Agent 测试 (`test_agents.py`)
- ✅ BaseAgent 抽象类
- ✅ SearchAgent 搜索逻辑
- ✅ PromptAgent 提示词优化
- ✅ QuizAgent 试题生成

### API 测试 (`test_api.py`)
- ✅ 模型配置 CRUD
- ✅ 知识库管理
- ✅ 搜索记录
- ✅ 提示词记录
- ✅ 试题管理

### 模型测试 (`test_models.py`)
- ✅ ModelConfig 模型
- ✅ SearchRecord 模型
- ✅ PromptRecord 模型
- ✅ KnowledgeBase 模型
- ✅ QuizQuestion 模型
- ✅ QuizSession 模型
- ✅ QuizAttempt 模型

### 服务测试 (`test_services.py`)
- ✅ LLMService
- ✅ 搜索引擎
- ✅ 爬虫服务

### WebSocket 测试 (`test_websocket.py`)
- ✅ 连接管理
- ✅ 消息格式验证
- ✅ 错误处理
- ✅ Agent 路由

## 最佳实践

1. **测试隔离**: 每个测试使用独立的数据库会话
2. **异步支持**: 使用 pytest-asyncio 测试异步代码
3. **Mock 外部服务**: LLM 和搜索引擎使用 mock
4. **清晰的断言**: 使用描述性的断言消息
5. **测试命名**: 使用 `test_<功能>_<场景>` 格式

## CI/CD 集成

在 CI/CD 管道中添加:
```yaml
- name: Run Tests
  run: |
    cd backend
    python -m venv .venv
    . .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v --cov=app --cov-report=xml
```

## 注意事项

1. 测试使用 SQLite 内存数据库，不需要真实的 MySQL 连接
2. WebSocket 测试需要 mock LLM 服务
3. 某些集成测试可能需要设置环境变量
4. 覆盖率目标：建议保持在 80% 以上
