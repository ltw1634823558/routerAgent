# Repository Guidelines

## 项目结构与模块组织

- `backend/app/`：FastAPI 后端。`routers/` 提供 REST/WebSocket 路由，`agents/` 实现 Agent，`services/` 封装 LLM、搜索和爬虫，`models/` 与 `schemas/` 定义数据模型。
- `backend/tests/`：后端 pytest 测试及 fixtures；测试文件按功能划分为 `test_agents.py`、`test_api.py`、`test_models.py`、`test_services.py`、`test_websocket.py`。
- `frontend/src/`：Vue 3 + TypeScript 前端；页面放在 `views/`，HTTP/WebSocket 客户端放在 `api/`，路由放在 `router/`。
- `mysql/init.sql`：数据库初始化脚本；`docker-compose.yml` 当前用于启动 MySQL（主机端口 `3307`）。

## 构建、测试与本地开发

后端在 `backend/` 目录执行：

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload       # http://localhost:8000
python -m pytest tests/ -v          # 全量测试
python -m pytest tests/ -v --cov=app --cov-report=html
```

前端在 `frontend/` 目录执行：

```bash
npm install
npm run dev                         # Vite 开发服务器
npm run build                       # 类型检查并生产构建
```

需要数据库时，先复制 `.env.example` 为 `.env` 并填入密钥，再运行 `docker-compose up -d` 启动 MySQL。

## 编码风格与命名约定

Python 使用 4 空格缩进、异步函数优先，模块/函数使用 `snake_case`，类使用 `PascalCase`；新增 Agent 应继承 `BaseAgent` 并实现异步 `run()`。TypeScript/Vue 使用 2 空格缩进，组件文件采用 `PascalCase.vue`，变量和函数采用 `camelCase`。保持现有目录边界，不在路由中直接堆积业务逻辑。提交前至少运行后端测试和 `npm run build`。

## 测试指南

测试框架为 pytest 与 pytest-asyncio，测试函数命名为 `test_<功能>_<场景>`。按需使用 `unit`、`integration`、`api`、`agent`、`websocket` 标记，例如 `python -m pytest tests/ -m api`。外部 LLM、搜索服务应使用 mock；测试默认使用 SQLite fixtures，不依赖本地 MySQL。新增或修改行为应补充对应测试，覆盖率建议保持 80% 以上。

## 提交与 Pull Request

现有提交使用 Conventional Commits 风格（如 `feat: 实现 WebSocket 和 Agent 核心逻辑`）；请使用 `feat:`、`fix:`、`test:`、`docs:` 等前缀，标题简洁、使用中文描述。PR 应说明变更目的、影响范围和验证命令，关联 Issue（如有）；涉及界面改动请附截图或录屏，并注明环境变量或数据库变更。

## 安全与配置

不要提交 `.env`、API Key、真实数据库凭据或生成目录。新增配置时同步更新 `.env.example`，代码通过环境变量读取密钥；日志和测试输出不得泄露敏感值。
