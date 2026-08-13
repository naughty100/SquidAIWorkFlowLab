## Context

此前来源来自 Web；本 change 引入少量本地 Markdown 文档，独立验证检索与答案支撑。目标是学习两步 RAG 的适用边界，而不是建设知识库平台，因此使用本地 embedding 和内存向量存储，同时完整记录模型与检索配置以保证结果可解释。

## Goals / Non-Goals

**Goals:**

- 用版本化 Profile 复现 embedding、切片和 Top K 组合。
- 分开测量检索排名质量与生成结论的证据支撑。
- 比较 no-rag、full-context 和 vector 三种上下文策略。
- 对无足够证据的输入给出明确状态，不伪造引用。

**Non-Goals:**

- 不实现持久化向量数据库、PDF 管道、混合检索、reranker 或 Agentic RAG。
- 不把自动结构校验包装成语义正确性判断。
- 不预设某个 embedding 模型在本项目数据上最佳。

## Decisions

### 完整 EmbeddingProfile

Profile 以受版本控制的配置文件保存，包含 profile ID、provider、model name、具体 revision SHA、device、dtype、trust_remote_code、归一化、batch size、query/document prefix、distance metric、预期维度、最大序列长度、cache dir 和 profile version。加载后验证实际维度与配置，并把完整配置 hash 写入 RunSummary。默认 CPU、float32、`trust_remote_code=false`、cosine 和归一化向量。

先评估 multilingual MiniLM；若 Recall@4 小于 5/6，再使用带中文查询 instruction 的 BGE small zh profile。最终按 Recall@4、MRR、索引耗时排序选择默认 Profile。

### RetrievalProfile 与索引

切片、重叠和 Top K 不放入 EmbeddingProfile，而由独立 RetrievalProfile 管理并哈希。实验矩阵使用 400/60、800/120、1200/180 和 Top K 2/4/8。文档加载、切片和 `InMemoryVectorStore` 在每次实验中确定性重建。

### 两层评估

检索层保存每个 query 的候选文档排序，计算 Recall@2/4/8 和 MRR。支撑层要求每个 ResearchFinding 引用合法 SourceEvidence，excerpt 可在对应 chunk 中定位且 hash 一致；任一必答问题无合法证据时返回 `insufficient_evidence`。语义支撑由固定人工 Rubric 审核。

### 三种上下文策略

`no-rag` 不提供本地文档，`full-context` 在明确长度上限内提供全部样本文档，`vector` 只提供 Top K 片段。三者使用同一生成 Schema、Prompt 主体和 finalizer，差异仅为上下文来源。

离线确定性答案适配器只根据查询与可见上下文选择证据，检索案例中的 `expected_document_ids` 只用于 Recall/MRR 评价，不得进入答案构造。三种 variant 共同记录生成控制 hash，Profile 评估摘要同时保存 embedding 与 baseline retrieval 配置 hash。

## Risks / Trade-offs

- [模型首次下载慢或失败] → 作为带 `rag` extra 的显式集成步骤，离线单元测试使用固定 embedding；缓存目录不提交 Git。
- [相似度总会返回 Top K] → 不以“返回非空”判定充分性，结合标注检索指标和逐问题证据门禁。
- [六个问题样本较少] → 只作为项目内门禁和调参基线，复盘不得宣称通用模型排名。
- [Profile 浮动导致结果不可复现] → revision 必须是具体 commit SHA，配置与 hash 随运行记录。

## Migration Plan

在 Agent 对照复盘后安装 `rag` extra、加入样本文档、Profile 和 exp04 命令。向量索引不持久化，无数据迁移；回滚可删除模型缓存和 exp04 代码而不影响既有实验。

## Open Questions

无。第二个 Profile 是否执行由 Recall@4 门禁自动决定。
