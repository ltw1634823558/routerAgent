# RouterAgent 🤖

自定义 AI 智能体平台，支持多种国内 LLM 模型和搜索引擎。

## ✨ 功能特性

### 🔧 模型配置管理
- 支持智谱、阿里通义、百度文心、讯飞星火、腾讯混元、月之暗面、MiniMax、DeepSeek 等国内主流模型
- 支持自定义模型配置
- API KEY 通过环境变量安全存储

### 🔍 搜集 Agent
- 支持 DuckDuckGo（免费）、Tavily、SerpAPI、Google、Bing 等搜索引擎
- 搜索结果自动提炼为结构化答案
- 附带来源链接

### ✨ 提示词优化 Agent
- 自然语言描述需求，自动生成优化的系统提示词
- 支持复制和导出

### 📝 问答 Agent（AI 岗位试题）
- 覆盖 AI 大模型开发、智能体开发、算法开发等技能领域
- 支持选择题、填空题、代码题
- 三级难度：基础/进阶/精通
- 答案附带解析和出处

### 📚 知识库管理
- 支持自动爬取更新（官方文档、CSDN、arXiv、GitHub）
- 支持手动导入文档
- 知识库统计和分类管理

## 🏗️ 技术栈

### 前端
- Vue 3 + TypeScript
- Vite
- Element Plus
- Pinia

### 后端
- FastAPI
- SQLAlchemy 2.0
- aiomysql
- WebSocket

### 数据库
- MySQL 8.0

### 部署
- Docker + Docker Compose

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/ltw1634823558/routerAgent.git
cd routerAgent
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API KEY
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 访问应用

- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 📁 项目结构

```
routerAgent/
├── frontend/           # Vue3 前端
│   ├── src/
│   │   ├── api/        # API 接口
│   │   ├── views/      # 页面组件
│   │   ├── router/     # 路由配置
│   │   └── stores/     # 状态管理
│   └── ...
├── backend/            # FastAPI 后端
│   ├── app/
│   │   ├── models/     # 数据库模型
│   │   ├── schemas/    # Pydantic 模型
│   │   ├── routers/    # API 路由
│   │   ├── agents/     # Agent 实现
│   │   └── services/   # 业务服务
│   └── ...
├── mysql/              # MySQL 初始化脚本
├── docker-compose.yml
└── README.md
```

## 🔑 API KEY 配置

在 `.env` 文件中配置以下环境变量：

```bash
# LLM API Keys
ZHIPU_API_KEY=your_zhipu_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key
MOONSHOT_API_KEY=your_moonshot_api_key

# 搜索引擎 API Keys
TAVILY_API_KEY=your_tavily_api_key
SERPAPI_KEY=your_serpapi_key
```

## 📖 开发指南

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

### 数据库迁移

项目启动时会自动创建表结构，无需手动迁移。

## 📄 License

MIT

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
