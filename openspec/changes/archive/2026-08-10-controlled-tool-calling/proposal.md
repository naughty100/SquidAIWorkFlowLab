## Why

单轮 Tool Calling 无法完成“先搜索、再读取网页”的真实研究任务，需要一个由应用掌控终止条件和预算的有限循环，作为固定流程与后续开放 Agent 的中间对照层。

## What Changes

- 增加只读的 `search_web` 与 `read_webpage` 工具，支持 fixture 和显式 live 模式。
- 实现最多三轮的受控 Tool Calling，支持单轮多个 Tool Call，第一版按输出顺序执行。
- 引入统一 `ExecutionBudget`，限制模型、工具、搜索、读取次数和整体 deadline。
- 实现固定 Python 研究流程，并让两种研究方式统一产出 `ResearchPack`。
- 实现公共 `finalize_proposal`，固定流程与受控循环共用最终生成、校验和 Markdown 渲染。
- 将网页清洗正文存入独立压缩 artifact，Trace 只保存引用、哈希和短预览。

## Capabilities

### New Capabilities

- `controlled-research-loop`: 规定固定研究流程、受控多轮 Tool Calling、顺序多调用、预算、网页 artifact 和统一提案终结行为。

### Modified Capabilities

无。

## Impact

- 依赖 `structured-output-experiment` 的显式结构化输出与 `bootstrap-lab` 的追踪能力。
- 新增 Tavily live 适配、Mock 工具 fixture、研究领域模型和 Tool 事件查询。
- 不使用 `create_agent`，不开放写文件工具，不并发执行 Tool Call。
