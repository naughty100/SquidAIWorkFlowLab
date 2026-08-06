## ADDED Requirements

### Requirement: Agent 仅负责生成 ResearchPack
Agent SHALL 使用既有只读研究工具收集资料并返回 `ResearchPack`，不得直接写文件或生成最终 Markdown。

#### Scenario: Agent 正常完成研究
- **WHEN** Agent 判定已有足够资料并结束工具循环
- **THEN** 其结构化结果 SHALL 通过 ResearchPack 校验后交给公共 `finalize_proposal`

### Requirement: Agent 显式使用结构化策略
Agent 的最终 ResearchPack MUST 显式使用 `ToolStrategy`，不得依赖 `create_agent` 自动选择 response format。

#### Scenario: 创建 Agent
- **WHEN** 系统构建 exp03 Agent
- **THEN** Agent 配置 SHALL 明确包含 `ToolStrategy[ResearchPack]`

### Requirement: Fixed 与 Agent 共用终结路径
Fixed 和 Agent variant SHALL 使用完全相同的 `finalize_proposal`、最终 Prompt、结构化机制、证据校验和 Markdown renderer。

#### Scenario: 比较两个研究 Variant
- **WHEN** 两个 variant 分别生成 ResearchPack
- **THEN** 系统 SHALL 将二者交给同一 finalizer，比较报告不得混用 variant 专用最终生成逻辑

### Requirement: Agent 受统一预算约束
Agent 研究阶段 SHALL 最多使用四次模型调用，并与 finalizer 合计不超过五次模型调用、六次工具、两次搜索、四次读取和 120 秒。

#### Scenario: Middleware 尚未触发但自有预算耗尽
- **WHEN** Agent 请求一次会超过 `ExecutionBudget` 的调用
- **THEN** 自有预算 SHALL 拒绝调用并使 Agent 以预算耗尽状态结束

#### Scenario: 自有预算尚未触发但 Middleware 拒绝
- **WHEN** LangChain middleware 先达到配置上限
- **THEN** 系统 SHALL 记录 middleware 终止原因和自有计数，不得继续调用

### Requirement: 重复工具调用必须终止
系统 SHALL 以工具名和规范化参数建立调用指纹，并在同一指纹第三次出现时终止 Agent 研究。

#### Scenario: 第三次重复搜索
- **WHEN** Agent 第三次请求完全相同参数的 `search_web`
- **THEN** 系统 SHALL 不执行该搜索，并保存重复调用错误及此前收集的 ResearchPack

### Requirement: 比较运行控制实验变量
`lab compare exp03` MUST 对配对运行使用相同 case、fixture version、模型配置、Prompt hash、预算、工具和 finalizer。

#### Scenario: 生成三次 Smoke Comparison
- **WHEN** 用户未指定 runs 数量
- **THEN** 系统 SHALL 对 fixed 与 agent 各执行三次配对运行，并明确将结果标记为 smoke comparison

### Requirement: 明显差异触发扩展比较
当任一核心量化指标差异至少为 20%，或人工 Rubric 平均差异至少为 1 分时，结论流程 MUST 要求至少十次固定案例运行。

#### Scenario: 三次运行显示明显成本差异
- **WHEN** smoke comparison 中 Agent 平均 token 比 fixed 高至少 20%
- **THEN** 报告 SHALL 标记需要扩展比较，且不得输出确定性的优劣结论

### Requirement: 比较报告同时保留研究和最终质量
比较结果 SHALL 分别记录 ResearchPack 来源覆盖、最终 Proposal Rubric、调用数、token、耗时、失败类型和可诊断性。

#### Scenario: Finalizer 降低最终结果差异
- **WHEN** 两个 variant 的 Proposal 分数接近但 ResearchPack 来源覆盖不同
- **THEN** 报告 SHALL 同时展示两个层级的指标，不得只展示最终 Proposal 分数

