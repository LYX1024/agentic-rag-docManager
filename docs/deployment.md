# 部署指南

## 快速启动

### 环境要求
- Docker 24+
- Docker Compose v2+
- WSL2 (Windows) 或 Linux
- 可用内存 ≥ 8GB

### 1. 配置环境变量

编辑项目根目录 `.env` 文件，至少需要配置以下内容：

```bash
# 必须修改的配置
EMBEDDING_API_KEY=sk-your-openai-api-key
LLM_API_KEY=sk-your-openai-api-key

# 可选修改（使用默认值可以直接启动）
MYSQL_ROOT_PASSWORD=mykb123456
REDIS_PASSWORD=redis123456
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
```

> 提示: 嵌入和LLM使用OpenAI兼容API。可以使用任何兼容的API提供商（如阿里百炼、智谱、DeepSeek等），只需修改 `EMBEDDING_API_BASE` 和 `LLM_API_BASE`。

### 2. 下载模型文件（可选）

重排序模型 `bge-reranker-large` 约1.3GB，首次运行时会自动从HuggingFace下载。如网络受限，可预先下载到 `~/.cache/huggingface/hub/`。

### 3. 构建并启动

```bash
# 在项目根目录执行
docker compose up -d --build
```

首次构建需要下载基础镜像和依赖包，约5-15分钟。后续启动只需几秒。

### 4. 验证服务状态

```bash
docker compose ps
```

预期所有8个服务的 STATUS 列均为 `Up (healthy)`。

### 5. 访问系统

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost |
| MinIO控制台 | http://localhost:9001 (minioadmin/minioadmin123) |
| Java Actuator | http://localhost/health |

### 6. 默认管理员账号

- 用户名: `admin`
- 密码: `admin123`

首次启动时由 `UserService.initAdminUser()` 自动创建。

---

## 开发模式

### Python RAG 服务热重载

修改 `rag-service/` 代码后：

```bash
docker compose restart rag-service
```

或挂载源码卷（已默认配置）并添加文件监控。

### Java 后端热重载

修改 `backend/` 代码后需要重新构建：

```bash
docker compose build backend
docker compose up -d --no-deps backend
```

### 前端热重载

```bash
cd frontend
npm run dev
```

Vite dev server 默认端口5173，已配置 `/api` 代理到 nginx(80)。

---

## 使用 MinIO 以外的对象存储

MinIO的S3兼容写法意味着可以无缝切换到其他对象存储：

### 切换到 AWS S3

修改 `.env`：
```bash
MINIO_ENDPOINT=https://s3.amazonaws.com
MINIO_ACCESS_KEY=your-aws-access-key
MINIO_SECRET_KEY=your-aws-secret-key
```

Java端无需改代码（使用MinioClient，它兼容S3协议）。

Python端因为使用boto3，AWS S3天然兼容，只需修改endpoint和credentials。

### 切换到阿里云 OSS

需在Java端替换 MinioClient 为 OSS SDK。Python端继续使用boto3（阿里云OSS支持S3兼容模式）。

---

## 常见问题

### Q: 启动后Java报 "gRPC connection refused"
**A**: rag-service容器启动较慢（需下载模型），等待30秒后重试。可观察 `docker compose logs rag-service`。

### Q: 文件上传后一直处于 UPLOADED 状态
**A**: 检查Python RAG服务日志：`docker compose logs rag-service`。常见原因：
1. EMBEDDING_API_KEY未配置或无效
2. 文件格式不支持（参考LOADER_DICT支持的格式）
3. FAISS索引文件权限问题

### Q: 聊天不返回结果
**A**: 检查LLM API配置：`LLM_API_KEY` 和 `LLM_API_BASE`。查看Java日志：`docker compose logs backend`。

### Q: Windows Docker Desktop 内存不足
**A**: 在 Docker Desktop Settings → Resources 中调整内存限制至少6GB。建议禁用不需要的服务（如rocketmq-namesrv/rocketmq-broker如果暂时不需要通知功能）。

---

## 停止和清理

```bash
# 停止所有容器（保留数据卷）
docker compose down

# 停止并删除所有数据
docker compose down -v
```
