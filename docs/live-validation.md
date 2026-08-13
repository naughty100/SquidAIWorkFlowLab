# 五个实验统一配置与验收

这份手册用于所有实现和离线门禁完成后的最后一次统一验收。默认测试不会访问网络；只有显式设置对应开关才会产生 Provider、Tavily 请求或下载 Hugging Face 模型。

## 1. 准备配置档案

复制 `.env.example`，例如保存为 `.env.acceptance`，填写：

```dotenv
AI_BASE_URL=https://your-openai-compatible-host/v1
AI_API_KEY=your-secret
AI_MODEL=your-model
AI_STRUCTURED_OUTPUT_METHOD=auto
TAVILY_API_KEY=your-tavily-secret
```

所有 `.env.*` 文件均被 Git 忽略。不要把密钥写进命令行、测试参数或报告。

安装核心依赖和 RAG extra：

```powershell
uv sync --locked --extra rag
```

## 2. 建立当前模型能力报告

```powershell
uv run --locked lab doctor --live --env-file .env.acceptance
```

验收要求：Chat 与 Tool Calling 为 `supported`；JSON Schema、Tool Calling 或 JSON Mode 中至少有一个明确 supported 的结构化机制。`unknown` 不视为通过。

## 3. 运行全部 live 验收

PowerShell：

```powershell
$env:LAB_LIVE_ENV_FILE = ".env.acceptance"
$env:RUN_LIVE_TESTS = "1"
$env:RUN_RAG_LIVE = "1"
uv run --locked --extra rag pytest -m "live or rag_live"
```

验收包含五项：

1. 实验一真实 prompt-parse 的传输/Schema 指标分离。
2. 实验二 fixed/tool-call 使用同一真实案例并各生成 Proposal。
3. 实验三先运行 3 次 fixed/agent 配对；若触发 20%/1 分门禁，测试自动再运行 10 次并保存方向性报告。
4. 实验四下载并检查 pinned MiniLM/BGE revision、维度、Recall 门禁和独立缓存。
5. 实验五以三个独立 CLI 子进程执行 live start、resume、state，验证跨进程 SQLite 恢复并保存 Proposal。

实验三可能执行 6 次或 26 次完整 variant 运行，实验五会调用 Tavily 和最终模型。运行前应确认账户配额和费用上限。

## 4. 运行离线总门禁

```powershell
uv run --locked ruff check src tests
uv run --locked pyright src tests
uv lock --check
uv run --locked pytest -m "not live and not rag_live"
cmd /c openspec validate --changes --strict --no-interactive
```

## 5. 记录结果并归档

只有以下证据全部存在时，才能勾选剩余 OpenSpec task：

- live/rag_live pytest 整体通过；
- exp03 smoke comparison 文件存在，若触发扩展则 10 次报告也存在；
- exp05 start/resume/state 三个 run 使用同一 thread，resume run 包含 `proposal.json`、`proposal.md` 和最终 `workflow-state.json`；
- 三份阶段复盘补入真实指标与 run ID；
- OpenSpec strict validation 仍通过。

随后依次归档：

```powershell
openspec archive agent-comparison
openspec archive rag-evaluation
openspec archive explicit-langgraph-workflow
```

归档命令的具体参数以当前安装版本的 `openspec archive --help` 为准；归档前不要手工移动 change 目录。
