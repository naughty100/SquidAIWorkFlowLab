# structured-output-comparison Specification

## Purpose

规定三种结构化输出路径的公平对照、能力门禁、重试、指标和可复盘产物。

## Requirements

### Requirement: 三个结构化输出 Variant 使用公共契约
系统 SHALL 为 `prompt-parse`、`sdk-native` 和 `langchain-native` 使用相同的 `IdeaBrief` 输入、TopicOptions 输出 Schema、case version 和 Prompt 语义。

#### Scenario: 对同一案例运行三个 Variant
- **WHEN** 用户针对同一 case 依次运行三个 variant
- **THEN** 三次运行 SHALL 记录相同的输入 hash、输出 Schema hash 和模型参数

### Requirement: Native 对照使用相同底层机制
`sdk-native` 与 `langchain-native` MUST 使用同一个已解析的具体结构化机制。

#### Scenario: 共同机制为 Tool Calling
- **WHEN** resolved method 为 `tool_calling`
- **THEN** SDK 和 LangChain variant SHALL 都使用相同 Schema 的强制 Tool Calling，而不得由 LangChain 自动选择

### Requirement: LangChain 必须显式指定结构化机制
所有 `with_structured_output` 调用 MUST 显式传入 resolved method。

#### Scenario: 构建 LangChain 结构化模型
- **WHEN** 系统初始化 `langchain-native`
- **THEN** 调用配置 SHALL 包含具体 method，且不得省略该参数

### Requirement: 不支持的 Native Variant 可诊断
当不存在双方共同 supported 的原生机制时，系统 SHALL 将 native variant 记录为 `unsupported`，同时允许 `prompt-parse` 继续运行。

#### Scenario: 所有原生机制不可用
- **WHEN** 能力报告中 JSON Schema、Tool Calling 和 JSON Mode 均非 supported
- **THEN** native variant SHALL 不发起模型请求并说明原因，prompt-parse SHALL 仍可执行

### Requirement: 传输与 Schema 指标分离
系统 SHALL 分别计算传输成功率和成功响应中的 Schema 合法率。

#### Scenario: 一次限流和四次合法响应
- **WHEN** 五次尝试中一次因 429 最终失败，另外四次返回合法 Schema
- **THEN** transport success rate SHALL 为 4/5，schema validity rate among successes SHALL 为 4/4

### Requirement: 重试上限一致
三个 variant MUST 使用相同 timeout、最多两次传输重试和最多一次 Schema 失败后的额外生成。

#### Scenario: 连续结构校验失败
- **WHEN** 初次响应和唯一一次 Schema 重试都无法通过校验
- **THEN** 运行 SHALL 失败并保存两次校验错误，不得继续请求

### Requirement: 结构化实验结果可复盘
每次 exp01 运行 SHALL 保存输入、合法结果或结构化错误、resolved method、调用统计和 Prompt hash。

#### Scenario: 查看运行摘要
- **WHEN** 用户执行 `lab runs show RUN_ID`
- **THEN** 系统 SHALL 展示 variant、状态、resolved method、传输与 Schema 指标，并隐藏敏感配置
