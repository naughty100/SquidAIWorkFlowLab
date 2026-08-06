# AI Workflow Lab

AI Workflow Lab 是一个本地运行的 Python 实验项目，用于系统学习、验证和复盘 LangChain、LangGraph 及常见 AI 应用模式。

当前只实现了实验基座：可复现的 Python 环境、安全配置、Provider 能力探测、本地 Trace、内容寻址 artifact 和离线 Mock Model。Tool Calling、Agent、RAG 与 LangGraph 将按各自 OpenSpec change 分阶段加入。

## 环境要求

- Windows、macOS 或 Linux
- [`uv`](https://docs.astral.sh/uv/)
- Git

项目固定使用 Python 3.12。`uv` 会根据 `.python-version` 自动准备兼容解释器，不依赖系统默认 Python。

## 安装

```powershell
uv sync --locked
```

锁文件 `uv.lock` 已提交版本控制。安装或 CI 中应使用 `--locked`，避免运行时隐式改变依赖解析。

## 离线环境检查

```powershell
uv run --locked lab doctor
```

离线 doctor 只检查：

- Python 版本；
- `uv.lock` 是否存在；
- 核心依赖是否可导入；
- output、runtime 和 cache 目录是否存在。

它不会创建模型客户端，也不会访问任何外部网络。所有 Provider 能力会显示为 `unknown`，原因为 `live_probe_not_requested`。

## Live Provider 能力探测

复制 `.env.example` 为本地 `.env`，至少填写：

```dotenv
AI_BASE_URL=https://your-openai-compatible-host/v1
AI_API_KEY=your-local-secret
AI_MODEL=your-model-name
```

然后显式执行：

```powershell
uv run --locked lab doctor --live
```

该命令会产生少量真实模型调用，依次探测 chat、streaming、tool calling、JSON mode 和 JSON schema。能力状态含义：

- `supported`：探测获得符合预期的能力响应；
- `unsupported`：基础 Chat 正常，服务明确拒绝该功能；
- `unknown`：未探测，或因认证、网络、限流、含糊响应而无法判断。

`unknown` 不会被当作 `unsupported`。后续结构化实验只能从明确 supported 的机制中选择。

## 本地数据

```text
data/
├── outputs/   # 每次命令的 summary、events、能力报告和 artifacts
├── runtime/   # 后续 checkpoint 等可再生运行状态
└── cache/     # 后续模型和索引缓存
```

这些目录的运行内容不会提交 Git，仅保留 `.gitkeep`。每次 doctor 会在 `data/outputs/commands/{run_id}` 生成：

- `summary.json`：运行状态和可复现元数据；
- `events.jsonl`：经过脱敏的逻辑事件轨迹；
- `capabilities.json`：Provider 能力报告；
- `artifacts/`：超过内联阈值的大文本 gzip JSON。

## 安全边界

- `.env`、输出、runtime 和 cache 默认忽略；
- API Key、Authorization、Cookie、token、password 和 secret 字段写盘前统一脱敏；
- 实际 API Key 值即使出现在异常或普通文本中也会被二次替换；
- 大文本先脱敏再写入 artifact，避免 JSONL 安全但压缩正文泄密；
- 能力报告只记录 `base_url_host`，不记录完整敏感 URL 或认证头。

本项目仍是个人本地实验工具。不要把包含私人资料的运行目录提交或公开分享。

## 开发门禁

```powershell
uv run --locked ruff check src tests
uv run --locked pyright src tests
uv lock --check
uv run --locked pytest -m "not live"
```

默认测试完全离线。任何可能访问外部网络并产生费用的测试必须使用 `live` marker，并由开发者显式执行。

## OpenSpec 实施顺序

1. `bootstrap-lab`
2. `structured-output-experiment`
3. `controlled-tool-calling`
4. `agent-comparison`
5. `rag-evaluation`
6. `explicit-langgraph-workflow`

每个 change 必须完成实现、离线测试、少量真实验证和中文复盘后，再进入下一个阶段。
