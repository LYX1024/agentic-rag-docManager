# RAG 流水线深度解析

## 1. 文档摄入流水线

### 整体流程
```
文件上传(MinIO) → 下载到本地 → 格式解析 → 文本分块 → 标题增强 → 向量嵌入 → FAISS存储
```

### 1.1 多格式文档解析 (LOADER_DICT)

每种文件扩展名对应一个加载器，通过工厂字典模式注册：

| 格式 | 加载器 | 底层技术 | 输出 |
|------|--------|----------|------|
| PDF | pdf_loader | PyMuPDF (fitz) | 每页一个Document |
| DOCX | docx_loader | python-docx | 单个Document |
| PPTX | pptx_loader | python-pptx | 单个Document (Slide N标记) |
| 图片 | image_loader | RapidOCR (rapidocr_onnxruntime) | OCR文本Document |
| TXT/MD/CSV | txt_loader | UTF-8直接读取 | 单个Document |

**扩展方式**: 在 `LOADER_DICT` 添加映射即可支持新格式。

**PyMuPDF PDF解析策略**:
1. 使用 `fitz.open()` 打开PDF
2. 逐页调用 `page.get_text()` 提取文本
3. 如果某页文本 < 50字符（可能为扫描件），回退OCR（预留接口）
4. 每页生成独立Document，携带 `page_number` 元数据

### 1.2 中文递归分块 (ChineseRecursiveTextSplitter)

继承自 LangChain 的 `RecursiveCharacterTextSplitter`，使用中文优化的分隔符优先级：

```
"\n\n" → "\n" → "。" → "！" → "？" → "，" → " " → ""
```

**参数**:
- `chunk_size=250`: 每个块的目标大小（字符数）
- `chunk_overlap=50`: 相邻块的重叠（防止语义断裂）

**为什么250不是750?**: 中文信息密度高，250字符已经包含足够上下文。较小的chunk提高检索精度（减少噪声），overlap保证不丢失跨块语义。

### 1.3 标题增强 (zh_title_enhance)

**问题**: 独立chunk丢失了层级上下文。例如一个chunk内容为"使用Spring Boot 3.2版本"，检索到后不知道这是哪个章节的内容。

**方案**: 从Document元数据中提取标题层级信息，预置到chunk文本前：
```
[第三章 系统架构] > [3.2 后端技术选型] > 使用Spring Boot 3.2版本作为后端框架...
```

这样即使chunk独立存在，也携带完整的层级导航信息。

---

## 2. 检索流水线

### 整体流程
```
用户Query → [BM25关键词检索 + FAISS语义检索] → RRF融合 → 分数过滤 → CrossEncoder重排序 → Top-K结果
```

### 2.1 BM25 关键词检索

**原理**: 基于词频(TF)和逆文档频率(IDF)的经典算法，擅长精确匹配查询。

**中文分词**: 使用 `jieba.lcut_for_search()` 分词，对专有名词、技术术语有良好支持。

**BM25核心公式**:
```
BM25(q, d) = Σ IDF(qi) × (f(qi,d) × (k1+1)) / (f(qi,d) + k1 × (1-b+b×|d|/avgdl))
```
其中 k1=1.5 控制词频饱和度，b=0.75 控制文档长度归一化。

**优势**: 专有名词、代码、编号等不适合语义检索的内容，BM25能精确匹配。

### 2.2 FAISS 语义检索

**原理**: 将query和文档chunk都编码为向量，通过余弦相似度（内积）计算语义相关性。

**流程**:
1. 使用 OpenAI text-embedding-3-small 编码query为1536维向量
2. 在FAISS索引中执行ANN（近似最近邻）搜索
3. 返回与query语义最相似的Top-K chunks

**优势**: 能理解同义词、改写、概念关联。例如"电脑"和"计算机"在BM25中不匹配，但语义检索能关联。

### 2.3 RRF 融合 (Reciprocal Rank Fusion)

**为什么需要融合?**: BM25和FAISS各自有盲区。BM25盲区是语义等价（"电脑"≠"计算机"），FAISS盲区是精确术语匹配。融合两者互补。

**RRF公式**:
```
RRF_score(d) = w_bm25 × 1/(k+rank_bm25(d)) + w_vector × 1/(k+rank_vector(d))
```

默认权重: `w_bm25=0.3, w_vector=0.7, k=60`

**为什么用RRF而不是分数归一化?**: RRF基于排名而非分数，是尺度不变(scale-invariant)的。BM25和FAISS的分数量纲不同，直接归一化容易失真。RRF的1/(k+rank)形式天然消除了量纲差异。

**参数k=60**: 控制高排名和低排名的区分度。k越大，高低排名的权重差异越小（所有d趋于等权）；k越小，高排名优势越明显，但噪声风险增加。

### 2.4 分数阈值过滤

score_threshold默认为0.35。低于此阈值的chunk被认为与query关联太弱，丢弃。

这个值是经验参数，调节的是"宁可漏检 vs 宁可误检"的权衡。0.35偏向宁可漏检（高精度），适合知识库场景（不能给错误信息）。

### 2.5 CrossEncoder 重排序

**Bi-encoder vs CrossEncoder**:
- Bi-encoder (FAISS): query和document分别独立编码，速度快但交互浅
- CrossEncoder: 将(query, document)拼接后联合编码，通过BERT全注意力机制深度交互

**流程**: 粗排（RRF融合取top-10）→ CrossEncoder精排 → 最终top-3。

默认模型: `BAAI/bge-reranker-large`，中文重排序效果SOTA。

**代价**: CrossEncoder是O(n)的（每个候选对都要喂入BERT），所以必须先粗排缩小候选集。

---

## 3. RAG 对话流

### 3.1 Prompt 模板
```
你是一个知识库助手。请基于以下参考资料回答用户的问题。
如果参考资料中没有相关信息，请如实告知。

参考资料：
{context}

用户问题：{query}
```

### 3.2 流式生成
1. 检索top-5 chunks → 拼接为context
2. 构建messages: [system(prompt+context), ...history, user(query)]
3. 调用LLM (gpt-4o-mini, stream=True)
4. 逐token yield给gRPC stream
5. Java端代理gRPC stream → SSE → 前端渲染

### 3.3 来源引用
最终chunk附带完整的SourceDoc列表，包含文件名、chunk索引、score，前端可展开查看。

---

## 4. 可深挖方向

### 4.1 查询改写 (Query Rewriting)
检索前用LLM改写用户query：消除歧义、补充上下文、生成多视角查询。这是提升检索精度最有效的手段之一。

### 4.2 HyDE (Hypothetical Document Embeddings)
让LLM先根据query生成一个"假设答案"，用假设答案的embedding去检索。对于开放域问答特别有效，因为假设答案与真实答案在语义空间更接近。

### 4.3 语义分块 (Semantic Chunking)
替代固定大小分块：计算相邻句子的embedding相似度，在相似度"低谷"处分块。这样每个chunk对应一个语义单元，检索更精准。

### 4.4 父子索引 (Parent-Child Indexing)
小chunk用于检索（精度高），检索到后返回对应的大chunk（上下文全）。解决"想精准检索但需要完整上下文"的矛盾。

### 4.5 自查询检索 (Self-Querying)
用LLM从query中提取结构化过滤条件（如"找2024年关于Spring Boot的文档"→ filter: year=2024, topic=spring_boot），结合向量检索做过滤。

### 4.6 多路召回 + 学习融合
3+条检索路径（向量、BM25、知识图谱、web搜索），用学习排序模型（而非固定RRF权重）融合。
