## Context

前序实验已分别验证结构化输出、固定研究、Agent 和 RAG。本 change 用固定研究流程而非 Agent 构建显式 StateGraph，隔离验证 checkpoint、interrupt、条件循环和恢复能力。运行完全本地，SQLite 保存线程状态，完整网页仍由 artifact store 管理。

## Goals / Non-Goals

**Goals:**

- 实现可暂停选择选题、进程退出后恢复的内容提案工作流。
- 显式展示 State、Node、Edge、条件循环、checkpoint 和历史状态。
- 严格区分 run 与 thread，并限制研究和修订轮次。
- 验证节点失败后的官方 checkpoint 恢复行为。

**Non-Goals:**

- 不把 Agent 放入 Graph，不实现多用户、服务端、时间旅行 UI 或公开 retry 命令。
- 不将网页正文、客户端或连接对象保存到 Graph state。
- 不把 SQLite 视为未来生产数据库选型。

## Decisions

### Graph 拓扑

使用 Graph API 定义：分析输入、生成选题、等待选择、校验选择、制定问题、收集 Web/RAG 证据、判断充分性、生成/终结提案、质量检查、修订和保存产物。研究不足最多补充两轮，质量未通过最多修订两轮；达到上限后分别产生证据警告或 `needs_review`。

### 纯 interrupt 节点

`wait_for_topic_selection` 从节点开头直接调用 `interrupt()`，恢复值返回后只做无副作用的格式校验。选题列表由前一节点写入 state，并在进入等待节点前由 checkpointer 持久化。Trace 对重复进入等待节点使用稳定事件 ID 去重，不在 interrupt 前写文件或调用外部服务。

### State 与 artifact

State 使用 JSON 可序列化的 TypedDict 形态，包含输入、选题、选择 ID、研究问题、SourceEvidence、ResearchPack、Proposal、质量结果、轮次计数和状态码。网页正文只以 `artifact_ref` 出现在 state；SQLite checkpoint 不复制正文。

### Checkpoint、run 与 thread

使用 SQLite checkpointer。初次 `lab run exp05` 创建独立 `run_id` 和 `thread_id`；每次 `graph resume` 创建新 run 并复用 thread。`graph state` 只读展示最新 checkpoint、下一节点、interrupt payload 和历史摘要。

初始 mode 属于持久化工作流配置并写入 state；恢复命令必须使用相同 mode，错误配置在创建新 checkpoint 前被拒绝。最终持久化的 `workflow-state.json` 使用 `persist_artifacts` 将要返回的 `succeeded` 或 `needs_review` 状态，而不是上一节点的临时状态。

统一 live 验收测试使用两个独立 `python -m ai_workflow_lab.cli` 子进程分别执行 start 与 resume，再以第三个子进程只读检查 state。测试只在 `RUN_LIVE_TESTS=1` 时启用，并通过 `LAB_LIVE_ENV_FILE` 把同一 dotenv 档案显式传给三个 CLI 进程；最终检查三个不同 run、同一 thread 以及 Proposal 文件。

### 失败恢复

不暴露 `graph retry`。集成测试通过注入一次性失败节点、重新建立进程级 Graph/checkpointer 并按 LangGraph 官方调用方式继续同一 thread，记录哪些节点重跑及 pending writes 表现。复盘后若确有用户操作价值，再另建 change 设计命令语义。

## Risks / Trade-offs

- [interrupt 恢复会从节点开头执行] → 等待节点保持纯函数式，所有外部副作用放在独立节点并采用幂等写入。
- [checkpoint 膨胀] → State 只保存领域摘要和 artifact reference，限制来源、研究轮次和修订轮次。
- [SQLite 连接生命周期处理不当] → 由应用启动层拥有连接和 checkpointer，节点只接收可序列化 state 与依赖上下文。
- [Graph 与普通函数复杂度难比较] → 保留前序固定流程结果，用相同案例、finalizer、质量 Rubric 和指标复盘。

## Migration Plan

在 RAG 复盘完成后新增 SQLite runtime 目录、Graph 模块和 CLI。首次运行自动创建本地 checkpoint 数据库；该数据库不提交 Git。回滚时停止注册 Graph 命令并删除可再生的本地 checkpoint 文件，不影响既有 run artifacts。

## Open Questions

无。公开失败恢复命令明确不属于本 change。
