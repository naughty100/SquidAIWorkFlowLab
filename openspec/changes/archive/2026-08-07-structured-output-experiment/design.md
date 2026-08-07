## Context

本 change 以 `bootstrap-lab` 的配置、能力报告和 Trace 为前置。实验要回答的是 LangChain 对结构化输出的封装价值，因此必须控制底层模型、Prompt、Schema、请求参数和原生机制，避免把“不同 Provider 能力”误当成“SDK 与 LangChain 差异”。

## Goals / Non-Goals

**Goals:**

- 用同一内容选题任务比较 `prompt-parse`、`sdk-native`、`langchain-native`。
- 强制 SDK native 与 LangChain native 使用同一具体结构化机制。
- 分开记录传输可靠性与 Schema 可靠性，并保留可复盘的输入、输出和错误。

**Non-Goals:**

- 不比较多个模型或 Provider。
- 不引入 Tool、Agent、RAG、流式结构化消费或自动语义评分。
- 不因某一原生能力不支持而静默换用另一机制。

## Decisions

### 公共领域契约

输入使用 `IdeaBrief`，输出使用包含三个 `TopicOption` 的 Pydantic Schema。Topic ID、运行时间和文件路径由代码补齐。三个 variant 使用相同 case version、Prompt 内容、模型参数和最大重试。

### 三种 variant

`prompt-parse` 使用底层 SDK 请求普通文本，Prompt 要求只返回 JSON，再由应用提取、解析和校验。`sdk-native` 直接使用 SDK 对应的 JSON Schema、强制 Tool Calling 或 JSON Mode。`langchain-native` 调用 `with_structured_output`，并强制传入由能力解析器得到的具体 `method`。

当配置为 `auto` 时，运行开始前解析一次并冻结具体机制；当用户显式指定机制时，状态必须为 supported，否则以配置错误结束。若不存在共同原生机制，两个 native variant 记录 `unsupported`，实验仍可执行 `prompt-parse`。

### 公平性与重试

SDK 和 LangChain 客户端都设置相同 timeout、最多 2 次传输重试和相同 token 上限。成功收到 Provider 响应后再统计 Schema 校验；Schema 失败最多额外请求一次。所有重试和最终失败进入 Trace。

### 指标与输出

每个 variant 分别记录 `transport_success_rate` 和 `schema_validity_rate_among_successes`，不把 429 或网络超时计为 Schema 失败。`lab run exp01` 产生标准运行目录；`lab runs show` 展示摘要、resolved method 和错误分类，不输出秘密。

## Risks / Trade-offs

- [OpenAI-compatible 服务对 native 参数实现不完整] → 依赖三态 probe；unknown 不参与自动选择，显式失败而非伪装成框架问题。
- [LangChain 内部仍可能增加消息或转换 Schema] → 保存逻辑请求、实际响应和 Schema hash，在复盘中明确这正是封装差异的一部分。
- [五次 live 样本过少] → 仅作为学习实验基线，不据此作统计性强结论。

## Migration Plan

先确认 `bootstrap-lab` 已实现并通过复盘，再新增 exp01 模块、案例、Prompt 和 CLI 子命令。回滚时删除 exp01 注册与相关依赖，不修改基座数据格式。

## Open Questions

无。具体 native method 由运行时能力报告决定，而不是在设计阶段假定。
