# 五个实验 OpenSpec 实现验证报告

验证日期：2026-08-12

本报告按 Completeness、Correctness、Coherence 三个维度，对当前工作树中的五个实验逐条映射 OpenSpec task、requirement、scenario、实现与测试。已归档 change 仍以当前主 spec 和当前代码为准重新检查，不以历史归档状态代替证据。

## Summary

| 实验 | OpenSpec change | Completeness | Correctness | Coherence |
|---|---|---:|---:|---|
| 实验一：结构化输出 | `structured-output-experiment` | 15/15 tasks | 7/7 requirements，7/7 scenarios | Followed，已归档 |
| 实验二：受控 Tool Calling | `controlled-tool-calling` | 18/18 tasks | 8/8 requirements，11/11 scenarios | Followed，已归档 |
| 实验三：Agent 对照 | `agent-comparison` | 14/15 tasks | 8/8 requirements，9/9 scenarios 有离线覆盖 | Followed；live 验收待执行 |
| 实验四：RAG 评估 | `rag-evaluation` | 20/20 tasks | 9/9 requirements，11/11 scenarios 有实现/测试证据 | Followed；真实 embedding 标记待统一运行 |
| 实验五：显式 LangGraph | `explicit-langgraph-workflow` | 21/22 tasks | 10/10 requirements，11/11 scenarios 有离线覆盖 | Followed；live 验收待执行 |

总计 88/90 个实验 task 已完成。剩余两个 task 都是明确延后到统一配置阶段的真实环境验收，不是实现缺口。

## Requirement implementation mapping

### 实验一

- 公共输入、Prompt 与 Schema hash：`src/ai_workflow_lab/exp01/contracts.py:38`。
- 三种 variant 的统一校验、Schema 重试和分母分离：`src/ai_workflow_lab/exp01/execution.py:111`。
- 能力冻结与 unsupported 零调用路径：`src/ai_workflow_lab/exp01/service.py:119`。
- SDK/LangChain 显式 native method：`src/ai_workflow_lab/exp01/backends.py:64`、`src/ai_workflow_lab/exp01/backends.py:127`。
- 场景覆盖：`tests/test_exp01_execution.py:20`、`tests/test_exp01_service.py:12`。

### 实验二

- 顺序多 Tool Call、错误继续、完整 budget message：`src/ai_workflow_lab/exp02/execution.py:107`。
- 最多三轮且应用拥有终止权：`src/ai_workflow_lab/exp02/execution.py:288`。
- finalizer 预留、分类预算与 deadline：`src/ai_workflow_lab/exp02/budget.py:18`。
- 公共 finalizer、引用校验和确定性 Markdown：`src/ai_workflow_lab/exp02/finalizer.py:57`。
- fixture/live 固定工具及正文 artifact：`src/ai_workflow_lab/exp02/tools.py:102`、`src/ai_workflow_lab/exp02/tools.py:198`。
- 场景覆盖：`tests/test_exp02_execution.py:34`、`tests/test_exp02_service.py:33`、`tests/test_exp02_tools.py:16`。

### 实验三

- 显式 `ToolStrategy[ResearchPack]`、模型和具名 Tool middleware：`src/ai_workflow_lab/exp03/agent.py:132`。
- Agent 来源与实际 Tool exchange 绑定，虚构来源拒绝：`src/ai_workflow_lab/exp03/agent.py:218`。
- fixed/agent 公共 finalizer 与失败部分结果：`src/ai_workflow_lab/exp03/service.py:58`。
- 配对运行、3/10 次门禁和分级结论：`src/ai_workflow_lab/exp03/comparison.py:63`。
- 场景覆盖：`tests/test_exp03_agent.py:117`、`tests/test_exp03_agent.py:157`、`tests/test_exp03_service.py:48`。

### 实验四

- 完整且独立哈希的 Embedding/Retrieval Profile：`src/ai_workflow_lab/exp04/domain.py:31`、`src/ai_workflow_lab/exp04/domain.py:64`。
- 固定 revision、维度/长度校验、确定性 chunk 与 InMemoryVectorStore：`src/ai_workflow_lab/exp04/indexing.py:174`、`src/ai_workflow_lab/exp04/indexing.py:231`。
- Recall/MRR、MiniLM→BGE 门禁和只在已执行 Profile 中选择：`src/ai_workflow_lab/exp04/evaluation.py:114`。
- Source ID、excerpt、hash 与必答问题证据门禁：`src/ai_workflow_lab/exp04/service.py:92`。
- 三种 context variant 共用控制 hash，期望文档标签不进入答案构造：`src/ai_workflow_lab/exp04/service.py:150`、`src/ai_workflow_lab/exp04/service.py:222`。
- 场景覆盖：`tests/test_exp04_evaluation.py:42`、`tests/test_exp04_service.py:90`、`tests/test_exp04_live.py:15`。

### 实验五

- 紧凑 JSON `WorkflowState`：`src/ai_workflow_lab/exp05/domain.py:8`。
- 显式节点、边、两轮研究/修订上限：`src/ai_workflow_lab/exp05/graph.py:339`。
- SQLite 生命周期、checkpoint/pending writes Trace 与严格 JSON 状态检查：`src/ai_workflow_lab/exp05/runtime.py:22`、`src/ai_workflow_lab/exp05/runtime.py:134`。
- start/resume 的新 run/同 thread、mode 一致性和 resume 前校验：`src/ai_workflow_lab/exp05/service.py:52`、`src/ai_workflow_lab/exp05/service.py:137`。
- 场景覆盖：`tests/test_exp05_workflow.py:33`、`tests/test_exp05_workflow.py:98`、`tests/test_exp05_workflow.py:160`。

## Verification evidence

- 离线测试：77 passed，5 个显式 live/rag_live 测试未执行；新增的 exp03/exp05 live 测试分别自动执行扩展门禁和真实 CLI 子进程恢复。
- Pyright strict：0 errors，0 warnings。
- `uv lock --check`：104 个 package 的锁文件解析通过。
- OpenSpec strict validation：3 个 active change 全部通过。
- 固定 embedding 完整矩阵：run `58e14fef2fd24e1b81c5c70a7deba163`，9 组 matrix，Recall@2/4/8 与 MRR 均为 1.0；该结果只验证 fixed embedding 管道。
- 独立 CLI 进程 fixture 恢复：thread `7f4bf56ba1924790a362c537a0be247c` 完成 start → resume → read-only state，最终 Proposal 已保存。

## CRITICAL

1. `agent-comparison` task 4.2 未完成：至少三次 fixed/agent live smoke comparison；触发门禁时扩展至至少十次。统一验收测试已经实现，但尚未使用真实配置执行。
2. `explicit-langgraph-workflow` task 5.2 未完成：真实案例跨进程 interrupt/resume live 运行与最终 Proposal。三个独立 CLI 子进程的验收测试已经实现，但尚未使用真实配置执行。

## WARNING

1. `rag_live` 集成测试已经实现，但 pinned MiniLM/BGE 模型尚未在本轮统一配置中下载执行。运行 `RUN_RAG_LIVE=1 uv run --locked --extra rag pytest -m rag_live` 后，才能把真实 revision、维度与缓存证据补入最终复盘。

## SUGGESTION

无。当前建议集中在完成既定 live 验收，不扩张实验范围。

## Final assessment

代码、离线测试、CLI、文档和 OpenSpec 实现已经完整。仍有 2 个 CRITICAL（均为用户明确延后的 live task）和 1 个外部集成 WARNING，因此实验三与实验五尚不能归档；实验四实现已达到归档条件，但建议与其余两项一起完成统一 live 复盘后再归档。
