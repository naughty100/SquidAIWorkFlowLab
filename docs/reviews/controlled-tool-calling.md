# controlled-tool-calling 阶段复盘

## 当前结论

实验二的离线工程路径已经完成：`fixed` 与 `tool-call` 都使用版本化 `career-ai-v1` fixture、相同只读工具 Schema、统一 `ExecutionBudget`、同一 `ResearchPack` 和同一 Proposal finalizer。两条路径能够生成来源相同、可追溯的提案产物。

真实 Provider 对照尚未完成。当前 `.env` 没有 `TAVILY_API_KEY`；最近一次 `deepseek-v4-flash` 能力报告中 Tool Calling 为 `unknown`，JSON Mode 与 JSON Schema 为 `unsupported`。因此现在既无法执行 Tavily live 搜索，也不能安全运行要求显式 Tool Calling 和结构化 finalizer 的完整 live 对照。

## Fixture 对照

2026-08-07 对相同案例执行两个 fixture variant：

| Variant | 状态 | 研究模型调用 | Finalizer 调用 | Tool 调用 | 来源 |
|---|---|---:|---:|---:|---:|
| `fixed` | succeeded | 0 | 1 | 4（1 search + 3 read） | 3 |
| `tool-call` | succeeded | 3 | 1 | 4（1 search + 3 read） | 3 |

固定流程在已知研究步骤下调用更少、行为更确定。受控循环增加了模型规划成本，但验证了 search→read 多轮、单轮多调用、按序执行、单项失败继续、预算拒绝消息以及提前结束协议。fixture 只能验证控制逻辑，不能据此判断 live 研究质量收益。

## 工具协议与安全边界

- 模型只看到 `search_web(query, max_results<=5)` 和 `read_webpage(url, max_chars<=12000)`。
- fixture 与 Tavily live 适配器共享参数、结果和结构化错误 Schema；运行开始后不切换模式。
- `ExecutionBudget` 使用 monotonic deadline，并为 finalizer 保留一次模型调用。
- 每个 Tool Call ID 恰好获得一个 ToolMessage；批次中失败不会阻止预算仍充足的后续调用。
- 网页正文按内容 hash 写入 `artifacts/web/*.json.gz`。Tool 与模型输入事件只保留 artifact reference、hash、长度和预览。
- `SourceEvidence.excerpt` 直接截取对应 artifact 正文；finalizer 会拒绝未知 source ID。
- Tavily 认证使用 Bearer header，错误归一化后不包含认证值。

## 验证结果

- Ruff：通过。
- Pyright strict：通过。
- 离线测试：45 passed，1 个 exp01 live 测试和 1 个 exp02 live 测试默认不执行。
- 两个 fixture CLI variant：通过，并生成 `research-pack.json`、`proposal.json`、`proposal.md`、网页 artifact 与脱敏事件。

## Live 门禁

完成本 change 还需要：

1. 配置 `TAVILY_API_KEY`。
2. 使用明确支持 Tool Calling，且至少支持一种显式结构化输出机制的模型配置档案。
3. 重新执行 `lab doctor --live`，确认能力状态为 `supported`。
4. 对相同 `career-ai-v1` 案例运行 `fixed` 与 `tool-call` live variant，并在本复盘补充运行 ID、预算、工具错误和结果差异。

在上述 live 门禁完成前，不进入 `agent-comparison`。
