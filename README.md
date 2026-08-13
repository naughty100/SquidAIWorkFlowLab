# AI Workflow Lab

AI Workflow Lab 是一个本地运行的 Python 实验项目，用于系统学习、验证和复盘 LangChain、LangGraph 及常见 AI 应用模式。

当前已实现全部五个实验：结构化输出、受控 Tool Calling、Agent 公平对照、最小 RAG，以及带 SQLite checkpoint 与人工中断的显式 LangGraph 工作流。所有实验共用可复现环境、安全配置、本地 Trace、内容寻址 artifact 和离线测试基座。

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

实验四需要下载本地 Hugging Face embedding 时安装可选依赖：

```powershell
uv sync --locked --extra rag
```

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

### 多模型配置档案

可以维护多个本地 dotenv 文件，无需复制或覆盖 `.env`。例如：

```text
.env.deepseek
.env.openai
.env.qwen
```

它们与 `.env` 一样填写 `AI_BASE_URL`、`AI_API_KEY` 和 `AI_MODEL`，且都被 Git 忽略。运行时显式选择：

```powershell
uv run --locked lab doctor --live --env-file .env.deepseek
uv run --locked lab doctor --live --env-file .env.openai
```

也可使用短参数 `-e`。未提供 `--env-file` 时仍读取默认 `.env`。操作系统中已设置的同名环境变量优先级高于 dotenv 文件；若要得到可复现的配置档案测试，请避免在终端或系统中设置 `AI_*` 覆盖值。

该命令会产生少量真实模型调用，依次探测 chat、streaming、tool calling、JSON mode 和 JSON schema。能力状态含义：

- `supported`：探测获得符合预期的能力响应；
- `unsupported`：基础 Chat 正常，服务明确拒绝该功能；
- `unknown`：未探测，或因认证、网络、限流、含糊响应而无法判断。

`unknown` 不会被当作 `unsupported`。后续结构化实验只能从明确 supported 的机制中选择。

全部实现完成后的统一 live 验收流程见 [`docs/live-validation.md`](docs/live-validation.md)。测试可通过 `LAB_LIVE_ENV_FILE` 选择同一个 dotenv 档案；只有同时显式设置 `RUN_LIVE_TESTS=1` 或 `RUN_RAG_LIVE=1` 时才会联网、产生费用或下载模型。

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

`summary.json` 还会记录所用 dotenv 配置档案的路径、模型名和 Provider host，但不会记录配置内容或 API Key。

## 实验一：结构化输出

实验一使用同一个内容选题案例，对照三种结构化输出路径：

```powershell
# 默认离线 Mock，不访问网络
lab run exp01 --mode mock --variant prompt-parse
lab run exp01 --mode mock --variant sdk-native
lab run exp01 --mode mock --variant langchain-native

# 显式使用真实 Provider
lab run exp01 --mode live --variant prompt-parse -e .env.deepseek
lab run exp01 --mode live --variant sdk-native -e .env.openai
lab run exp01 --mode live --variant langchain-native -e .env.openai
```

native variant 会读取当前模型最近一次 `doctor --live` 的能力报告，并在调用前将机制冻结为 `json_schema`、`tool_calling` 或 `json_mode`。没有明确 supported 的机制时，运行记录为 `unsupported` 且不会发起模型请求。LangChain 路径始终显式指定对应机制，不使用自动选择。

查看某次运行的脱敏摘要：

```powershell
lab runs show RUN_ID
```

摘要分别展示 `transport_success_rate` 与 `schema_validity_rate_among_successes`；网络或限流失败不会被算作 Schema 失败。每次运行还会保存固定案例版本、输入/Prompt/Schema hash、调用次数、合法结果或校验错误。

## 实验二：受控 Tool Calling

实验二用同一研究案例和公共 finalizer，对照固定 Python 流程与最多三轮、由应用控制终止条件的 Tool Calling 循环：

```powershell
# 默认 fixture；只读版本化 JSON，不访问网络
lab run exp02 --mode fixture --variant fixed
lab run exp02 --mode fixture --variant tool-call

# live 会调用模型和 Tavily，并可能产生费用
lab run exp02 --mode live --variant fixed
lab run exp02 --mode live --variant tool-call
```

live 模式除 `AI_*` 配置外还需要：

```dotenv
TAVILY_API_KEY=your-tavily-key
TAVILY_TIMEOUT_SECONDS=30
```

运行预算最多允许 5 次模型调用、6 次工具调用、2 次搜索、4 次网页读取和 120 秒，其中最后一次模型调用只保留给公共 Proposal finalizer。网页清洗正文保存在 `artifacts/web/{content_hash}.json.gz`，事件日志只保留引用、hash、长度和短预览。

按类型查看脱敏 Tool 轨迹：

```powershell
lab runs events RUN_ID --type exp02.tool
```

## 实验三：Agent 公平对照

Agent 只负责产生 `ResearchPack`，并与 fixed variant 共用工具、预算和公共 finalizer：

```powershell
lab run exp03 --mode fixture --variant fixed
lab run exp03 --mode fixture --variant agent
lab compare exp03 --mode fixture --runs 3
```

三次比较只生成 smoke 结论；达到 20% 量化差异或 1 分 Rubric 差异时，报告会要求至少十次比较。live 模式需要 AI 与 Tavily 配置：

Agent 的结构化来源会与本次实际 Tool exchange 绑定；模型无法通过返回一个 Schema 合法但并未读取过的来源绕过证据边界。

```powershell
lab compare exp03 --mode live --runs 3
lab compare exp03 --mode live --runs 10
```

## 实验四：最小 RAG

对同一知识集运行无 RAG、全文上下文和向量检索：

```powershell
lab run exp04 --variant no-rag
lab run exp04 --variant full-context
lab run exp04 --variant vector
```

默认使用确定性 fixed embedding，以便完全离线测试。真实本地模型会使用锁定的 revision、CPU/float32 和独立缓存：

```powershell
uv sync --locked --extra rag
lab rag evaluate --embedding-profile auto --local-embeddings
lab run exp04 --variant vector --local-embeddings
```

`rag evaluate` 保存逐查询排名、Recall@2/4/8、MRR、Profile 门禁和 400/800/1200 切片 × Top K 2/4/8 的完整矩阵。

评估标注中的期望文档 ID 只用于计算排名指标，不会传给三种上下文 variant 的答案构造路径。运行摘要会保存 embedding、retrieval 和生成控制 hash。

## 实验五：显式 LangGraph 工作流

首次运行创建独立 run/thread，并在人工选题处 interrupt：

```powershell
lab run exp05 --mode fixture
lab graph state THREAD_ID
lab graph resume THREAD_ID --topic-id topic-career-roadmap --mode fixture
```

每次 resume 都创建新 run 但复用原 thread。`graph state` 只读显示最新 checkpoint、下一节点、interrupt payload 和历史摘要。本阶段没有 `graph retry`；节点失败恢复只通过官方 checkpoint 调用集成测试验证。

resume 的 `--mode` 必须与 thread 初始 mode 一致；不一致会在 checkpoint 改变前被拒绝。

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
uv run --locked pytest -m "not live and not rag_live"
```

默认测试完全离线。任何可能访问外部网络并产生费用的测试必须使用 `live` marker，并由开发者显式执行。

## OpenSpec 实施顺序

1. `bootstrap-lab`
2. `structured-output-experiment`
3. `controlled-tool-calling`
4. `agent-comparison`
5. `rag-evaluation`
6. `explicit-langgraph-workflow`

前三个 change 已归档；实验三至五的实现、离线门禁和中文复盘已完成。需要 Provider 密钥或本地 embedding 下载的统一 live 验证仍由对应 OpenSpec 任务跟踪。
