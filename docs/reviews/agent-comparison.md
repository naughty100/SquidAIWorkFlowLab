# 实验三：Agent 对照实验复盘

## 实验目标

在相同案例、fixture、只读工具、`ExecutionBudget` 和公共 `finalize_proposal` 下，对照固定 Python 研究流程与 LangChain Agent，判断自主工具决策是否值得额外的成本、延迟和调试复杂度。

## 最终实现

- `fixed` 使用确定性的 search → read → ResearchPack 流程。
- `agent` 使用 `create_agent`，最终响应显式配置 `ToolStrategy(ResearchPack)`，不依赖自动策略选择。
- Agent 只拥有 `search_web` 与 `read_webpage`，不能写文件或生成最终 Markdown。
- Agent 返回的 source ID 必须来自本次真实 Tool exchange；应用用规范化工具证据覆盖模型回传字段，拒绝虚构来源。
- 两种路径都把 ResearchPack 交给同一个 `finalize_proposal`、证据校验和 renderer。
- 自有预算限制研究模型最多 4 次、总模型 5 次、工具 6 次、搜索 2 次、读取 4 次和 120 秒；LangChain model/tool middleware 是第二道门禁。
- Tool middleware 分别限制 search=2、read=4，不把 ToolStrategy 的结构化返回误计为 Web 工具。
- 工具名与规范化参数形成 SHA-256 指纹，同一指纹第三次出现时不执行工具并终止研究。
- `lab compare exp03` 生成配对 run、分别保留研究覆盖和 Proposal Rubric，并执行 20% 量化差异/1 分 Rubric 差异门禁。

## 评价维度

| 层级 | 指标 |
|---|---|
| ResearchPack | 来源覆盖、工具错误、终止原因 |
| Proposal | 证据可追溯性、证据具体性、可执行性 |
| 执行 | 模型/工具调用、Provider token、耗时、失败类型、可诊断性 |

三次运行只标记为 smoke comparison。若门禁触发，报告状态为 `extension_required`，至少完成十次后才允许输出方向性结论。

## 已验证结果

统一离线门禁覆盖正常研究、预算耗尽、middleware 结束、第三次重复调用、实际证据绑定、虚构来源拒绝、部分证据保留、公共 finalizer 和样本结论约束。当前全仓库离线结果为 74 项通过；fixture 配对能够稳定生成两种 Proposal，但 fixture 不代表真实 Agent 质量和 token 成本。

## LangChain 带来的收益

`create_agent` 提供标准工具循环、结构化响应状态和可组合 middleware，使实验可以观察模型的自主决策，而无需自行维护每轮消息协议。显式 `ToolStrategy` 也让 ResearchPack 契约可检查。

## 框架增加的复杂度

- middleware、自有预算与 Provider usage 必须校准，不能把 framework 计数直接当成唯一成本来源。
- Agent 的结构化终止、预算终止和部分成功需要应用自行归一化。
- 自主搜索需要额外的重复调用检测和更丰富的 Trace。
- 相同 finalizer 可能缩小最终 Proposal 差异，因此必须保留 ResearchPack 层指标。

## 普通代码替代方案

固定函数流程更短、更稳定、工具次数可预测，适合研究步骤已知的任务。Agent 只有在中间证据会实质改变后续搜索方向时才可能产生足够价值。

## 阶段结论

实现证据支持“固定流程是默认方案，Agent 是需要以数据证明收益的实验方案”。尚不能宣称任何一方在真实质量上更优。最终配置 Provider 后执行：

```powershell
lab compare exp03 --mode live --runs 3
# comparison.json 的 extension_triggered 为 true 时：
lab compare exp03 --mode live --runs 10
```

真实 smoke/扩展结果、人工 Rubric 与最终方向性结论待统一 live 验证后补入本文件。

统一验收也可运行 `tests/test_exp03_live.py`：它先执行 3 次 smoke，并在门禁触发时自动执行一份 10 次报告；默认测试不会运行它。
