## Context

实验一解决结构化结果，本 change 开始接入外部能力。研究任务需要先搜索再读取页面，单轮 Tool Calling 不足；但直接进入 Agent 会掩盖工具协议、预算和终止控制，因此先实现应用拥有循环控制权的有限研究执行器，并保留固定 Python 流程作为对照。

## Goals / Non-Goals

**Goals:**

- 用相同工具实现固定流程和最多三轮的手工 Tool Calling 循环。
- 支持模型单轮发出多个 Tool Call，并按输出顺序逐个执行。
- 用统一预算、`ResearchPack` 和 `finalize_proposal` 控制比较变量。
- 将网页正文外置为可重建的内容寻址 artifact。

**Non-Goals:**

- 不使用 `create_agent`、并行 Tool 执行、写文件工具或开放式无限循环。
- 不让 Tool 或模型决定任意本地路径。
- 不在本阶段引入 RAG 或 checkpoint。

## Decisions

### 工具边界

只暴露 `search_web(query, max_results<=5)` 和 `read_webpage(url, max_chars<=12000)`。工具以相同 Schema 对接 fixture 与 Tavily；mode 在运行开始时固定。所有错误归一化为带 code、message、retryable 的 Tool 结果，且每个 Tool Call ID 都获得对应 ToolMessage。

### 受控循环和多调用

每轮模型可返回零个或多个 Tool Call。应用按模型给出的顺序校验和执行，不并发；单项失败后继续同批后续调用。若 deadline 或预算在批次中耗尽，剩余调用不执行，但逐个返回 `budget_exceeded` ToolMessage，使消息协议完整。模型不再请求工具时提前结束；三轮后解除工具绑定并进入 finalizer。

### 统一预算

`ExecutionBudget` 同时维护最大值、当前计数和 monotonic deadline。研究阶段最多 4 次模型调用，公共 finalizer 预留第 5 次；工具最多 6 次，其中搜索 2 次、读取 4 次，总时长 120 秒。任何执行路径都只能通过预算对象调用模型或工具。

### 研究结果和公共终结

固定流程与受控循环都只产出 `ResearchPack`，其中包含问题、发现和规范化来源。公共 `finalize_proposal` 使用同一 Prompt、显式结构化机制和校验逻辑生成 `ProposalBundle`，再由调用方保存。这样后续 Agent 也能复用同一路径。

### 网页 artifact 外置

`read_webpage` 的清洗正文写入 `artifacts/web/{content_hash}.json.gz`。模型仍获得受长度约束的正文，但 Trace 序列化时将 ToolMessage 中的正文替换为 artifact reference；事件只记录 URL、hash、长度、短预览和调用 ID。SourceEvidence 的 excerpt 必须来自对应 artifact。

## Risks / Trade-offs

- [顺序执行增加延迟] → 第一版优先可观察性和确定顺序；只有复盘证明并发收益必要时再单独设计。
- [Tavily 或网页内容不稳定] → 默认使用版本化 fixture，live 结果保存为 artifact 并记录抓取时间。
- [预算耗尽导致缺少最终输出] → 在研究阶段强制预留 finalizer 的一次模型调用；若 Provider 传输仍失败则明确记录失败。
- [完整网页可能包含敏感或恶意文本] → 限制字符数、内容类型和 artifact 路径，Tool 保持只读，并在 Prompt 中标记网页为不可信数据。

## Migration Plan

在实验一复盘完成后加入工具、研究 Schema、预算和 exp02 CLI。现有 exp01 不改行为。回滚时移除 exp02 注册与 Tavily 依赖，保留通用 artifact store。

## Open Questions

无。Tool 并发和其他搜索 Provider 明确留到后续证据支持时再讨论。
