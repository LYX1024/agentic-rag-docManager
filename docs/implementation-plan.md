# RAG知识库搜索平台 — 实现计划

## Context

构建一个求职用的RAG知识库搜索项目，要求功能完善、链路完整、RAG核心模块有可深挖性。核心原则：**在多个基础开源项目上改造组装，不独立从零编码**。

- **前端**：Vue 3 + Element Plus
- **Java后端**：Spring Boot 3.x，负责文档CRUD、saToken统一鉴权
- **Python后端**：基于LangChain-Chatchat v0.3.x改造的RAG核心引擎
- **RPC**：gRPC（Java ↔ Python）
- **基础设施**：MySQL + MinIO（S3兼容写法）+ Redis + RocketMQ
- **部署**：Docker Compose（开发/上线统一）
- **深挖方向**：文档解析与分块策略 + 检索增强策略（不含Agent/知识图谱）

---

## 1. 项目目录结构

```
myKnowledgeBase/
├── frontend/                  # Vue 3 + Element Plus + TypeScript
├── backend/                   # Spring Boot 3.x Java
├── rag-service/               # Python RAG引擎（基于LangChain-Chatchat改造）
├── proto/                     # gRPC proto定义（Java+Python共享）
├── docs/                      # 架构文档、API文档、面试准备清单
├── docker/                    # 各服务Dockerfile + nginx配置 + MySQL初始化脚本
│   ├── nginx/
│   ├── backend/
│   ├── rag-service/
│   └── mysql/init/
├── docker-compose.yml
└── .env
```

---

## 2. 关键架构决策

### 2.1 文件上传流程（核心链路）
```
前端 → Nginx → Java接收MultipartFile
  → Java上传文件到MinIO（生成key: {kbId}/{uuid}/{filename}）
  → Java写入kb_file表（status=UPLOADED）
  → Java通过gRPC调用Python DocumentService.UploadDocument（传MinIO key）
  → Python从MinIO下载文件 → 解析 → 分块 → 嵌入 → 存入FAISS
  → Python返回结果 → Java更新kb_file.status=COMPLETED
  → RocketMQ发送"文档处理完成"通知
```

### 2.2 检索问答流程
```
前端 → Nginx → Java saToken鉴权
  → Java通过gRPC调用Python SearchService.HybridSearch
  → Python: BM25+FAISS混合检索 → RRF融合 → CrossEncoder重排序
  → 返回结果 → Java包装返回前端
```

### 2.3 RAG对话（流式）
```
前端(SSE) → Nginx → Java鉴权
  → Java通过gRPC streaming调用Python ChatService.RagChat
  → Python检索 → 构建prompt → LLM流式生成
  → Java代理gRPC流 → SSE推送给前端
```

### 2.4 存储抽象（方便切换对象存储）
- Java: MinioClient包装为`StorageService`接口，配置文件切换endpoint/credentials
- Python: boto3 S3 client，配置文件切换endpoint即为不同对象存储

---

## 3. 分阶段实施

### Phase 1：基础设施 + Docker Compose

创建完整docker-compose.yml（8个服务：mysql, minio, redis, rocketmq-namesrv, rocketmq-broker, rag-service, backend, nginx），各服务healthcheck，内部网络隔离，nginx作为唯一对外入口。

**产出文件**：
- `docker-compose.yml`
- `docker/nginx/nginx.conf`
- `docker/mysql/init/01-schema.sql`（占位，Phase 3补充DDL）
- `docker/rag-service/Dockerfile`
- `docker/backend/Dockerfile`
- `.env`

**验证**：`docker compose up -d` 全部healthy

---

### Phase 2：gRPC Proto定义 + 桩代码生成

定义4个服务契约（4个proto文件 + 1个common.proto），生成Java和Python桩代码。

**Proto服务**：
1. `KBManagementService`：CreateKB, ListKBs, DeleteKB, UpdateKB, GetKBStats
2. `DocumentService`：UploadDocument, ListDocuments, DeleteDocument, ReprocessDocument, GetDocumentStatus
3. `SearchService`：Search, HybridSearch, Rerank
4. `ChatService`：RagChat (server-streaming), GetChatHistory

**产出文件**：
- `proto/common.proto`、`proto/kb_management.proto`、`proto/document.proto`、`proto/search.proto`、`proto/chat.proto`
- Python: `rag-service/generated/` 下生成 `*_pb2.py` 和 `*_pb2_grpc.py`
- Java: `backend/pom.xml` 配置 `protobuf-maven-plugin`

---

### Phase 3：Java后端（鉴权 + CRUD + gRPC客户端）

Spring Boot 3.2.x 应用，saToken鉴权，MySQL JPA实体，MinIO文件存储，gRPC客户端连接Python服务。

**产出文件**：
- `backend/pom.xml` — Spring Boot + saToken + gRPC + MinIO + RocketMQ依赖
- `backend/src/main/java/com/mykb/` 下：
  - `config/` — SaTokenConfig, GrpcClientConfig, MinioConfig, RedisConfig, RocketMQConfig, CorsConfig
  - `entity/` — User, KnowledgeBase, KnowledgeFile, FileChunk, ChatSession
  - `repository/` — 5个JPA Repository接口
  - `service/` — UserService, KBService, DocumentService, SearchService, ChatService
  - `controller/` — AuthController, KBController, DocumentController, SearchController, ChatController
  - `grpc/client/` — KBManagementClient, DocumentClient, SearchClient, ChatClient
  - `dto/` — 请求/响应DTO
  - `exception/` — GlobalExceptionHandler
- `backend/src/main/resources/application.yml`
- `docker/mysql/init/01-schema.sql` — 5张表DDL

---

### Phase 4：Python RAG核心（解析 → 分块 → 嵌入 → 存储）

基于LangChain-Chatchat改造，保留其核心能力，替换文件系统为MinIO、SQLite为MySQL（通过Java侧管理元数据）。

**从LangChain-Chatchat保留（copy-adapt）**：
- `kb_service/kb_service.py` — KBService ABC + 工厂模式
- `kb_service/faiss_service.py` — FAISS实现
- `loader/` — LOADER_DICT + RapidOCR加载器（PDF/DOCX/PPT/图片）
- `splitter/chinese_recursive_splitter.py` — 中文递归分块器
- `splitter/zh_title_enhance.py` — 标题增强

**新写代码**：
- `server.py` — gRPC服务启动入口
- `services/` — 4个gRPC服务实现类
- `pipeline/ingestion.py` — 完整摄入流程编排（下载→解析→分块→嵌入→存储）
- `storage/minio_client.py` — MinIO下载封装（boto3，S3兼容）
- `embedding/embed_model.py` — OpenAI兼容的嵌入API客户端（~50行）
- `retriever/hybrid_retriever.py` — BM25+向量RRF混合检索
- `retriever/reranker.py` — CrossEncoder重排序
- `config/` — Pydantic YAML配置模型

**产出文件**：
- `rag-service/requirements.txt`
- `rag-service/server.py`
- `rag-service/config/config.yaml` + `model_config.py`
- `rag-service/kb_service/`（改造）
- `rag-service/loader/`（改造）
- `rag-service/splitter/`（改造）
- `rag-service/retriever/`（新写）
- `rag-service/embedding/`（新写）
- `rag-service/storage/`（新写）
- `rag-service/pipeline/`（新写）
- `rag-service/services/`（新写）

---

### Phase 5：检索 + RAG对话（串联Phase 3+4）

完善混合检索和流式RAG对话。Java端实现gRPC streaming代理到SSE。

**关键实现**：
- `rag-service/retriever/hybrid_retriever.py` — RRF融合算法：`score(d) = Σ w_i / (k + rank_i)`
- `rag-service/services/chat_service.py` — 检索→构建prompt→LLM流式生成→yield proto chunks
- `backend/.../controller/ChatController.java` — gRPC stream → SSE（Flux + ServerSentEvent）

---

### Phase 6：Vue 3前端

Vite + Vue 3 + TypeScript + Element Plus + Pinia + Vue Router。

**页面**：登录/注册、知识库管理仪表盘、知识库详情（文件列表+上传）、搜索页、RAG对话页

**产出文件**：
- `frontend/` 完整Vue项目
- `src/api/request.ts` — Axios实例（saToken请求头拦截）
- `src/api/chat.ts` — SSE EventSource封装
- `src/stores/auth.ts`、`knowledgeBase.ts`、`chat.ts` — Pinia状态管理
- `src/views/` — 6个页面
- `src/components/` — 布局+业务组件

---

### Phase 7：集成联调 + 文档

- 全链路Docker Compose验证
- `docs/architecture.md` — 架构图+数据流
- `docs/rag_pipeline.md` — RAG流水线深度解析（面试用）
- `docs/deployment.md` — 部署指南
- `docs/deep_dive_checklist.md` — 面试深挖15问+准备答案

---

## 4. 改造vs新写汇总

| 层面 | 改造自开源项目 | 新写 |
|------|--------------|------|
| Python-文档解析 | LangChain-Chatchat: LOADER_DICT, RapidOCR加载器 | MinIO下载适配 |
| Python-分块 | LangChain-Chatchat: ChineseRecursiveTextSplitter, zh_title_enhance | 无 |
| Python-向量存储 | LangChain-Chatchat: KBService ABC, FAISS实现 | 无（仅适配路径配置） |
| Python-嵌入 | 无 | OpenAI兼容API客户端（~50行） |
| Python-检索 | LangChain-Chatchat: BM25 retriever, CrossEncoder wrapper | RRF融合逻辑, gRPC服务实现 |
| Python-gRPC服务 | 无 | server.py + 4个Servicer实现 |
| Java-鉴权 | saToken框架 | Config + 登录注册接口 |
| Java-CRUD | Spring Boot + JPA框架 | 实体/仓库/服务/控制器 |
| Java-gRPC客户端 | 桩代码自动生成 | 4个Client包装类 + GrpcClientConfig |
| Java-SSE代理 | Spring WebFlux框架 | ChatController流式代理 |
| 前端 | Element Plus组件库 | 所有页面/组件/状态管理 |
| 基础设施 | 官方Docker镜像 | docker-compose.yml + Dockerfiles + nginx.conf |

---

## 5. 面试深挖准备要点

### 文档解析与分块策略
- LOADER_DICT工厂模式：文件扩展名→加载器映射，扩展新格式只需注册
- RapidOCR vs Tesseract：中文OCR效果更好，PDF先尝试PyMuPDF提取，低文本页面回退OCR
- ChineseRecursiveTextSplitter：中文分隔符优先级 `\n\n → \n → 。→ ！→ ？→ ，`
- zh_title_enhance：chunk携带层级标题上下文，解决独立chunk语义丢失
- chunk_size=250/overlap=50的权衡：精确度vs上下文完整性

### 检索增强策略
- BM25+FAISS互补：关键词精确匹配 + 语义相似度，覆盖不同查询类型
- RRF融合公式：`1/(k+rank)` — 排序尺度不变性，比分数归一化更鲁棒
- CrossEncoder vs Bi-encoder：联合编码(query,doc)对，更深语义交互，先粗排再精排
- score_threshold=0.35过滤：排除低质量匹配，减少上下文噪声
- 可扩展方向：查询改写（同义词扩展）、HyDE（假设文档嵌入）

---

## 6. 验证方案

### 各阶段验证
| 阶段 | 验证方式 |
|------|---------|
| Phase 1 | `docker compose ps` 全部healthy |
| Phase 2 | Python/Java桩代码编译通过，消息序列化测试 |
| Phase 3 | 单元测试：Service层Mock gRPC；集成测试：真实MySQL+MinIO |
| Phase 4 | Python单元测试：加载器/分块器/检索器；集成测试：真实MinIO+FAISS |
| Phase 5 | 端到端：上传文档→等待处理→搜索→RAG对话（curl脚本） |
| Phase 6 | 手动测试：注册→登录→创建KB→上传文件→搜索→对话 |
| Phase 7 | `docker compose up -d` 一键启动，全链路可用 |

### 最终验证脚本
```bash
# 注册 → 创建KB → 上传文件 → 轮询状态 → 搜索 → 对话
# 预期：搜索返回相关结果，对话返回流式回答+来源引用
```
