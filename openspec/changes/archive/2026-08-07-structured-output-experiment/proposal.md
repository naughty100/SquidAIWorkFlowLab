## Why

在进入 Tool Calling 和 Agent 前，需要用同一底层结构化机制公平比较纯 Prompt、底层 SDK 和 LangChain 封装，确认 LangChain 实际减少了哪些解析、校验和错误处理工作。

## What Changes

- 增加内容选题的公共输入与输出 Schema，以及固定案例和 Prompt。
- 实现 `prompt-parse`、`sdk-native`、`langchain-native` 三个实验 variant。
- SDK native 与 LangChain native 强制使用相同的已探测结构化机制，禁止 LangChain 自动选择。
- 分别统计传输成功率和成功响应中的 Schema 合法率。
- 增量增加 `lab run exp01` 和 `lab runs show`，并保存结构化实验产物与复盘数据。

## Capabilities

### New Capabilities

- `structured-output-comparison`: 规定三种结构化输出路径的公平对照、显式机制选择、校验、指标和失败行为。

### Modified Capabilities

无。

## Impact

- 依赖 `bootstrap-lab` 提供的配置、能力报告、Trace 和 artifact 基座。
- 新增实验一领域 Schema、Prompt、案例、CLI variant 和离线/在线测试。
- 不引入 Tool、Agent、RAG 或 LangGraph。
