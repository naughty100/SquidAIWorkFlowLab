## Context

前一 change 已提供固定流程、受控工具循环、统一预算、`ResearchPack` 和公共 finalizer。本 change 只替换研究编排方式，用 `create_agent` 观察模型自主决定搜索与读取的收益和风险，不能让 Agent 使用不同的最终提案生成路径。

## Goals / Non-Goals

**Goals:**

- 在相同输入、工具、预算和 finalizer 下比较固定流程与 Agent。
- 对 Agent 的模型、工具、重复调用和整体时限实施可审计的硬限制。
- 形成可重复的量化指标和人工 Rubric 报告。

**Non-Goals:**

- 不显式设计 StateGraph，不引入多 Agent、长期记忆或 Agentic RAG。
- 不让 Agent 直接生成最终 Markdown 或写文件。
- 不用三次 smoke 结果作统计性强结论。

## Decisions

### Agent 只负责研究

`create_agent` 绑定既有搜索和读取工具，最终响应显式使用 `ToolStrategy[ResearchPack]`。Agent 完成后，其 ResearchPack 必须经过与 fixed variant 完全相同的 `finalize_proposal`。固定流程和 Agent 的运行图因此都可表达为 `research → finalize → persist`。

模型回传的 ResearchPack 不能单凭 Schema 合法就被信任。应用将其中的 source ID 与本次 `TrackedAgentTools` 实际 exchange 绑定，并用工具生成的规范化 SourceEvidence 替换模型字段；不存在于真实工具结果中的来源会使 Agent 以 `invalid_response` 结束。

### 双重预算但单一计量

LangChain middleware 在 Agent 内部阻止超限，自有 `ExecutionBudget` 包装实际模型和工具调用并作为报告的唯一计量来源。Agent 研究阶段最多 4 次模型调用，finalizer 使用预留的第 5 次；最多 6 次工具、2 次搜索、4 次读取和 120 秒。

ToolStrategy 的结构化返回在框架内部也表现为 Tool Call，因此 middleware 只对 `search_web=2` 和 `read_webpage=4` 分别限流，两者合计仍为六次真实研究工具；不使用会误计结构化返回的全局 Tool Call 限制。

### 重复调用控制

以工具名加规范化参数形成调用指纹。同一指纹前两次允许执行并记录；第三次终止 Agent 研究，返回明确的重复调用错误和已收集证据，不无限消耗预算。

### 比较方法

`lab compare exp03` 对同一 case、fixture version、模型配置和 Prompt hash 执行配对运行。先各运行 3 次作为 smoke；若任一核心量化指标差异达到 20%，或人工 Rubric 平均差异达到 1 分，则扩展为至少 10 次固定案例后才记录方向性结论。

统一验收由带 `live` marker 的集成测试执行。只有显式设置 `RUN_LIVE_TESTS=1` 才会产生 Provider/Tavily 调用；测试先执行三次配对，并在 `extension_triggered=true` 时自动追加一份十次配对报告。`LAB_LIVE_ENV_FILE` 可选择与 CLI 相同的 dotenv 配置档案，未设置时沿用 `.env`。

## Risks / Trade-offs

- [create_agent 底层依赖 LangGraph] → 本阶段将其视为不可展开的 Agent runtime，只评估接口表现；显式状态和恢复留到实验五。
- [middleware 与自有预算统计不一致] → 所有真实调用必须经过自有预算包装，middleware 只作为第二道保险，测试校验两者边界。
- [同模型 finalizer 掩盖研究差异] → ResearchPack 和最终 Proposal 都保存，分别评分来源覆盖和最终质量。
- [Agent 可能在预算内仍无法完成] → 保留部分 ResearchPack、失败原因和完整调用轨迹，不伪造成功结果。

## Migration Plan

完成 exp02 复盘后增加 Agent variant 和 compare 命令，不改固定流程与 finalizer 的公开契约。回滚只移除 Agent 注册、middleware 与比较报告，exp02 继续可用。

## Open Questions

无。预算是否放宽由本 change 的复盘结论决定，不在初始实现中动态调整。
