# 开发环境部署指南

## 架构

开发模式下，业务代码在 Windows 本地运行（支持热重载/断点调试），基础设施组件在 WSL2 Docker 中运行。

```
┌────────────────────────────────────────────────────────────────┐
│                      Windows 本地                               │
│                                                                 │
│  Vue Dev Server    Java Backend      Python RAG                │
│  localhost:5173    localhost:8080    localhost:50051           │
│       │                 │                  │                    │
│       │    /api 代理     │                  │                    │
│       └────────┬────────┘       gRPC      │                    │
│                │ ◄─────────────────────────┘                   │
└────────────────┼────────────────────────────────────────────────┘
                 │ localhost 端口转发 (WSL2 自动)
┌────────────────┼────────────────────────────────────────────────┐
│                │            WSL2 Docker                         │
│                ▼                                                │
│  ┌──────────────┐  ┌───────┐  ┌───────┐  ┌──────────────┐     │
│  │    Nginx     │  │ MySQL │  │ Redis │  │   MinIO      │     │
│  │   :80        │  │ :3306 │  │ :6379 │  │ :9000/:9001  │     │
│  └──────────────┘  └───────┘  └───────┘  └──────────────┘     │
│                                                                 │
│  ┌────────────────┐  ┌──────────────────┐                      │
│  │ RocketMQ-ns    │  │ RocketMQ-broker  │                      │
│  │ :9876          │  │ :10911           │                      │
│  └────────────────┘  └──────────────────┘                      │
└────────────────────────────────────────────────────────────────┘
```

> WSL2 会自动将容器端口转发到 Windows localhost，因此所有基础设施服务均可通过 `localhost:<port>` 访问。

---

## 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| WSL2 | 任意发行版 | Ubuntu 22.04 推荐 |
| Docker Desktop | 24+ | 启用 WSL2 Integration |
| JDK | 17 | Eclipse Temurin 推荐 |
| Maven | 3.9+ | 或使用 `mvnw` |
| Python | 3.11 | Conda/venv 推荐 |
| Node.js | 18+ | npm 9+ |
| 可用内存 | ≥ 8GB | WSL2 分配建议 4GB |

---

## 第一步：WSL2 环境准备

### 1.1 确保 Docker Desktop 启用 WSL2

Docker Desktop → Settings → Resources → WSL Integration → 勾选你的 WSL 发行版。

### 1.2 在 WSL2 中创建项目目录（可选）

```bash
# 进入 WSL2
wsl

# 如果项目在 Windows 上，通过 /mnt 访问
ls /mnt/d/MyProject/myKnowledgeBase/
```

> 建议直接在 Windows 目录下操作（`/mnt/d/...`），避免文件在 Windows/WSL 之间复制。

---

## 第二步：启动基础设施容器

### 2.1 配置环境变量

在项目根目录复制 `.env.example` 为 `.env`，填入 API Key：

```bash
cp .env.example .env
```

编辑 `.env`，至少修改：

```ini
EMBEDDING_API_KEY=sk-your-key
LLM_API_KEY=sk-your-key
```

其余使用默认值即可。

### 2.2 仅启动基础设施服务

在 WSL2 终端中执行：

```bash
cd /mnt/d/MyProject/myKnowledgeBase

# 只启动基础设施（排除 Python、Java、Nginx 的业务容器）
docker compose up -d mysql redis minio rocketmq-namesrv rocketmq-broker
```

验证：

```bash
docker compose ps
# 预期：mysql/redis/minio/rocketmq-namesrv/rocketmq-broker 状态均为 Up (healthy)
```

### 2.3 验证各服务

```bash
# MySQL
docker compose exec mysql mysql -u root -pmykb123456 -e "SELECT 1"

# Redis
docker compose exec redis redis-cli -a redis123456 PING

# MinIO（浏览器访问 http://localhost:9001，账号 minioadmin / minioadmin123）
curl http://localhost:9000/minio/health/live
```

---

## 第三步：Python RAG 服务

### 3.1 创建虚拟环境

```powershell
# Windows PowerShell
cd D:\MyProject\myKnowledgeBase\rag-service

# 使用 venv
python -m venv venv
.\venv\Scripts\activate

# 或使用 conda
# conda create -n mykb-rag python=3.11 -y && conda activate mykb-rag
```

### 3.2 安装依赖

```powershell
# 配置清华镜像加速（可选）
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装
pip install -r requirements.txt
```

### 3.3 生成 gRPC 桩代码

```powershell
cd D:\MyProject\myKnowledgeBase

python -m grpc_tools.protoc `
  -I.\proto `
  --python_out=.\rag-service\generated `
  --grpc_python_out=.\rag-service\generated `
  .\proto\*.proto
```

### 3.4 配置连接地址

编辑 `rag-service/config/config.yaml`，无需修改（默认值指向 `localhost` 即为 WSL2 容器）：

```yaml
# storage.minio_endpoint 默认为 http://localhost:9000（WSL2 转发）
# embedding.api_base / llm.api_base 按需配置
```

或通过环境变量覆盖：

```powershell
$env:MINIO_ENDPOINT="http://localhost:9000"
$env:MINIO_ACCESS_KEY="minioadmin"
$env:MINIO_SECRET_KEY="minioadmin123"
$env:EMBEDDING_API_KEY="sk-your-key"
$env:LLM_API_KEY="sk-your-key"
```

### 3.5 启动服务

```powershell
cd D:\MyProject\myKnowledgeBase\rag-service
python server.py
```

预期输出：

```
RAG gRPC server starting on port 50051
All services registered. Waiting for requests...
```

---

## 第四步：Java 后端

### 4.1 生成 gRPC 桩代码

```powershell
cd D:\MyProject\myKnowledgeBase\backend

# 使用 Maven 编译（protobuf-maven-plugin 会自动生成桩代码）
mvn compile
```

### 4.2 配置连接地址

编辑 `backend/src/main/resources/application.yml`，确认以下配置（默认值指向 localhost）：

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mykb?useSSL=false&serverTimezone=Asia/Shanghai&characterEncoding=utf8mb4
  data:
    redis:
      host: localhost

minio:
  endpoint: http://localhost:9000

grpc:
  rag-service:
    host: localhost
    port: 50051
```

### 4.3 启动服务

```powershell
cd D:\MyProject\myKnowledgeBase\backend

# 编译并运行
mvn spring-boot:run
```

或使用 IDE：
- **IntelliJ IDEA**：打开 `backend/pom.xml` 作为项目 → 运行 `BackendApplication`
- **VS Code**：安装 Spring Boot 扩展 → Run

### 4.4 验证

```powershell
curl http://localhost:8080/actuator/health
# 预期: {"status":"UP"}
```

---

## 第五步：Vue 前端

### 5.1 安装依赖

```powershell
cd D:\MyProject\myKnowledgeBase\frontend
npm install
```

### 5.2 配置 Vite 代理

编辑 `frontend/vite.config.ts`，确认 API 代理指向本地 Java：

```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',  // Java 后端
        changeOrigin: true,
      },
    },
  },
})
```

### 5.3 启动 dev server

```powershell
npm run dev
```

访问 http://localhost:5173

---

## 第六步：端到端验证

### 6.1 Python gRPC 连通性

```powershell
pip install grpcio-tools
python -c "import grpc; ch = grpc.insecure_channel('localhost:50051'); grpc.channel_ready_future(ch).result(timeout=5); print('OK')"
```

### 6.2 Java → Python gRPC 连通性

启动 Java 后，调用一个依赖 Python 的接口：

```powershell
# 登录获取 token
$body = @{username="admin";password="admin123"} | ConvertTo-Json
$resp = Invoke-RestMethod -Uri http://localhost:8080/api/auth/login -Method Post -Body $body -ContentType "application/json"
$token = $resp.data

# 创建知识库（会触发 Java → Python gRPC）
$kbBody = @{name="测试知识库";description="";vsType="FAISS";embedModel="bge-m3"} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8080/api/kb -Method Post -Body $kbBody -ContentType "application/json" -Headers @{"sa-token"=$token}
```

### 6.3 前端 → Java → Python 全链路

1. 浏览器访问 http://localhost:5173
2. 使用 admin / admin123 登录
3. 创建知识库 → 上传文件 → 搜索 → RAG 对话

---

## 开发工作流

### Python 热重载

修改 `rag-service/` 代码后，`Ctrl+C` 停止 → 重新 `python server.py`。或使用 `watchdog`：

```powershell
pip install watchdog
watchmedo auto-restart --patterns="*.py" --recursive -- python server.py
```

### Java 热重载

使用 Spring DevTools（已支持的 IDE 自动重启）或 `mvn spring-boot:run` 配合 DevTools。

### 前端热重载

Vite 默认支持 HMR，修改代码后浏览器自动刷新。

---

## 服务端口速查表

| 服务 | 开发地址 | 说明 |
|------|----------|------|
| Vue Dev Server | http://localhost:5173 | HMR 热更新 |
| Java Backend | http://localhost:8080 | Actuator: /actuator/health |
| Python gRPC | localhost:50051 | 无 HTTP 端点 |
| MySQL | localhost:3306 | root / mykb123456 |
| Redis | localhost:6379 | 密码: redis123456 |
| MinIO API | http://localhost:9000 | S3 兼容接口 |
| MinIO Console | http://localhost:9001 | 管理后台 |
| RocketMQ ns | localhost:9876 | Name Server |
| RocketMQ br | localhost:10911 | Broker |

---

## 常见问题

### Q: Java 启动报 "gRPC connection refused"

**A**: 确认 Python RAG 服务正在运行且端口 50051 可访问：

```powershell
netstat -an | findstr 50051
# 应显示 LISTENING
```

### Q: 前端请求 API 报 502 或 CORS 错误

**A**: 确认 Java 服务在 8080 端口运行，且 Vite 代理配置正确。不要在开发模式使用 Nginx。

### Q: WSL2 Docker 容器无法从 Windows 访问

**A**: WSL2 默认启用 localhost 端口转发。如果失效：

```powershell
# 重启 WSL2
wsl --shutdown
# 重启 Docker Desktop
```

### Q: 文件上传成功但一直显示"处理中"

**A**: 
1. 检查 Python 服务日志是否有异常
2. 确认 EMBEDDING_API_KEY 已配置且额度充足
3. 确认 MinIO 可访问：浏览器打开 http://localhost:9001

### Q: RocketMQ 占用内存过大

**A**: 开发时可跳过 RocketMQ：

```bash
docker compose up -d mysql redis minio
```

文档通知功能在无 RocketMQ 时可正常使用，仅异步通知失效。

---

## 停止服务

```powershell
# 停止 Python RAG
Ctrl+C

# 停止 Java
Ctrl+C

# 停止 Vue
Ctrl+C

# 停止容器
wsl
cd /mnt/d/MyProject/myKnowledgeBase
docker compose down

# 如需清理数据卷
docker compose down -v
```
