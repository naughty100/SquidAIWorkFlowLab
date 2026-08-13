# LangGraph 暂停、检查点与恢复

LangGraph 的价值不只是把函数画成图，而是显式管理 State、Node、Edge、条件循环、interrupt 和 checkpoint。人工选择节点应从开头立即调用 interrupt，之前不能写文件或执行外部服务，因为恢复时该节点会从头重放。

SQLite checkpointer 使用 thread_id 作为持久化游标。每次 CLI 调用仍应创建新的 run_id；恢复同一工作流复用 thread_id，并在 RunSummary 中关联两者。进程关闭后重建 SQLite 连接和 Graph，使用 Command(resume=...) 可以继续暂停中的线程。

Graph state 只保存 JSON 可序列化的领域数据、状态码、轮次和 artifact reference，不能保存客户端、数据库连接或完整网页正文。研究补充和质量修订都要有明确上限；节点失败恢复语义应先通过集成测试记录，再决定是否提供公开 retry 命令。
