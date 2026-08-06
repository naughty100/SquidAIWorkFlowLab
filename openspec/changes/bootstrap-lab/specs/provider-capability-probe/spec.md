## ADDED Requirements

### Requirement: Provider 能力使用三态表示
系统 SHALL 将每项模型能力表示为 `supported`、`unsupported` 或 `unknown`，并允许附加 reason 与脱敏错误信息。

#### Scenario: 能力成功响应
- **WHEN** Provider 对指定能力探测返回符合预期的语义结果
- **THEN** 系统 SHALL 将该能力标记为 `supported`

#### Scenario: 功能被明确拒绝
- **WHEN** 基础 Chat 已成功且 Provider 明确拒绝某项功能参数
- **THEN** 系统 SHALL 将该功能标记为 `unsupported`

#### Scenario: 探测结论不确定
- **WHEN** 探测因未执行、认证、网络、限流或含糊响应而无法判断
- **THEN** 系统 SHALL 将该能力标记为 `unknown`，不得标记为 `unsupported`

### Requirement: Live 探测必须显式启用
系统 MUST 仅在用户传入 `--live` 时对 OpenAI-compatible endpoint 发起 chat、streaming、tool calling、JSON mode 和 JSON schema 探测。

#### Scenario: 未显式启用 live
- **WHEN** 用户运行 `lab doctor`
- **THEN** 所有需要远程请求的能力 SHALL 标记为 `unknown`，并说明未执行 live probe

### Requirement: 能力报告不得泄露连接秘密
能力报告 SHALL 记录模型、探测时间和 `base_url_host`，但 MUST 不得保存 API Key、认证头或完整敏感 URL。

#### Scenario: 保存 live 能力报告
- **WHEN** live probe 执行完成
- **THEN** 持久化报告 SHALL 可识别目标 host 和模型，同时通过秘密泄漏检查

### Requirement: 结构化机制必须解析为具体值
当调用方请求自动选择结构化输出机制时，解析器 SHALL 按 `json_schema`、`tool_calling`、`json_mode` 顺序返回第一个 supported 的具体机制，且 MUST 跳过 unknown 与 unsupported。

#### Scenario: JSON Schema 未知但 Tool Calling 支持
- **WHEN** `json_schema` 为 unknown 且 `tool_calling` 为 supported
- **THEN** 解析器 SHALL 返回 `tool_calling`

#### Scenario: 没有可用机制
- **WHEN** 三种结构化能力均非 supported
- **THEN** 解析器 SHALL 返回无可用机制错误，不得猜测或静默 fallback

### Requirement: 显式机制必须通过能力门禁
用户显式指定结构化机制时，系统 MUST 要求其能力状态为 supported。

#### Scenario: 指定 unknown 机制
- **WHEN** 用户指定的机制状态为 unknown
- **THEN** 系统 SHALL 在模型调用前失败并提示先完成有效探测或更换机制

