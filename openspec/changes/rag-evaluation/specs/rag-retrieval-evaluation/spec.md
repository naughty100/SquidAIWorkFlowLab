## ADDED Requirements

### Requirement: EmbeddingProfile 完整且可复现
每个 EmbeddingProfile MUST 包含 profile ID、provider、model name、具体 revision SHA、device、dtype、trust_remote_code、normalize、batch size、query/document prefix、distance metric、预期维度、最大序列长度、cache dir 和 profile version。

#### Scenario: 加载完整 Profile
- **WHEN** 用户选择一个 embedding profile 运行实验
- **THEN** 系统 SHALL 校验所有必需字段、使用具体 revision，并把完整配置 hash 写入 RunSummary

#### Scenario: 模型维度不匹配
- **WHEN** 实际 embedding 维度与 Profile 的 expected dimensions 不一致
- **THEN** 系统 SHALL 在建立索引前失败并记录配置错误

### Requirement: RetrievalProfile 与 EmbeddingProfile 分离
切片器、chunk size、overlap、Top K、score type 和 profile version MUST 由独立 RetrievalProfile 管理和哈希。

#### Scenario: 只修改 Top K
- **WHEN** 用户从 Top K 4 切换到 Top K 8 而 embedding 配置不变
- **THEN** embedding profile hash SHALL 保持不变，retrieval profile hash SHALL 改变

### Requirement: 本地索引确定性重建
系统 SHALL 从版本化 Markdown 文档、选定 Profile 和固定文档排序构建 `InMemoryVectorStore`，不得依赖持久化向量数据库。

#### Scenario: 相同输入重复建索引
- **WHEN** 文档、Profile 和依赖版本均未变化
- **THEN** 两次构建 SHALL 产生相同 chunk ID、document metadata 和配置 hash

### Requirement: 检索评估计算 Recall 与 MRR
`lab rag evaluate` SHALL 对至少六个带期望文档 ID 的查询保存完整排名，并计算 Recall@2、Recall@4、Recall@8 和 MRR。

#### Scenario: 期望文档位于第四名
- **WHEN** 某查询的第一个相关文档排名为 4
- **THEN** 该查询对 Recall@4 贡献一次命中，对 MRR 贡献 1/4

### Requirement: Embedding 模型选择遵循门禁
系统 SHALL 先评估 multilingual MiniLM Profile；仅当其 Recall@4 小于 5/6 时，再评估 BGE small zh Profile，并按 Recall@4、MRR、索引耗时排序选择默认 Profile。

#### Scenario: 首个 Profile 达到门禁
- **WHEN** multilingual MiniLM 的 Recall@4 至少为 5/6
- **THEN** 系统 SHALL 将其保留为默认候选，并不得把未执行的第二个 Profile 描述为更差

#### Scenario: 首个 Profile 未达到门禁
- **WHEN** multilingual MiniLM 的 Recall@4 小于 5/6
- **THEN** 系统 SHALL 执行 BGE Profile 评估并按既定排序规则记录选择结果

### Requirement: 每项发现必须绑定可验证证据
每个 ResearchFinding MUST 引用至少一个合法 Source ID；对应 SourceEvidence 的 `supporting_excerpt` MUST 能在规范化 chunk 或 artifact 中定位，且 `content_hash` MUST 匹配。

#### Scenario: 模型生成不存在的摘录
- **WHEN** supporting excerpt 无法在引用内容中精确定位
- **THEN** 系统 SHALL 将该证据判为无效，并不得把相关 Finding 计为已支撑

### Requirement: 证据不足时明确拒绝
当没有合法证据，或任一必答研究问题没有至少一个有效 ResearchFinding 时，系统 SHALL 返回 `insufficient_evidence`。

#### Scenario: Top K 返回内容但不覆盖必答问题
- **WHEN** Retriever 返回四个 chunk，但其中一个必答问题没有合法引用
- **THEN** 结果 SHALL 为 `insufficient_evidence`，不得因 Top K 非空而判为充分

### Requirement: 三种 RAG Variant 控制生成变量
`no-rag`、`full-context` 和 `vector` SHALL 使用相同案例、生成 Schema、Prompt 主体、模型参数和 finalizer，差异仅限提供的本地上下文。

#### Scenario: 执行 RAG 对照
- **WHEN** 用户针对同一案例运行三个 variant
- **THEN** RunSummary SHALL 记录各自上下文策略、Profile hash、来源数量、token 和证据状态

### Requirement: 自动与人工评估边界清晰
自动测试 SHALL 校验排名、引用、excerpt 和 hash；证据在语义上是否支持结论 MUST 由固定人工 Rubric 记录。

#### Scenario: 结构合法但语义可疑
- **WHEN** 引用结构和 hash 都合法但审阅者认为摘录不支持结论
- **THEN** 自动结果 SHALL 保持结构通过，人工 Rubric SHALL 独立记录为不支持

