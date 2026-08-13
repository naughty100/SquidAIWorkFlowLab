## 1. Agent 研究路径

- [x] 1.1 使用既有模型和工具创建 exp03 Agent，并显式配置 `ToolStrategy[ResearchPack]`
- [x] 1.2 将实际模型与工具调用接入统一 `ExecutionBudget`，同时配置 LangChain 调用限制 middleware
- [x] 1.3 实现工具名与规范化参数指纹，并在第三次相同调用时终止研究
- [x] 1.4 确保 Agent 只返回 ResearchPack，并调用既有 `finalize_proposal` 生成最终产物

## 2. 公平比较与报告

- [x] 2.1 增加 `lab run exp03` 的 fixed/agent variant，共用案例、fixture、模型、预算、工具和 finalizer
- [x] 2.2 增加 `lab compare exp03 --case --runs` 的配对执行和运行关联
- [x] 2.3 统计 ResearchPack 来源覆盖、Proposal 人工 Rubric、调用数、token、耗时、失败和可诊断性
- [x] 2.4 实现 3 次 smoke 标记，以及 20% 量化差异或 1 分 Rubric 差异触发至少 10 次扩展比较的门禁

## 3. 测试与限制验证

- [x] 3.1 用可控 Agent 响应测试正常研究、预算耗尽、middleware 先终止和部分 ResearchPack 保留
- [x] 3.2 测试第三次重复搜索/读取不执行，并产生可诊断终止原因
- [x] 3.3 测试 fixed 与 agent 都调用同一个 finalizer，且最终生成配置完全一致
- [x] 3.4 测试比较报告在样本不足或触发扩展门禁时不得给出确定性优劣结论

## 4. 实验复盘

- [x] 4.1 通过全局 lint、类型、锁文件和离线测试门禁
- [ ] 4.2 执行至少三次 fixed/agent live smoke comparison，并在触发门禁时扩展至至少十次
- [x] 4.3 完成 `docs/reviews/agent-comparison.md`，分别记录研究质量和最终质量后再进入下一 change
