## Why

在固定流程、Agent 和 RAG 已分别获得实验结论后，需要用一条显式 StateGraph 验证状态、条件循环、人工中断、进程重启恢复和 checkpoint 是否为真实工作流带来足够价值。

## What Changes

- 以固定研究流程和本地 RAG 组成“选题—研究—提案—质检”显式 Graph。
- 使用 SQLite checkpointer，严格区分一次执行的 `run_id` 与持久化游标 `thread_id`。
- 增加纯等待 `interrupt` 节点、选题恢复、状态查看和 checkpoint 历史摘要。
- 增加最多两轮的资料补充与最多两轮的提案修订条件循环。
- Graph state 仅保存可序列化领域数据和 artifact reference，网页正文不进入 checkpoint。
- 不预设公开 `graph retry` 命令；失败恢复语义仅通过集成测试验证并记录。

## Capabilities

### New Capabilities

- `stateful-content-workflow`: 规定显式 LangGraph 的状态、节点、条件循环、人工中断、SQLite 持久化、恢复与输出行为。

### Modified Capabilities

无。

## Impact

- 依赖 `controlled-tool-calling`、`rag-evaluation` 及公共 finalizer；Agent 不进入 Graph，以隔离变量。
- 引入 LangGraph Graph API 和 SQLite checkpointer 包。
- 增量增加 Graph start、resume、state CLI 与恢复测试。
