# 系统架构文档

## 总体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户浏览器 (Vue 3)                            │
└──────────┬──────────────────────────────────────────────────────────┘
           │ HTTP/SSE
           v
┌─────────────────────────────────────────────────────────────────────┐
│                     Nginx (:80)                                      │
│  - 静态文件服务 (Vue dist)                                            │
│  - /api/* → Java Backend (:8080)                                    │
│  - /api/chat/* → Java Backend (SSE, buffering off)                  │
└──────────┬──────────────────────────────────────────────────────────┘
           │
           v
┌─────────────────────────────────────────────────────────────────────┐
│                   Java Backend (Spring Boot 3.2)                     │
│  - saToken 统一鉴权                                                    │
│  - 知识库/文档 CRUD                                                    │
│  - MinIO 文件存储                                                      │
│  - MySQL 元数据管理                                                    │
│  - Redis 缓存                                                         │
│  - RocketMQ 通知                                                      │
│  - gRPC Client → Python                                              │
└──────────┬──────────────────────────────────────┬────────────────────┘
           │ gRPC (50051)                         │ JDBC / HTTP
           v                                      v
┌──────────────────────────┐  ┌──────────────────────────────────────┐
│  Python RAG Service       │  │  基础设施服务                          │
│  - 文档解析 (OCR/PDF/etc)  │  │  - MySQL (:3306) - 元数据             │
│  - 分块 (ChineseRecursive) │  │  - MinIO (:9000) - 文件存储           │
│  - 嵌入 (OpenAI API)       │  │  - Redis (:6379) - 缓存               │
│  - FAISS 向量存储          │  │                                       │
│  - BM25+向量混合检索       │  │                                       │
│  - CrossEncoder 重排序     │  └──────────────────────────────────────┘
│  - LLM 流式生成            │
└──────────────────────────┘
```

## 数据流

### 文件上传流程
```
1. 用户选择文件 → Vue前端
2. POST /api/doc/upload (multipart) → Nginx → Java
3. Java saToken鉴权 → MinioClient.putObject() → MinIO
4. Java INSERT kb_file (status=UPLOADED) → MySQL
5. Java gRPC DocumentService.UploadDocument(minio_key) → Python
6. Python MinIO下载 → 解析 → 分块 → 嵌入 → FAISS存储
7. Python 返回结果 → Java 更新 kb_file.status=COMPLETED
8. RocketMQ 发布 "document.processed" 通知
```

### 搜索流程
```
1. 用户输入查询 → Vue前端
2. POST /api/search/hybrid → Nginx → Java
3. Java saToken鉴权 → gRPC SearchService.HybridSearch → Python
4. Python: BM25检索 + FAISS向量检索 → RRF融合 → 过滤 → [重排序]
5. Python 返回 Top-K 结果 → Java 包装 → JSON响应
```

### RAG对话流程
```
1. 用户提问 → Vue前端 (SSE EventSource)
2. GET /api/chat/rag?query=...&kbId=... → Nginx → Java
3. Java saToken鉴权 → gRPC ChatService.RagChat (streaming) → Python
4. Python: 检索 → 构建Prompt → LLM流式生成
5. Python yield chunks → Java SseEmitter.send() → 前端渲染
6. 最终chunk包含来源引用 sources
```


