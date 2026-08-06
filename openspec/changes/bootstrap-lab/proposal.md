## Why

当前仓库只有产品企划，尚无可重复运行的 Python 工程、模型能力探测和实验记录基础。先建立最小实验基座，才能让后续实验在相同环境、配置与追踪口径下开展，同时避免一次性建设尚未使用的框架能力。

## What Changes

- 初始化 Python 3.12、`uv`、`src` layout、测试、静态检查和锁文件管理。
- 增加配置加载、敏感字段过滤、Mock Model 和最小 Run Recorder。
- 增加 `lab doctor [--live]`，以 `supported`、`unsupported`、`unknown` 三态探测模型能力。
- 增加内容寻址的运行 artifact 存储，为后续网页正文与 Trace 分离提供基础。
- 明确本阶段不实现实验运行、Tool、RAG、Agent、LangGraph 和完整 CLI。

## Capabilities

### New Capabilities

- `lab-runtime-foundation`: 规定本地 Python 实验工程、配置安全、运行元数据、Trace 与 artifact 的最小基座。
- `provider-capability-probe`: 规定 OpenAI-compatible 模型接口的能力探测、三态结果和显式结构化机制解析。

### Modified Capabilities

无。

## Impact

- 新增 Python 项目配置、依赖锁文件、CLI 入口和 `src/ai_workflow_lab` 基础包。
- 新增本地运行数据目录和 Git 忽略规则。
- 引入 `uv`、Pydantic、Typer、pytest、ruff、pyright 及 OpenAI-compatible 客户端依赖。
- 后续所有 change 以本 change 完成并复盘为前置条件。
