## Context

仓库当前只有产品企划、README 和 OpenSpec 配置，没有 Python 工程或既有兼容约束。本 change 是所有后续实验的最小基座，面向单用户、本地运行和默认离线测试；它需要提供可复现环境、安全配置、可检查的 Provider 能力以及足够调试的运行记录，同时避免提前引入实验二之后的抽象。

## Goals / Non-Goals

**Goals:**

- 建立 Python 3.12 与 `uv` 管理的可复现工程和统一 `lab` CLI 入口。
- 用三态能力模型描述 OpenAI-compatible 服务的实际支持情况。
- 提供可扩展但保持最小的 Run Recorder、JSONL Trace 和内容寻址 artifact store。
- 确保默认命令和测试不访问外部服务，敏感配置不落盘。

**Non-Goals:**

- 不实现任何正式实验、Tool、Agent、RAG、LangGraph 或产品界面。
- 不建设多 Provider 抽象、远程可观测平台、数据库或通用插件系统。
- 不在本 change 中实现网页抓取，只提供通用 artifact 写入能力。

## Decisions

### Python 工程与依赖

使用 Python 3.12、`src/ai_workflow_lab` layout 和 `uv.lock`。运行依赖放入项目依赖，测试与静态检查放入 development dependency group；CI 通过 `uv lock --check` 后使用 `uv run --locked`，避免检查过程隐式改锁文件。CLI 使用 Typer，只注册本阶段存在的 `doctor` 命令。

### 配置和秘密处理

通过 Pydantic Settings 读取 `.env` 和进程环境，核心键为 `AI_BASE_URL`、`AI_API_KEY`、`AI_MODEL`、timeout 与 retry。配置对象向日志序列化前统一经过字段名与值双重过滤；只记录 `base_url_host`，不记录完整 URL 查询参数、Key、Authorization 或 Cookie。

### 三态能力探测

每项能力以 `supported | unsupported | unknown` 表示，另附 `reason` 和探测错误。只有基础 Chat 已成功且服务明确拒绝功能时才能判为 `unsupported`；认证、网络、限流、跳过或含糊响应均为 `unknown`。结构化机制解析器可按 `json_schema → tool_calling → json_mode` 选择首个 supported 项，但只返回具体枚举值供调用方显式传入。

### 本地追踪与 artifact

每次命令生成独立 `run_id` 和运行目录。`events.jsonl` 使用带 `trace_schema_version` 的追加事件；`summary.json` 保存 Git commit、Python 版本、lock hash、模型与能力信息。Artifact store 以规范化内容 SHA-256 为文件名，写入 gzip JSON，并返回相对 `artifact_ref`。大文本在 Trace 中只保留引用、哈希、长度和短预览。

### 默认离线

`lab doctor` 只检查本地配置、依赖和目录；只有 `--live` 才创建真实客户端和发出探测请求。Mock Model 使用固定响应，供后续实验注入，不模仿完整 Provider 实现。

## Risks / Trade-offs

- [能力探测可能产生少量费用] → 仅在 `--live` 下执行，展示将进行的探测项，并保存探测时间避免误读旧报告。
- [错误过滤遗漏秘密] → 对常见敏感字段做拒绝列表，对实际 Key 值做二次替换，并加入泄漏回归测试。
- [过早抽象 Recorder] → 只定义 run、event、artifact 三个稳定概念；Tool 和 Graph 专用字段由后续 change 增量加入。
- [Python 3.12 与本机默认版本不同] → 由 `.python-version` 和 `uv` 管理项目解释器，不依赖系统 Python。

## Migration Plan

这是空仓库初始化，无数据迁移。若初始化失败，可删除本 change 新增的 Python 工程文件和未提交的 `data/outputs` 后重新执行；不影响现有企划文档。

## Open Questions

无。后续 Provider 具体支持能力以 `doctor --live` 的实际报告为准。
