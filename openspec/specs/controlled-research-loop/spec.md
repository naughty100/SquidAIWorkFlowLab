# controlled-research-loop Specification

## Purpose

定义固定研究流程和应用掌控的受控 Tool Calling 循环，用一致的预算、证据与终结器产出可追溯提案。

## Requirements

### Requirement: 研究工具保持只读且模式固定

系统 SHALL 仅向模型暴露 `search_web` 和 `read_webpage`，并在运行开始时固定为 fixture 或 live 实现。

#### Scenario: 默认运行研究实验

- **WHEN** 用户未显式指定 live 模式
- **THEN** 两个工具 SHALL 只读取版本化 fixture，且不得访问网络或写入模型指定路径

### Requirement: 受控循环最多执行三轮

应用 SHALL 拥有 Tool Calling 循环的终止权，最多执行三个 Tool Round，并在模型不再请求工具时提前结束。

#### Scenario: 第二轮已返回最终研究结果

- **WHEN** 模型在第二轮不产生 Tool Call
- **THEN** 应用 SHALL 停止研究循环并把当前 ResearchPack 交给 finalizer

#### Scenario: 达到第三轮仍请求工具

- **WHEN** 第三轮结束后模型仍请求新工具
- **THEN** 应用 SHALL 停止绑定工具，并使用已有证据进入最终结构化生成

### Requirement: 单轮多个 Tool Call 顺序执行

单个模型响应包含多个 Tool Call 时，系统 MUST 按响应中的顺序逐个校验与执行，第一版不得并发。

#### Scenario: 一轮请求读取多个页面

- **WHEN** 模型依次返回三个 `read_webpage` 调用
- **THEN** 系统 SHALL 按原顺序执行，并为每个 call ID 生成且仅生成一个 ToolMessage

#### Scenario: 批次中某一调用失败

- **WHEN** 顺序批次中的第二个调用返回可归一化错误且预算仍充足
- **THEN** 系统 SHALL 为第二个调用返回错误 ToolMessage，并继续执行第三个调用

### Requirement: 预算耗尽保持消息协议完整

研究路径 MUST 通过统一 `ExecutionBudget` 限制为最多五次模型调用、六次工具、两次搜索、四次读取和 120 秒，其中一次模型调用为 finalizer 保留。

#### Scenario: 批次执行中工具预算耗尽

- **WHEN** 执行部分 Tool Call 后剩余调用会超过预算
- **THEN** 剩余每个调用 SHALL 获得带原 call ID 的 `budget_exceeded` ToolMessage，且不得实际执行

#### Scenario: 研究尝试消耗预留调用

- **WHEN** 研究阶段准备使用为 finalizer 保留的最后一次模型调用
- **THEN** 预算 SHALL 拒绝该研究调用并保留 finalizer 配额

### Requirement: 固定与受控研究输出统一

固定 Python 流程和受控 Tool Calling SHALL 都输出同一 `ResearchPack` Schema，并使用相同来源规范化与错误模型。

#### Scenario: 两个 Variant 完成研究

- **WHEN** fixed 与 tool-call variant 对同一案例完成来源收集
- **THEN** 两个结果 SHALL 都能不经 variant 专用转换传入公共 finalizer

### Requirement: 所有研究路径共用 Proposal Finalizer

`finalize_proposal` SHALL 使用同一 Prompt、显式结构化机制、证据校验和确定性 Markdown renderer 处理所有 ResearchPack，且不得直接写文件。

#### Scenario: Fixed 和 Tool Calling 使用相同 ResearchPack

- **WHEN** 两种路径向 finalizer 提交内容相同的 ResearchPack
- **THEN** finalizer SHALL 使用相同模型请求配置和校验路径，调用方再负责保存返回的 ProposalBundle

### Requirement: 网页正文独立存储

`read_webpage` 的完整清洗正文 MUST 存入 `artifacts/web/{content_hash}.json.gz`，不得直接写入 `events.jsonl`。

#### Scenario: 记录包含网页正文的 ToolMessage

- **WHEN** Trace Recorder 序列化模型实际收到的网页 ToolMessage
- **THEN** 事件 SHALL 使用 artifact reference、hash、长度和短预览替代正文，并能通过 artifact 重建输入

### Requirement: Tool 错误结构化返回

参数错误、空结果、超时、限流和服务端错误 SHALL 转换为包含 code、message 与 retryable 的 Tool 结果。

#### Scenario: Live 搜索超时

- **WHEN** Tavily 搜索超过配置 timeout
- **THEN** 模型 SHALL 收到对应 call ID 的结构化 timeout ToolMessage，Trace SHALL 记录错误而不泄露认证信息
