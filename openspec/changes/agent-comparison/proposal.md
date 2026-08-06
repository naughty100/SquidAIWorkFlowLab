## Why

受控循环完成后，需要在完全相同的输入、工具、预算和最终生成路径下比较固定流程与 Agent，判断自主工具决策是否值得其额外成本和不可预测性。

## What Changes

- 使用 `create_agent` 实现只负责生成 `ResearchPack` 的黑盒 Agent 研究路径。
- Agent 显式使用结构化输出策略，不依赖自动机制选择。
- 固定流程与 Agent 共用工具、`ExecutionBudget` 和 `finalize_proposal`。
- 增加重复工具调用检测、预算双重限制和可比较的运行指标。
- 增加 `lab compare exp03`，先执行三次 smoke comparison，达到差异阈值后扩展到至少十次。

## Capabilities

### New Capabilities

- `agent-orchestration-comparison`: 规定 Agent 研究执行、统一预算、公平对照、重复调用控制和分级比较结论。

### Modified Capabilities

无。

## Impact

- 依赖 `controlled-tool-calling` 提供的工具、`ResearchPack`、预算和公共 finalizer。
- 引入 LangChain `create_agent` 与相关 middleware，但不显式设计 StateGraph。
- 新增比较报告、人工 Rubric 和 Agent 离线模拟测试。
