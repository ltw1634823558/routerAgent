-- RouterAgent 数据库初始化脚本

CREATE DATABASE IF NOT EXISTS router_agent DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE router_agent;

-- 模型配置表
CREATE TABLE IF NOT EXISTS model_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '配置名称',
    provider VARCHAR(50) NOT NULL COMMENT '提供商',
    model_name VARCHAR(100) NOT NULL COMMENT '模型名称',
    api_url VARCHAR(500) COMMENT 'API 地址',
    api_key_env VARCHAR(100) NOT NULL COMMENT 'API KEY 环境变量名',
    is_default BOOLEAN DEFAULT FALSE COMMENT '是否默认',
    capabilities JSON COMMENT '模型能力标签',
    priority INT NOT NULL DEFAULT 100 COMMENT '故障切换优先级，数值越小越优先',
    enabled BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
    fallback_model_ids JSON COMMENT '备用模型 ID 列表',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型配置表';

-- 搜索记录表
CREATE TABLE IF NOT EXISTS search_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    query VARCHAR(500) NOT NULL COMMENT '搜索内容',
    engine VARCHAR(50) NOT NULL COMMENT '搜索引擎',
    result TEXT COMMENT '结构化答案',
    sources JSON COMMENT '来源链接列表',
    model_config_id INT COMMENT '使用的模型配置',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_config_id) REFERENCES model_configs(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='搜索记录表';

-- 提示词记录表
CREATE TABLE IF NOT EXISTS prompt_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_input TEXT NOT NULL COMMENT '用户描述',
    generated_prompt TEXT NOT NULL COMMENT '生成的提示词',
    model_config_id INT COMMENT '使用的模型配置',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_config_id) REFERENCES model_configs(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提示词记录表';

-- Prompt IDE 模板与版本表
CREATE TABLE IF NOT EXISTS prompt_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '模板名称',
    description TEXT COMMENT '模板说明',
    content LONGTEXT NOT NULL COMMENT '模板正文，使用 {{variable}} 占位符',
    variables JSON NOT NULL COMMENT '变量名列表',
    tags JSON NOT NULL COMMENT '标签列表',
    current_version INT NOT NULL DEFAULT 1 COMMENT '当前版本号',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提示词模板';

CREATE TABLE IF NOT EXISTS prompt_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_id INT NOT NULL COMMENT '模板 ID',
    version INT NOT NULL COMMENT '版本号',
    content LONGTEXT NOT NULL COMMENT '版本正文',
    variables JSON NOT NULL COMMENT '变量名列表',
    change_note VARCHAR(500) COMMENT '变更说明',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_prompt_version_template_version (template_id, version),
    FOREIGN KEY (template_id) REFERENCES prompt_templates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提示词模板版本';

-- 知识库表
CREATE TABLE IF NOT EXISTS knowledge_base (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL COMMENT '标题',
    content LONGTEXT NOT NULL COMMENT '内容',
    source VARCHAR(500) COMMENT '来源 URL',
    source_type ENUM('official', 'csdn', 'arxiv', 'github', 'url', 'manual') COMMENT '来源类型',
    category VARCHAR(100) COMMENT '技能分类',
    tags JSON COMMENT '标签列表',
    crawled_at TIMESTAMP COMMENT '爬取时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库表';

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    knowledge_id INT NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(500),
    metadata_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_knowledge_chunks_knowledge_id (knowledge_id),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_base(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文本切片';

CREATE TABLE IF NOT EXISTS knowledge_import_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    source_type VARCHAR(30) NOT NULL DEFAULT 'url',
    target VARCHAR(1000),
    options JSON,
    total_items INT NOT NULL DEFAULT 0,
    imported_items INT NOT NULL DEFAULT 0,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    finished_at TIMESTAMP NULL,
    INDEX idx_knowledge_import_jobs_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库导入任务';

-- 试题表
CREATE TABLE IF NOT EXISTS quiz_questions (
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
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_base(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='试题表';

-- 答题会话表
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(100) COMMENT '技能分类',
    difficulty ENUM('basic', 'intermediate', 'advanced') COMMENT '难度',
    total_questions INT NOT NULL COMMENT '总题数',
    correct_count INT DEFAULT 0 COMMENT '正确数',
    score DECIMAL(5,2) DEFAULT 0 COMMENT '得分',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP COMMENT '完成时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='答题会话表';

-- 答题记录表
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT COMMENT '答题会话ID',
    question_id INT NOT NULL,
    user_answer TEXT COMMENT '用户答案',
    is_correct BOOLEAN COMMENT '是否正确',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES quiz_questions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='答题记录表';

-- 插入默认模型配置
INSERT INTO model_configs (name, provider, model_name, api_url, api_key_env, is_default) VALUES
('智谱 GLM-4', 'zhipu', 'glm-4', 'https://open.bigmodel.cn/api/paas/v4', 'ZHIPU_API_KEY', TRUE),
('智谱 GLM-4-Flash', 'zhipu', 'glm-4-flash', 'https://open.bigmodel.cn/api/paas/v4', 'ZHIPU_API_KEY', FALSE),
('DeepSeek', 'deepseek', 'deepseek-chat', 'https://api.deepseek.com/v1', 'DEEPSEEK_API_KEY', FALSE),
('通义千问', 'alibaba', 'qwen-turbo', 'https://dashscope.aliyuncs.com/api/v1', 'DASHSCOPE_API_KEY', FALSE),
('Moonshot Kimi', 'moonshot', 'moonshot-v1-8k', 'https://api.moonshot.cn/v1', 'MOONSHOT_API_KEY', FALSE);
