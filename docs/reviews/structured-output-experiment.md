# structured-output-experiment 复盘

## 结论

实验一已经建立可重复运行的结构化输出对照。当前主力配置 `deepseek-v4-flash` 在火山方舟 OpenAI-compatible endpoint 上可稳定执行 `prompt-parse`；最近一次能力报告中 JSON Mode 与 JSON Schema 为 unsupported、Tool Calling 为 unknown，因此两个 native variant 均被能力门禁安全跳过，没有产生模型请求。

这不是实验阻塞，而是实验结论的一部分：该 Provider 组合当前需要应用层承担 JSON 提取、Pydantic 校验和一次有上限的 Schema 修复重试。要比较 SDK native 与 LangChain native 的封装差异，需要另行配置一个明确支持共同 native 机制的模型档案。

## 公平性控制

- 三个 variant 共用 `career-transition-v1`、`topic-options-v1`、`IdeaBrief` 和 `TopicOptionsDraft`。
- 输入、Prompt、Schema 分别使用稳定 SHA-256 记录，三个 mock variant 的 hash 相同。
- SDK native 与 LangChain native 均接收冻结后的具体机制；LangChain 的 `tool_calling` 显式映射为 `function_calling`。
- timeout、最大输出 token 和最多两次 SDK 传输重试一致；成功传输后的 Schema 失败最多额外生成一次。
- Topic ID 在 Schema 校验通过后由代码根据位置、标题和角度派生。

## Live 验证

2026-08-06 对当前 `.env` 配置执行五次 `prompt-parse`：

| Run ID | 状态 | 传输 | Schema |
|---|---|---:|---:|
| `355b5a329a1247edb618959ca3e8a178` | succeeded | 1/1 | 1/1 |
| `a72d28e19e7a453c9f5adc91811cc9af` | succeeded | 1/1 | 1/1 |
| `7aece17ead744c3380e4263ae503a690` | succeeded | 1/1 | 1/1 |
| `fdd0b3674a534f5ba7e6f36548e35ea2` | succeeded | 1/1 | 1/1 |
| `cf37a89fd31a4bedac8d6c723ff72f7b` | succeeded | 1/1 | 1/1 |

聚合结果：transport success rate 为 5/5；成功响应中的 Schema validity rate 为 5/5；没有触发 Schema 重试。

Native 能力门禁验证：

| Variant | Run ID | 状态 | 模型调用 |
|---|---|---|---:|
| `sdk-native` | `d5cc3289773841d383d22a81fc824cea` | unsupported | 0 |
| `langchain-native` | `4873499961c9494e94698c11951419d3` | unsupported | 0 |

## 工程观察

`prompt-parse` 需要显式实现 JSON 对象提取、Schema 错误分类与修复 Prompt；这些正是 native 机制和 LangChain 封装可能减少的代码。当前五次样本只能说明该固定案例的 smoke reliability，不能推导模型对任意复杂 Schema 都稳定。

传输指标与 Schema 指标分离后，Provider 超时、429 或认证问题不会被误判成模型格式遵循问题。完整输入、结果、错误和大 Prompt 通过 Run Recorder 保存并脱敏，大文本仍使用外置 artifact。

## 后续

在进入 `controlled-tool-calling` 前，可选地增加一个支持 JSON Schema 或 Tool Calling 的 `.env` 配置档案，各运行至少五次 `sdk-native` 与 `langchain-native`，完成真正的框架封装对照。当前 change 不因外部 Provider 缺少 native 能力而阻塞。
