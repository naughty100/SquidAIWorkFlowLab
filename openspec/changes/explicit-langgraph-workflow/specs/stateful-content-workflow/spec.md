## ADDED Requirements

### Requirement: 工作流使用显式 StateGraph
系统 SHALL 通过显式节点和边实现输入分析、选题生成、人工选择、研究计划、Web/RAG 证据收集、充分性判断、提案生成、质量检查、修订和保存。

#### Scenario: 完整工作流通过
- **WHEN** 用户选择选题、证据充分且质量检查通过
- **THEN** Graph SHALL 依次完成必需节点并保存结构化 Proposal 与确定性 Markdown

### Requirement: 人工选择通过纯 Interrupt 节点暂停
`wait_for_topic_selection` MUST 从节点开头调用 `interrupt()`，且 interrupt 前不得执行文件写入、外部调用或其他非幂等副作用。

#### Scenario: 首次进入等待节点
- **WHEN** 选题已经由前一节点写入 checkpoint
- **THEN** 等待节点 SHALL 返回包含候选 topic ID 的可序列化 interrupt payload 并暂停

#### Scenario: 恢复后节点重新开始
- **WHEN** 同一 thread 使用 topic ID 恢复
- **THEN** 等待节点 SHALL 可从开头安全重放，随后只执行无副作用的输入校验

### Requirement: SQLite 持久化支持跨进程恢复
系统 SHALL 使用 SQLite checkpointer 按 thread 保存状态，使进程退出后能够继续等待中的工作流。

#### Scenario: 关闭进程后恢复选题
- **WHEN** 工作流在 interrupt 处暂停、进程关闭并重新启动
- **THEN** 用户 SHALL 能使用原 thread ID 和合法 topic ID 继续后续节点

### Requirement: Run 与 Thread 标识分离
每次 CLI 执行 MUST 创建新的 `run_id`；恢复已有工作流 MUST 复用 `thread_id` 并把新 run 关联到该 thread。

#### Scenario: 同一 Thread 两次恢复
- **WHEN** 用户对同一 thread 执行两次合法的运行调用
- **THEN** 两次调用 SHALL 具有不同 run ID，且 RunSummary 中的 thread ID 相同

### Requirement: Graph State 保持紧凑可序列化
Graph state MUST 只包含 JSON 可序列化的领域数据、状态码、轮次计数和 artifact reference，不得包含客户端、连接对象或完整网页正文。

#### Scenario: 保存网页来源状态
- **WHEN** 研究节点读取网页并生成 SourceEvidence
- **THEN** checkpoint SHALL 保存 evidence 和 artifact reference，但不得复制 artifact 中的完整清洗正文

### Requirement: 资料补充循环有上限
资料不足时 Graph SHALL 最多执行两轮研究；达到上限仍不足时 SHALL 继续生成带证据警告的结果。

#### Scenario: 第二轮后仍缺少必答问题证据
- **WHEN** `research_round` 已达到 2 且充分性检查未通过
- **THEN** Graph SHALL 不再回到研究节点，并在后续结果中标记证据不足

### Requirement: 质量修订循环有上限
质量检查未通过时 Graph SHALL 最多执行两轮修订；达到上限仍未通过时 SHALL 输出 `needs_review`。

#### Scenario: 第二轮修订仍失败
- **WHEN** `revision_count` 已达到 2 且 QualityResult 未通过
- **THEN** Graph SHALL 结束自动修订、保存现有提案并将状态标为 `needs_review`

### Requirement: Graph 状态可以只读检查
`lab graph state THREAD_ID` SHALL 展示最新 checkpoint、下一待执行节点、interrupt payload 和历史摘要，且不得修改线程状态。

#### Scenario: 查看暂停线程
- **WHEN** 用户查看等待选题的 thread
- **THEN** 命令 SHALL 显示候选选题和等待节点，并且前后 checkpoint hash 保持不变

### Requirement: 不提供未验证语义的公开 Retry
本 change MUST 不暴露 `lab graph retry`；节点失败恢复行为 SHALL 通过集成测试使用官方 checkpoint 调用方式验证并写入复盘。

#### Scenario: 节点发生一次性失败
- **WHEN** 集成测试中的节点首次执行失败，随后使用同一 SQLite checkpoint 和 thread 继续
- **THEN** 测试 SHALL 记录实际重放节点、保留状态和 pending writes 行为，而 CLI 帮助中不得出现 retry 命令

### Requirement: Agent 不得进入显式 Graph
Graph 的研究节点 SHALL 使用固定研究流程和本地 RAG，不得调用 exp03 Agent。

#### Scenario: 执行研究节点
- **WHEN** Graph 收集 Web 与本地证据
- **THEN** Trace SHALL 显示确定性研究编排，且不得出现 `create_agent` 执行事件

