# RouterAgent 架构设计文档

## 项目结构

```
routerAgent/
├── frontend/                    # Vue3 + TypeScript 前端
│   ├── src/
│   │   ├── api/                 # API 接口
│   │   ├── components/          # 通用组件
│   │   ├── views/               # 页面视图
│   │   │   ├── ModelConfig.vue  # 模型配置页
│   │   │   ├── SearchAgent.vue  # 搜集 Agent
│   │   │   ├── PromptAgent.vue  # 提示词优化 Agent
│   │   │   └── QAAgent.vue      # 问答 Agent
│   │   ├── stores/              # Pinia 状态管理
│   │   ├── utils/               # 工具函数
│   │   └── types/               # TypeScript 类型
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── main.py              # 应用入口
│   │   ├── config.py            # 配置管理
│   │   ├── database.py          # 数据库连接
│   │   ├── models/              # SQLAlchemy 模型
│   │   │   ├── __init__.py
│   │   │   ├── model_config.py  # 模型配置
│   │   │   ├── search.py        # 搜索记录
│   │   │   ├── quiz.py          # 试题/答题
│   │   │   └── knowledge.py     # 知识库
│   │   ├── schemas/             # Pydantic 模型
│   │   ├── routers/             # API 路由
│   │   │   ├── model.py         # 模型配置 API
│   │   │   ├── search.py        # 搜索 Agent API
│   │   │   ├── prompt.py        # 提示词 Agent API
│   │   │   ├── quiz.py          # 问答 Agent API
│   │   │   └── knowledge.py     # 知识库 API
│   │   ├── agents/              # Agent 实现
│   │   │   ├── base.py          # Agent 基类
│   │   │   ├── search.py        # 搜集 Agent
│   │   │   ├── prompt.py        # 提示词 Agent
│   │   │   └── quiz.py          # 问答 Agent
│   │   ├── services/            # 业务逻辑
│   │   │   ├── llm/             # LLM 服务
│   │   │   ├── search/          # 搜索服务
│   │   │   └── crawler/         # 爬虫服务
│   │   └── utils/               # 工具函数
│   ├── requirements.txt
│   └── Dockerfile
│
├── mysql/                       # MySQL 初始化脚本
│   └── init.sql
│
├── docs/                        # 文档
│   ├── REQUIREMENTS.md
│   └── ARCHITECTURE.md
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 数据库设计

### 1. 模型配置表 (model_configs)

```sql
CREATE TABLE model_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '配置名称',
    provider VARCHAR(50) NOT NULL COMMENT '提供商：zhipu/alibaba/baidu/xunfei/tencent/moonshot/minimax/deepseek/custom',
    model_name VARCHAR(100) NOT NULL COMMENT '模型名称',
    api_url VARCHAR(500) COMMENT 'API 地址',
    api_key_env VARCHAR(100) NOT NULL COMMENT 'API KEY 环境变量名',
    is_default BOOLEAN DEFAULT FALSE COMMENT '是否默认',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 2. 搜索记录表 (search_records)

```sql
CREATE TABLE search_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    query VARCHAR(500) NOT NULL COMMENT '搜索内容',
    engine VARCHAR(50) NOT NULL COMMENT '搜索引擎',
    result TEXT COMMENT '结构化答案',
    sources JSON COMMENT '来源链接列表',
    model_config_id INT COMMENT '使用的模型配置',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_config_id) REFERENCES model_configs(id)
);
```

### 3. 提示词记录表 (prompt_records)

```sql
CREATE TABLE prompt_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_input TEXT NOT NULL COMMENT '用户描述',
    generated_prompt TEXT NOT NULL COMMENT '生成的提示词',
    model_config_id INT COMMENT '使用的模型配置',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_config_id) REFERENCES model_configs(id)
);
```

### 4. 知识库表 (knowledge_base)

```sql
CREATE TABLE knowledge_base (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL COMMENT '标题',
    content LONGTEXT NOT NULL COMMENT '内容',
    source VARCHAR(500) COMMENT '来源 URL',
    source_type ENUM('official', 'csdn', 'arxiv', 'github', 'manual') COMMENT '来源类型',
    category VARCHAR(100) COMMENT '技能分类',
    tags JSON COMMENT '标签列表',
    crawled_at TIMESTAMP COMMENT '爬取时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5. 试题表 (quiz_questions)

```sql
CREATE TABLE quiz_questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    knowledge_id INT COMMENT '关联知识库',
    question TEXT NOT NULL COMMENT '题目',
    question_type ENUM('choice', 'multiple_choice', 'fill', 'code') NOT NULL COMMENT '题型',
    options JSON COMMENT '选项（选择题）',
    answer TEXT NOT NULL COMMENT '答案',
    explanation TEXT COMMENT '解析',
    difficulty ENUM('basic', 'intermediate', 'advanced') NOT NULL COMMENT '难度',
    category VARCHAR(100) COMMENT '技能分类',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_base(id)
);
```

### 6. 答题记录表 (quiz_attempts)

```sql
CREATE TABLE quiz_attempts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    user_answer TEXT COMMENT '用户答案',
    is_correct BOOLEAN COMMENT '是否正确',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES quiz_questions(id)
);
```

### 7. 答题会话表 (quiz_sessions)

```sql
CREATE TABLE quiz_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(100) COMMENT '技能分类',
    difficulty ENUM('basic', 'intermediate', 'advanced') COMMENT '难度',
    total_questions INT NOT NULL COMMENT '总题数',
    correct_count INT DEFAULT 0 COMMENT '正确数',
    score DECIMAL(5,2) COMMENT '得分',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP COMMENT '完成时间'
);
```

---

## API 设计

### WebSocket 端点

```
ws://localhost:8000/ws/agent/{agent_type}
```

- `agent_type`: search / prompt / quiz

### REST API

#### 模型配置
- `GET /api/models` - 获取所有模型配置
- `POST /api/models` - 创建模型配置
- `PUT /api/models/{id}` - 更新模型配置
- `DELETE /api/models/{id}` - 删除模型配置
- `PUT /api/models/{id}/default` - 设为默认

#### 搜索 Agent
- `GET /api/search/records` - 获取搜索历史
- `WebSocket /ws/agent/search` - 实时搜索

#### 提示词 Agent
- `GET /api/prompt/records` - 获取提示词历史
- `WebSocket /ws/agent/prompt` - 实时生成

#### 问答 Agent
- `GET /api/quiz/categories` - 获取技能分类
- `POST /api/quiz/generate` - 生成试题
- `POST /api/quiz/submit` - 提交答案
- `GET /api/quiz/history` - 获取答题历史

#### 知识库
- `GET /api/knowledge` - 获取知识库列表
- `POST /api/knowledge/import` - 手动导入文档
- `POST /api/knowledge/crawl` - 触发爬取

---

## 技术选型详情

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **状态管理**: Pinia
- **UI 组件库**: Element Plus / Naive UI
- **HTTP 客户端**: Axios
- **WebSocket**: 原生 WebSocket API

### 后端
- **框架**: FastAPI
- **ORM**: SQLAlchemy 2.0
- **数据库驱动**: aiomysql
- **WebSocket**: FastAPI 内置 WebSocket
- **LLM 客户端**: httpx (异步 HTTP)

### 部署
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx (可选)

---

## 开发计划

### Phase 1: 项目搭建
- [ ] 创建前后端项目结构
- [ ] 配置 Docker Compose
- [ ] 初始化数据库
- [ ] 实现基础 CRUD

### Phase 2: 核心功能
- [ ] 模型配置管理
- [ ] LLM 服务封装
- [ ] WebSocket 通信

### Phase 3: Agent 实现
- [ ] 搜集 Agent
- [ ] 提示词 Agent
- [ ] 问答 Agent

### Phase 4: 知识库
- [ ] 爬虫服务
- [ ] 知识库管理
- [ ] 试题生成

### Phase 5: 优化与部署
- [ ] 前端 UI 美化
- [ ] 性能优化
- [ ] 完整部署流程
