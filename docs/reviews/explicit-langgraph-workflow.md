# 实验五：显式 LangGraph 工作流复盘

## 实验目标

用一条“选题—研究—提案—质检”显式 StateGraph 验证状态、条件循环、人工中断、SQLite checkpoint、跨进程恢复和失败恢复是否产生普通函数流程不具备的价值。

## 最终实现

Graph 拓扑如下：

```text
analyze_input → generate_topics → wait_for_topic_selection(interrupt)
→ plan_research → collect_evidence(Web + fixed RAG) → assess_evidence
→ [最多两轮研究] → finalize_proposal → quality_check
→ [最多两轮修订] → persist_artifacts
```

- `WorkflowState` 仅包含 JSON 可序列化领域数据、状态码、轮次和 artifact reference。
- `wait_for_topic_selection` 的第一个动作就是 `interrupt()`，之前不记录 Trace、不写文件、不调用外部服务。
- SQLite checkpointer 由应用启动层持有；`run_id` 标识单次命令，`thread_id` 是持久化游标。
- `graph resume` 使用 `Command(resume=topic_id)`；恢复前先纯校验 topic ID，非法输入不推进 checkpoint。
- 初始 mode 写入 checkpoint；使用不同 mode 恢复会在 checkpoint 变化前被拒绝。
- `graph state` 连续读取并比较 checkpoint/state hash，确保只读。
- checkpoint commit、pending writes、节点开始/结束、interrupt、resume 和条件路由都有可关联 Trace。
- Graph 研究路径只调用固定 Web 流程和 RAG，不调用 exp03 `create_agent`。
- CLI 有 `resume` 与 `state`，明确不注册未验证的 `graph retry`。

## 已验证结果

离线集成测试已证明：

- interrupt 后关闭并重建 Graph/SQLite 连接，可用原 thread 恢复；恢复 run 与初始 run 不同。
- 非法 topic ID 不改变 checkpoint ID 或 state hash。
- interrupt 节点重放不会生成外部 artifact。
- 注入一次性节点失败后，可使用官方同 thread checkpoint 调用继续；pending writes 与重放节点留在 Trace。
- 研究两轮后产生 evidence warning；修订两轮后保存 `needs_review`。
- `workflow-state.json` 保存最终 `succeeded`/`needs_review`，不保留上一节点的临时状态。
- checkpoint 包含 artifact reference，但不含网页完整正文或 Agent 事件。

全仓库统一离线门禁为 74 项通过。另以三个独立 CLI 进程完成 fixture start/resume/state：thread `7f4bf56ba1924790a362c537a0be247c` 的 start run `0a6fd8a46294496aadfe48250be8724e` 在 interrupt 暂停，resume run `718a3fa2fafe4df19c34b18f02882d2b` 完成 Proposal，state run `2f203c7fa94846abbe2b61d719ce5834` 只读返回同一最终 checkpoint。

## LangGraph 带来的收益

普通函数可以表达顺序步骤，但跨进程 interrupt/resume、持久化游标、历史 checkpoint 和失败后继续需要大量自建协议。LangGraph 在这些场景提供了明确且可测试的运行语义，尤其适合等待时间远长于单次进程生命周期的人工决策。

## 框架增加的复杂度

- interrupt 节点会从头重放，因此副作用边界必须重新设计。
- state schema、checkpoint 兼容性、run/thread 区分和连接生命周期都成为长期契约。
- 节点级 Trace、pending writes 和业务 artifact 是三套不同的持久化视角，需要关联 ID。
- 对无暂停、无恢复、步骤固定的短任务，普通 Python 函数仍更简单。

## 产品化信号

若真实用户经常需要在选题或审批处暂停数小时、跨设备恢复，Graph 的价值明确；若流程通常一次完成，固定函数足够。本阶段不据此选择生产数据库，也不开放 retry 命令。

最终配置 Provider 后应执行一次真实跨进程运行：

```powershell
lab run exp05 --mode live
# 关闭当前进程，再使用输出的 thread_id/topic_id：
lab graph resume THREAD_ID --topic-id TOPIC_ID --mode live
lab graph state THREAD_ID
```

真实模型 Proposal、失败恢复观察与最终产品化判断待统一 live 验证后补充。

统一验收中的 `tests/test_exp05_live.py` 会创建三个独立 CLI 进程完成 start、resume 和 state，从而避免把同一 pytest 进程内重建 runtime 误当成真实跨进程验证；默认测试不会运行它。
