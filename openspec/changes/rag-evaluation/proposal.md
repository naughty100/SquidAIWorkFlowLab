## Why

在把本地知识接入最终工作流前，需要先独立验证 embedding、切片和 Top K 是否能检索到真正相关的证据，并区分“检索命中”与“答案获得支撑”两个问题。

## What Changes

- 增加完整、可哈希、可复现的 `EmbeddingProfile` 与独立 `RetrievalProfile`。
- 使用本地 Hugging Face embedding、Markdown 文档和 `InMemoryVectorStore` 实现最小两步 RAG。
- 比较无 RAG、全文上下文和向量检索三种路径。
- 计算 Recall@K 与 MRR，保存逐查询排名，并按门禁决定是否评估第二个 embedding profile。
- 增加 `supporting_excerpt`、`content_hash` 和逐问题证据校验；证据不足时明确返回 `insufficient_evidence`。
- 增量增加 `lab rag evaluate`。

## Capabilities

### New Capabilities

- `rag-retrieval-evaluation`: 规定 embedding/retrieval profile、索引、检索指标、证据支撑校验和 RAG 对照实验。

### Modified Capabilities

无。

## Impact

- 依赖前序 change 的领域 Schema、结构化输出、Trace 和 artifact 能力。
- 增加可选的本地 embedding 依赖、样本文档和检索评估案例。
- 不引入持久化向量数据库或 Agentic RAG。
