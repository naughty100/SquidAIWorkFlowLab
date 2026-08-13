## 1. Profile 与本地依赖

- [x] 1.1 将 Hugging Face、sentence-transformers 等重型依赖配置为 `rag` optional extra
- [x] 1.2 定义完整 `EmbeddingProfile` 与独立 `RetrievalProfile` Schema、规范化序列化和 hash
- [x] 1.3 为 multilingual MiniLM 解析并锁定具体模型 revision SHA，填写维度、长度、CPU、float32、normalize 和空 prefix 配置
- [x] 1.4 为 BGE small zh 解析并锁定具体 revision SHA，填写中文 query instruction、空 document prefix 及完整运行配置
- [x] 1.5 实现 Profile 加载、trust_remote_code 禁用、模型维度/长度校验和独立缓存目录

## 2. 索引与三种上下文策略

- [x] 2.1 创建版本化 Markdown 样本文档、稳定文档 ID 和确定性加载顺序
- [x] 2.2 实现按 RetrievalProfile 切片并生成稳定 chunk ID 的 `InMemoryVectorStore` 重建流程
- [x] 2.3 实现 no-rag、带明确长度上限的 full-context 和 vector 三种 variant
- [x] 2.4 将本地证据规范化为带 supporting excerpt、content hash 和来源元数据的 SourceEvidence

## 3. 检索与支撑评估

- [x] 3.1 创建至少六个带期望文档 ID 和必答问题的检索评估案例
- [x] 3.2 实现逐查询排名、Recall@2/4/8 和 MRR 计算及结果保存
- [x] 3.3 实现 MiniLM Recall@4 小于 5/6 时自动执行 BGE Profile 的门禁
- [x] 3.4 按 Recall@4、MRR、索引耗时生成 Profile 选择结果，未执行的 Profile 不参与优劣结论
- [x] 3.5 实现 Source ID、excerpt 子串、content hash 和必答问题覆盖校验，以及 `insufficient_evidence`
- [x] 3.6 增加固定人工证据支撑 Rubric，并与自动结构结果分栏记录

## 4. CLI、测试与复盘

- [x] 4.1 增加 `lab run exp04` 三种 variant 和 `lab rag evaluate --embedding-profile` 命令
- [x] 4.2 用固定 embedding 测试 Profile/hash、chunk 稳定性、排名指标、证据校验和拒答路径
- [x] 4.3 增加真实本地 embedding 集成标记，验证 revision、维度、Recall 门禁和模型缓存
- [x] 4.4 通过全局门禁并执行完整检索矩阵
- [x] 4.5 完成 `docs/reviews/rag-evaluation.md`，记录默认 Profile 选择与 RAG 价值后再进入下一 change
