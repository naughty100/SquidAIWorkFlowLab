# controlled-tool-calling 阶段复盘

## 当前结论

实验二已经完成。`fixed` 与 `tool-call` 都使用版本化 `career-ai-v1` fixture、相同只读工具 Schema、统一 `ExecutionBudget`、同一 `ResearchPack` 和同一 Proposal finalizer。两条路径能够生成可追溯的提案产物；同时已通过能力门禁并完成真实 Provider 对照。

2026-08-10 的 `deepseek-v4-flash` live 能力报告（run ID `e05f02c605134541baa30ab734a4c083`）确认 chat、streaming、Tool Calling 与 JSON Mode 均为 `supported`。JSON Schema 被 Provider 拒绝，因此 finalizer 采用已支持的 JSON Mode；这满足显式结构化输出的要求。

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

## Live 对照与结论

2026-08-10 对同一 `career-ai-v1` 案例完成两个 live variant：

| Variant | Run ID | 状态 | 研究模型调用 | Finalizer 调用 | Tool 调用 | 来源 | Tool 错误 |
|---|---|---|---:|---:|---:|---:|---:|
| `fixed` | `466a91516d50493099e9aea7384f6ac0` | succeeded | 0 | 1 | 4（1 search + 3 read） | 3 | 0 |
| `tool-call` | `3fdc5cba959c4c29ac9340015371780a` | succeeded | 3 | 1 | 6（2 search + 4 read） | 3 | 2 |

`fixed` 在已知流程下更省模型和工具调用，并在约 22.75 秒内完成；`tool-call` 因模型自主规划使用了更多查询和读取，在约 45.75 秒内完成。后者的两个工具错误分别是受预算控制拒绝的第三次搜索和一个 Tavily 空正文；二者均已按协议写入对应 ToolMessage，且不妨碍 finalizer 使用三条有效来源产出提案。两次运行都保存了 `research-pack.json`、`proposal.json`、`proposal.md`、网页 artifact 和脱敏事件。

首次 `tool-call` 运行在完成后曾因 Windows GBK 控制台无法输出网页文本的 `∙` 字符而返回非零退出码；运行记录本身为 succeeded。CLI 现已在输出边界转义非 ASCII JSON，避免已完成的运行被控制台编码错误误报为失败。
