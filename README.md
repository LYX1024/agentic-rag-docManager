# Agentic RAG Document Manager

智能知识库搜索平台 —— 结合 Agentic RAG 与文档管理系统。

## 分支说明

| 分支 | 用途 |
|------|------|
| `master` | 生产部署分支。`frontend/vite.config.ts` 代理指向 Nginx (`:80`)，使用 `docker compose up -d` 一键部署 |
| `dev` | 日常开发分支。`frontend/vite.config.ts` 代理指向 Java 后端 (`:8080`)，配合 `docker-compose.dev.yml` 仅启动基础设施容器 |

> 两个分支的业务代码始终保持一致，差异仅在于部署配置文件。

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| **前端** | Vue 3 + Vite + Tailwind CSS | 北欧极简风格，手写 UI 组件，无第三方组件库 |
| **Java 后端** | Spring Boot 3.2 + MyBatis-Plus | REST API + gRPC 客户端 |
| **Python RAG** | Python 3.11 + gRPC aio + LangChain | 异步协程架构，Agentic RAG 引擎 |
| **RPC** | gRPC (protobuf) | Java ↔ Python 跨语言通信 |
| **存储** | MySQL + MinIO (S3) + Redis | 元数据/文件存储/缓存 |
| **向量库** | FAISS | BM25 + 向量混合检索 (RRF 融合) |
| **部署** | Docker Compose | 统一开发与生产环境 |

## 架构

```
┌──────────┐   HTTP/SSE   ┌──────────────┐   gRPC    ┌──────────────────┐
│  Vue 3   │ ───────────→ │  Java Spring │ ────────→ │  Python RAG      │
│ Frontend │ ←─────────── │  Backend     │ ←──────── │  (Async gRPC)    │
└──────────┘              └──────┬───────┘           └────────┬─────────┘
                                 │                            │
                                 ▼                            ▼
                          ┌──────────┐              ┌──────────────────┐
                          │  MySQL   │              │  FAISS + BM25    │
                          │  Redis   │              │  + Embedding API │
                          │  MinIO   │              └──────────────────┘
                          └──────────┘
```

### 核心数据流

```
文档上传:  前端 → Java → MinIO → gRPC → Python 解析/分块/嵌入 → FAISS
                              ↕ Redis Pub/Sub 异步通知状态变更
搜索:      前端 → Java → gRPC → Python BM25+Vector RRF 融合 → LLM 重排序
对话:      前端(SSE) → Java → gRPC streaming → Python Agentic RAG
            (ReAct 循环: Thought → search/rewrite → Observation → Final Answer)
```

## 功能

### 文档管理系统
- 多格式支持：PDF / Word / PPT / Markdown / 代码 / 图片 OCR
- 按标题层级分节，chunk 保留文档结构上下文
- 在线预览：Markdown 渲染 / PDF canvas / Word 转换
- 分类组织 + MinIO 对象存储

### Agentic RAG 检索
- **ReAct 范式**：LLM 自主决策搜索/重写/回答，最多 5 轮
- **双工具调用**：`search()` 直接检索 / `rewrite()` 查询重写多路搜索
- **混合检索**：BM25（关键词）+ FAISS（语义向量）+ RRF 融合
- **对话历史**：滑动窗口（最近 8 轮完整保留）+ LLM 摘要压缩
- **历史持久化**：MySQL 存储 + Redis 缓存 + Python 从 Java 拉取恢复

## 快速启动

### 环境要求
- Docker 24+
- JDK 17
- Python 3.11
- Node.js 18+

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少配置 API Key：
```ini
EMBEDDING_API_KEY=sk-your-embedding-key
LLM_API_KEY=sk-your-llm-key
```

### 2. 构建前端

```bash
cd frontend
npm install
npm run build
cd ..
```

### 3. 一键部署

```bash
docker compose up -d --build
```

### 4. 访问

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost |
| MinIO 管理 | http://localhost:9001 |

默认管理员：`admin` / `admin123`

### 开发模式

详见 [docs/dev-deployment.md](docs/dev-deployment.md)

## 项目结构

```
├── frontend/            # Vue 3 前端
├── backend/             # Spring Boot Java 后端
├── rag-service/         # Python RAG 引擎
│   ├── config/          # Pydantic YAML 配置
│   ├── loader/          # 文档加载器 (PDF/MD/DOCX/PPTX/代码)
│   ├── splitter/        # 中文递归分块器
│   ├── embedding/       # OpenAI 兼容异步嵌入客户端
│   ├── retriever/       # BM25 + Vector + Hybrid 检索器
│   ├── kb_service/      # FAISS 向量存储 (ABC + 工厂)
│   ├── pipeline/        # 摄入流水线编排
│   └── services/
│       ├── chat/        # Agentic RAG (ReAct + Tool Calling)
│       ├── search/      # 搜索服务
│       ├── document/    # 文档管理
│       └── kb/          # 知识库 CRUD
├── proto/               # gRPC Proto 定义
├── docs/                # 文档
└── docker/              # Dockerfile + 配置
```
