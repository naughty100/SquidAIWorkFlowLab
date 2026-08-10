## 1. 研究领域与工具

- [x] 1.1 定义 `ResearchBrief`、`SourceEvidence`、`ResearchFinding`、`ResearchPack` 和 `ProposalBundle`
- [x] 1.2 定义 `search_web`、`read_webpage` 参数/结果 Schema 及统一 Tool 错误类型
- [x] 1.3 实现版本化 fixture 工具，并验证默认模式不访问网络
- [x] 1.4 实现 Tavily live 适配、结果数量/正文长度限制、超时和认证信息脱敏

## 2. Artifact 与预算

- [x] 2.1 将网页清洗正文写入 `artifacts/web/{content_hash}.json.gz` 并返回 artifact reference
- [x] 2.2 扩展 Trace 序列化器，使网页 ToolMessage 和模型输入事件只保存引用、hash、长度及短预览
- [x] 2.3 实现带 monotonic deadline、计数器和 finalizer 预留配额的 `ExecutionBudget`
- [x] 2.4 为每次模型/工具调用统一接入预算检查、事件记录和错误归一化

## 3. 两种研究路径与 Finalizer

- [x] 3.1 实现固定 Python 的查询生成、搜索、页面选择、读取和 ResearchPack 组装
- [x] 3.2 实现最多三轮、最多四次研究模型调用的手工 Tool Calling 循环
- [x] 3.3 支持单轮多个 Tool Call 按输出顺序执行，并为失败或预算拒绝的每个 call ID 返回 ToolMessage
- [x] 3.4 实现公共 `finalize_proposal`，统一最终 Prompt、显式结构化机制、证据校验和 Markdown renderer
- [x] 3.5 增加 exp02 fixed/tool-call CLI variant 及按事件类型查看 Tool 轨迹的命令

## 4. 验证与复盘

- [x] 4.1 覆盖 search→read 多轮、单轮多调用顺序、单项失败继续、轮次上限和提前结束
- [x] 4.2 覆盖模型/工具分类预算、deadline、finalizer 配额和批次剩余调用的 budget_exceeded 消息
- [x] 4.3 覆盖网页正文不进入 events.jsonl、artifact 可重建、excerpt 来源和秘密过滤
- [x] 4.4 通过全局门禁并用相同案例运行 fixed/tool-call live 对照
- [x] 4.5 完成 `docs/reviews/controlled-tool-calling.md`，确认工具协议和受控循环结论后再进入下一 change
