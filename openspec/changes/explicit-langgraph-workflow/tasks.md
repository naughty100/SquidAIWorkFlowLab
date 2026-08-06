## 1. Graph 状态与持久化

- [ ] 1.1 增加 LangGraph Graph API 和 SQLite checkpointer 依赖及忽略的本地数据库目录
- [ ] 1.2 定义仅包含 JSON 可序列化领域数据、artifact reference、状态码和轮次计数的 WorkflowState
- [ ] 1.3 实现 checkpointer 生命周期、独立 run ID/thread ID 生成和 RunSummary 关联

## 2. 节点与拓扑

- [ ] 2.1 实现输入分析、选题生成、研究问题、固定 Web/RAG 收集和资料充分性节点
- [ ] 2.2 实现从节点开头调用 interrupt 的纯 `wait_for_topic_selection` 及独立选择校验
- [ ] 2.3 实现调用公共 `finalize_proposal` 的提案节点、质量检查、修订和产物保存节点
- [ ] 2.4 配置资料不足最多两轮、质量修订最多两轮的条件边和上限状态
- [ ] 2.5 确保网页正文只保存到 artifact store，Graph state 和 SQLite checkpoint 仅持有引用

## 3. CLI 与可观察性

- [ ] 3.1 增加 `lab run exp05`，首次执行创建独立 run/thread 并在 interrupt 时显示候选 topic ID
- [ ] 3.2 增加 `lab graph resume THREAD_ID --topic-id`，每次恢复创建新 run 并继续原 thread
- [ ] 3.3 增加只读 `lab graph state THREAD_ID`，显示最新 checkpoint、下一节点、interrupt payload 和历史摘要
- [ ] 3.4 为节点开始、结束、interrupt、resume、条件路由和 checkpoint 写入可关联的 Trace 事件
- [ ] 3.5 确认 CLI 不注册 `graph retry`，并在文档中说明本阶段的失败恢复边界

## 4. 恢复与循环测试

- [ ] 4.1 测试暂停后关闭并重建进程级 Graph/SQLite 连接，再用原 thread 恢复
- [ ] 4.2 测试非法 topic ID 不推进工作流且不破坏已有 checkpoint
- [ ] 4.3 测试 interrupt 节点重放不会重复外部副作用或产生重复持久化结果
- [ ] 4.4 注入一次性节点失败，按官方 checkpoint 调用方式继续同一 thread，并记录重放节点与 pending writes 行为
- [ ] 4.5 测试研究和修订循环严格封顶，分别产生证据警告与 `needs_review`
- [ ] 4.6 测试 Graph 研究路径不调用 `create_agent`，且 checkpoint 不包含网页正文

## 5. 最终验证与阶段复盘

- [ ] 5.1 通过全局 lint、类型、锁文件和离线测试门禁
- [ ] 5.2 用真实案例完成一次跨进程 interrupt/resume live 运行并保存最终 Proposal
- [ ] 5.3 完成 `docs/reviews/explicit-langgraph-workflow.md`，比较固定函数流程与 Graph 的复杂度、恢复价值和产品化信号
