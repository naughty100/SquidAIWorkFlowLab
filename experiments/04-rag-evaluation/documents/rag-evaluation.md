# RAG 检索与证据评估

最小 RAG 包含文档加载、切片、embedding、向量索引、Top K 检索、上下文组装和带引用生成。检索返回非空不代表证据充分，因为相似度索引总能返回若干结果。应使用带期望文档 ID 的查询计算 Recall@2、Recall@4、Recall@8 和 MRR，并保存逐查询排名。

EmbeddingProfile 要固定模型名、具体 revision、维度、最大长度、device、dtype、归一化、query/document prefix 和缓存目录；切片大小、overlap 与 Top K 属于独立 RetrievalProfile。两种 Profile 分开 hash，修改 Top K 不应改变 embedding hash。

证据层要求每项发现引用合法 Source ID，supporting excerpt 必须能在规范化 chunk 中定位且 content hash 一致。任一必答问题没有有效发现时，状态应为 insufficient_evidence。结构校验与语义支撑必须分栏记录，后者由人工 Rubric 判断。
