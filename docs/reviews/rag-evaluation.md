# 实验四：RAG 检索与证据评估复盘

## 实验目标

独立验证本地 Markdown 的 embedding、切片和 Top K 是否能检索正确证据，并把“检索命中”与“生成结论获得支撑”分开评价。

## 最终实现

- 两个版本化 `EmbeddingProfile`：multilingual MiniLM 与 BGE small zh v1.5，均锁定具体 Hugging Face revision、CPU/float32、维度、长度、prefix、归一化和独立缓存目录，且强制 `trust_remote_code=false`。
- `RetrievalProfile` 独立管理字符切片、overlap、Top K、score type 与配置 hash。
- 六篇版本化中文 Markdown、稳定文档 ID、确定性排序和稳定 chunk ID。
- 每次运行重建 LangChain `InMemoryVectorStore`，不依赖持久化向量数据库。
- 至少六个带期望文档 ID/必答问题的查询，保存完整文档排名并计算 Recall@2/4/8 与 MRR。
- MiniLM Recall@4 低于 5/6 时才执行 BGE；只在已执行 Profile 间按 Recall@4、MRR、索引耗时选择。
- `no-rag`、`full-context` 和 `vector` 共用案例、Schema、finalizer；全文上下文有 50,000 字符硬上限。
- `expected_document_ids` 只参与 Recall/MRR 评价，不进入离线答案构造；答案适配器只读取查询和当前 variant 可见的上下文。
- SourceEvidence 同时保存 supporting excerpt、chunk/content hash、文档元数据和 artifact reference。
- RunSummary 保存 embedding、baseline retrieval 与三种 variant 共同生成控制 hash。

## 自动评价与人工评价边界

自动门禁只证明：Source ID 存在、excerpt 是 chunk 子串、content hash 一致、每个必答问题有合法 Finding。任一条件不满足即为 `insufficient_evidence`。摘录是否在语义上真正支持结论由独立人工 Rubric 判断，自动结构通过不代表语义正确。

## 已验证结果

离线固定 embedding 已验证 Profile/hash 分离、稳定 chunk、排名指标、高/低 Recall 两侧门禁、证据校验、必答问题缺失拒答、no-rag 拒答和 vector/full-context 路径。全仓库统一离线门禁为 74 项通过。最新矩阵 run `58e14fef2fd24e1b81c5c70a7deba163` 完成 400/800/1200 × Top K 2/4/8 共 9 组；baseline 中 MiniLM fixed embedding 的 Recall@2/4/8 与 MRR 均为 1.0，因此按门禁跳过 BGE。该 run 同时保存了 embedding 与 baseline retrieval hash。

上述分数只证明测试 embedding 与数据/门禁链路正确，不能用于选择真实默认模型。运行前的默认候选是 `minilm-multilingual-v1`；只有它未达到 Recall@4 ≥ 5/6 时才执行 `bge-small-zh-v1`。真实默认 Profile 必须由以下 pinned 本地模型矩阵决定：

```powershell
uv sync --locked --extra rag
lab rag evaluate --embedding-profile auto --local-embeddings
lab run exp04 --variant no-rag
lab run exp04 --variant full-context
lab run exp04 --variant vector --local-embeddings
```

## RAG 带来的收益

RAG 为结论提供可定位的项目内证据，并允许对知识覆盖进行独立门禁。Profile 与 retrieval 参数分离后，可以解释性能变化来自模型还是切片/Top K。

## 框架增加的复杂度

- 模型 revision、维度、最大长度和缓存必须显式治理。
- 相似度总会返回 Top K，需要额外的充分性门禁。
- 来源结构校验不能替代语义审核。
- 样本只有六个查询，结果仅适用于本项目知识集，不能宣称通用模型排名。

## 阶段结论

最小两步 RAG 对需要项目内事实支撑的工作流有明确价值；它不应被扩张为通用知识库平台。是否采用 BGE、最终 Recall/MRR 和人工支撑分数待统一下载模型与 live 验证后补充。
