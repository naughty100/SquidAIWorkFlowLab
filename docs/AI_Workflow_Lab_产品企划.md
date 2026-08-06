# AI Workflow Lab 产品企划

> 一个用于系统学习、验证和沉淀 LangChain / LangGraph 能力的个人 AI 应用实验项目。  
> 当前阶段不急于建设前端工作台、Java 后端或商业产品，而是先通过一组可运行、可比较、可复盘的实验，判断哪些 AI 工作流真正值得产品化。

---

## 1. 项目概览

### 1.1 项目名称

**AI Workflow Lab**

中文名称可暂定为：

**AI 工作流实验室**

该名称只用于当前探索阶段，不代表未来正式产品名。

### 1.2 项目定位

AI Workflow Lab 是一个本地运行的 Python 实验项目，用于逐步掌握：

- 大模型调用与 Prompt 设计
- 结构化输出
- Tool Calling
- Agent
- RAG
- LangGraph 状态工作流
- Human-in-the-loop
- Checkpoint 与恢复执行
- AI 调用日志、质量评估与成本意识

它不是一个完整产品，也不是 Coze、Dify 的替代品。

当前阶段的核心任务是：

> 用最小可运行实验回答：LangChain 和 LangGraph 分别解决什么问题，什么任务值得采用 AI 工作流，什么任务使用普通代码更合理。

---

## 2. 项目背景

目前已具备较深的前端工程经验，熟悉 React、TypeScript、组件体系、前端性能和工程化，但希望向 **AI 应用全栈工程师** 发展。

现阶段真正需要补足的能力包括：

- Python AI 应用生态
- LangChain / LangGraph
- 模型调用与结构化输出
- Agent 与 Tool Calling
- RAG
- 有状态 AI 工作流
- AI 应用的错误处理、评估和可观测性
- 后续 Java 业务后端与 Python AI Runtime 的协作方式

此前曾尝试直接规划一个包含 React、Spring Boot、Python AI Runtime、工作流 Recipe、内容创作、PRD 和旅行计划的完整系统。

但经过讨论发现，目前尚未验证：

- 哪些工作流真正有持续使用价值
- Recipe 应该是什么形态
- 哪些任务必须使用 LangGraph
- 哪些状态需要持久化
- 是否真的需要前台与后台系统
- 内容创作、PRD 和旅行计划是否共享同一种抽象

因此，本项目先退回技术与使用验证阶段。

---

## 3. 核心目标

### 3.1 第一目标：掌握 AI 工作流基础

通过连续实验掌握：

1. LangChain 基础模型调用
2. 结构化输出
3. Tool Calling
4. Agent 执行机制
5. RAG
6. LangGraph 状态、节点与边
7. 人工中断与恢复
8. Checkpoint
9. 节点失败处理
10. 工作流执行记录

### 3.2 第二目标：判断技术适用边界

每个实验都必须回答：

- 不使用 LangChain 能否实现？
- LangChain 替我减少了什么工作？
- LangChain 又增加了什么复杂度？
- 是否应该使用 Agent？
- 固定函数流程是否更稳定？
- LangGraph 的状态和恢复能力是否真正必要？
- 这个实验是否值得进一步产品化？

### 3.3 第三目标：发现真实可用场景

当前可以优先探索“研究并生成内容提案”，但不把项目限制为自媒体工具。

未来可能出现的方向包括：

- 内容创作
- 技术调研
- PRD 生成
- 旅行规划
- 学习计划
- 研究报告
- 个人知识整理

这些只是候选场景，不在当前阶段提前固化为产品模块。

---

## 4. 非目标

在完成核心实验前，明确不做：

- React 前端工作台
- Spring Boot 业务后端
- 用户登录与权限
- ECS 正式部署
- 多租户
- 商业化
- 自动发布到内容平台
- 拖拽工作流编辑器
- Recipe 市场
- 插件市场
- 多 Agent 协作系统
- 通用知识库管理后台
- Redis、Kafka、Elasticsearch
- Kubernetes
- 复杂微服务架构
- 长期记忆系统
- 完整个人风格模型

这些不是永久排除，而是暂时不进入第一阶段。

---

## 5. 核心原则

### 5.1 实验优先于架构

先通过实验发现问题，再引入架构。

禁止先设计完整平台，再寻找使用场景。

### 5.2 先理解普通模型调用，再进入 Agent

学习顺序必须保持：

```text
模型调用
→ 结构化输出
→ Tool Calling
→ Agent
→ RAG
→ LangGraph
```

不跳过基础能力直接做多 Agent。

### 5.3 每个实验必须可以独立运行

每个实验应具备：

- 明确输入
- 明确输出
- 单独运行入口
- 自动化测试
- 运行示例
- 实验复盘

### 5.4 允许得出“不需要 LangGraph”的结论

如果某个任务使用普通 Python 函数更简单、更稳定，应明确记录。

项目目标不是证明 LangGraph 无所不能，而是掌握它的适用边界。

### 5.5 暂不抽象 Recipe

Recipe 只有在多个真实流程被反复运行后才可能出现。

当前不预设：

```text
Recipe = 输入 Schema + Graph + Prompt + Tool + 输出 Schema
```

这可以作为未来候选抽象，但不是现阶段的基础设施。

### 5.6 使用真实任务验证

实验可以小，但不能只是无意义的 Hello World。

应尽量使用自己真实关心的问题，例如：

- 程序员职业转型内容选题
- LangChain 与 LangChain4j 技术调研
- 野行章鱼需求分析
- 东京旅行资料整理
- 自媒体账号方向研究

---

## 6. 项目形态

### 6.1 第一阶段形态

第一阶段只建设一个 Python 仓库。

```text
ai-workflow-lab/
├── experiments/
│   ├── 01-structured-output/
│   ├── 02-tool-calling/
│   ├── 03-agent/
│   ├── 04-rag/
│   └── 05-langgraph-workflow/
│
├── src/
│   └── ai_workflow_lab/
│       ├── config/
│       ├── models/
│       ├── prompts/
│       ├── tools/
│       ├── observability/
│       └── utils/
│
├── tests/
├── docs/
│   ├── notes/
│   ├── decisions/
│   └── reviews/
│
├── data/
│   ├── sample_docs/
│   └── outputs/
│
├── scripts/
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

### 6.2 推荐基础工具

- Python
- `uv` 或其他统一依赖管理工具
- `pyproject.toml`
- `pytest`
- `ruff`
- `mypy` 或 `pyright`
- Pydantic
- LangChain
- LangGraph
- 本地 `.env`
- Git

具体依赖版本在项目初始化时锁定，不在企划阶段预设。

---

## 7. 实验总览

| 实验 | 核心主题 | 需要回答的问题 |
|---|---|---|
| 01 | 模型与结构化输出 | 如何让模型稳定返回业务可用对象？ |
| 02 | Tool Calling | 模型如何调用外部能力并处理失败？ |
| 03 | Agent | 哪些开放任务适合自主决策？ |
| 04 | RAG | 检索增强是否真的改善答案？ |
| 05 | LangGraph | 状态、暂停、恢复和节点编排是否有价值？ |

---

# 8. 实验一：模型调用与结构化输出

## 8.1 目标

掌握最基础、最稳定的大模型应用形式：

```text
输入
→ Prompt
→ 模型
→ 结构化结果
```

本阶段不使用 Agent，不使用 LangGraph。

## 8.2 示例任务

输入：

> 我想做一个关于程序员职业转型的内容。

输出三个内容方向：

```python
class TopicOption(BaseModel):
    title: str
    angle: str
    target_audience: str
    core_question: str
    reason: str
```

## 8.3 需要实现

- 模型初始化
- 环境变量配置
- Prompt 模板
- Pydantic Schema
- 结构化输出
- 输出校验
- 异常处理
- 重试策略
- 同步调用
- 流式输出对比
- 日志记录

## 8.4 验收标准

- 连续多次运行均返回合法 Schema
- 非法输出能被识别
- 错误不会直接导致程序无说明退出
- 可以更换输入主题复用
- 有至少一组自动化测试
- 输出保存为 JSON

## 8.5 复盘问题

- LangChain 的结构化输出比直接调用模型 SDK 省了什么？
- Schema 越复杂是否越不稳定？
- 哪些字段适合让模型生成？
- 哪些字段应该由业务代码计算？
- 是否需要流式结构化输出？

---

# 9. 实验二：Tool Calling

## 9.1 目标

理解模型如何从“生成文本”转变为“调用系统能力”。

## 9.2 示例任务

输入：

> 调研 LangChain 和 LangChain4j 的主要差异，并输出一份带来源的 Markdown 摘要。

## 9.3 初始工具

建议先实现三个工具：

```text
search_web
read_webpage
save_markdown
```

如果暂时不接真实搜索服务，可先使用可控的本地模拟工具验证调用流程，再替换为真实接口。

## 9.4 需要实现

- Tool 定义
- Tool 参数 Schema
- Tool 描述
- 模型工具绑定
- 工具执行
- 工具返回结构
- 工具异常
- 超时
- 参数错误
- 工具调用日志
- 最终 Markdown 输出

## 9.5 验收标准

- 模型能正确选择工具
- 模型能生成合法参数
- 工具失败时能返回明确错误
- 工具结果能重新进入模型上下文
- 最终结果记录使用过的来源
- 可限制最大工具调用次数

## 9.6 复盘问题

- 模型是否经常选择错误工具？
- Tool 描述对调用准确率影响多大？
- 哪些工具应该由模型选择？
- 哪些工具应该由代码固定调用？
- Tool 返回自然语言还是结构化数据更好？

---

# 10. 实验三：Agent

## 10.1 目标

理解 Agent 的自主循环，以及它相比固定工作流的收益和风险。

## 10.2 示例任务

> 研究一个适合个人账号发布的技术选题，并输出内容提案。

Agent 可以使用：

- 搜索
- 网页读取
- 内容摘要
- 保存文件

## 10.3 需要实现

- Agent 创建
- 工具绑定
- 最大步骤限制
- 执行超时
- 中间步骤日志
- Token 与调用次数记录
- 重复调用检测
- 工具失败处理
- 最终结果 Schema

## 10.4 对照实验

必须同时实现一个固定流程版本：

```text
生成搜索词
→ 固定调用搜索
→ 固定读取结果
→ 固定生成提案
```

然后与 Agent 版本比较：

- 输出质量
- 稳定性
- 速度
- Token 消耗
- 调试难度
- 可预测性

## 10.5 验收标准

- Agent 能完成完整任务
- 有明确最大循环次数
- 可以查看每次 Tool 调用
- 不会无限循环
- 有固定流程对照组
- 输出结果可以自动校验

## 10.6 复盘问题

- Agent 是否真的比固定流程好？
- 自主决策在哪些步骤有价值？
- 哪些步骤应禁止 Agent 自由发挥？
- 如何判断 Agent 已经完成任务？
- 如何控制成本和延迟？

---

# 11. 实验四：最小 RAG

## 11.1 目标

理解文档检索增强生成的完整链路，并验证它是否真正改善回答。

## 11.2 数据范围

只准备少量真实 Markdown 文档，例如：

- 职业转型思考
- 野行章鱼项目记录
- 自媒体脑暴
- 技术学习笔记
- 旅行计划笔记

无需一开始处理大量 PDF。

## 11.3 基本流程

```text
文档读取
→ 文本切片
→ Embedding
→ 本地向量存储
→ Retriever
→ 上下文组装
→ 模型回答
```

## 11.4 需要实现

- Document Loader
- Text Splitter
- Embedding
- 本地向量存储
- Retriever
- Top K
- 元数据
- 来源引用
- 无结果处理
- 对照测试

## 11.5 对照实验

对同一个问题分别执行：

1. 不使用 RAG
2. 使用全文直接塞入上下文
3. 使用向量检索
4. 使用不同切片大小
5. 使用不同 Top K

## 11.6 验收标准

- 可以成功索引本地文档
- 检索结果与问题相关
- 输出能标记来源
- 无相关内容时不会伪造来源
- 至少有一组检索质量测试
- 可清空并重建索引

## 11.7 复盘问题

- RAG 是否真的提高回答准确度？
- 切片大小如何影响结果？
- Top K 过大是否引入噪声？
- 向量检索是否需要配合关键词检索？
- 是否值得引入独立向量数据库？

---

# 12. 实验五：LangGraph 有状态工作流

## 12.1 目标

验证 LangGraph 的核心价值：

- State
- Node
- Edge
- Conditional Edge
- Checkpoint
- Interrupt
- Resume
- 节点失败
- 恢复执行
- Human-in-the-loop

## 12.2 建议场景

**研究并生成一份内容提案**

流程：

```text
输入想法
    ↓
分析任务
    ↓
生成三个方向
    ↓
暂停等待人工选择
    ↓
根据选择收集资料
    ↓
生成内容提案
    ↓
质量检查
    ↓
输出 Markdown
```

这个场景只是实验载体，不代表未来产品必然是内容创作工具。

## 12.3 建议状态结构

```python
class WorkflowState(TypedDict):
    user_input: str
    topic_options: list[dict]
    selected_topic: dict | None
    sources: list[dict]
    proposal: dict | None
    quality_result: dict | None
    final_markdown: str | None
    errors: list[str]
```

## 12.4 建议节点

```text
analyze_input
generate_topic_options
wait_for_selection
collect_sources
generate_proposal
quality_check
revise_proposal
render_markdown
```

## 12.5 建议条件分支

```text
资料是否足够？
├── 否：继续收集
└── 是：生成提案

质量检查是否通过？
├── 否：修订
└── 是：输出
```

必须限制最大修订次数，避免无限循环。

## 12.6 需要实现

- Graph 状态
- 普通节点
- 条件边
- 人工中断
- 恢复执行
- Checkpointer
- Thread ID
- 节点输入输出日志
- 节点异常
- 重试策略
- 最大循环次数
- 最终结果保存

## 12.7 验收标准

- 工作流可以暂停等待人工输入
- 程序重启后仍可继续恢复
- 单个节点失败不会丢失全部状态
- 可以查看当前节点和历史节点
- 输出包含中间决策结果
- 质量检查失败时最多自动修订固定次数
- 整个流程有自动化测试

## 12.8 复盘问题

- 普通 Python 函数是否已经足够？
- LangGraph 的 Checkpoint 是否真正有帮助？
- 哪些状态必须持久化？
- 哪些节点适合人工介入？
- Graph API 和 Functional API 哪个更适合？
- 工作流是否值得进一步产品化？

---

# 13. 公共能力

五个实验可以逐步沉淀公共能力，但禁止过早设计“大而全框架”。

## 13.1 模型配置

统一处理：

- Provider
- Model
- API Key
- Temperature
- Timeout
- Retry
- Token 限制

## 13.2 Prompt 管理

第一阶段使用文件管理：

```text
src/ai_workflow_lab/prompts/
├── topic_generation.md
├── research_summary.md
└── quality_check.md
```

每个 Prompt 记录：

- 用途
- 输入变量
- 输出结构
- 修改原因
- 版本说明

暂不建设 Prompt 管理后台。

## 13.3 日志

至少记录：

- 实验名称
- 模型
- 输入摘要
- 输出摘要
- Tool 调用
- 节点名称
- 耗时
- Token
- 错误
- 重试次数

注意避免把 API Key 和敏感原文直接写入日志。

## 13.4 输出目录

```text
data/outputs/
├── structured-output/
├── tool-calling/
├── agent/
├── rag/
└── langgraph/
```

每次运行可以保存：

- 输入
- 最终输出
- 中间结果
- 运行元数据
- 错误信息

---

# 14. 测试策略

## 14.1 单元测试

适用于：

- Schema 校验
- 工具参数
- 文本切片
- 状态更新函数
- 条件判断
- Markdown 渲染

## 14.2 集成测试

适用于：

- 模型结构化输出
- Tool Calling
- RAG 检索
- LangGraph 执行
- Checkpoint 恢复

模型集成测试应控制调用次数和成本。

## 14.3 模拟模型

对于工作流逻辑测试，优先使用 Fake Model 或固定响应，避免每次测试都调用真实模型。

## 14.4 回归样例

维护少量固定输入：

```text
cases/
├── content_topic.json
├── technical_research.json
├── product_requirement.json
└── travel_question.json
```

每次修改 Prompt 或工作流后检查：

- Schema 是否仍合法
- 关键字段是否存在
- 是否产生明显退化
- Tool 调用是否异常增加

---

# 15. 评估维度

当前不追求复杂自动评分平台，但每个实验至少记录以下维度：

| 维度 | 说明 |
|---|---|
| 正确性 | 是否完成任务，是否存在明显错误 |
| 结构稳定性 | 是否符合 Schema |
| 来源可靠性 | 是否能追溯信息来源 |
| 可控性 | 是否遵守步骤与限制 |
| 稳定性 | 多次运行结果是否可接受 |
| 延迟 | 完成一次任务需要多久 |
| 成本 | 调用次数和 Token |
| 可调试性 | 出错时是否能定位原因 |
| 代码复杂度 | 框架带来的额外成本 |
| 实用性 | 自己是否愿意再次使用 |

每个实验结束后填写一份复盘表。

---

# 16. 实验复盘模板

```markdown
# 实验复盘：实验名称

## 实验目标

## 最终实现

## 实际运行结果

## LangChain / LangGraph 带来的收益

## 框架增加的复杂度

## 不使用框架的替代方案

## 发现的问题

## 是否值得继续

## 是否出现可复用模式

## 是否值得产品化

## 下一步
```

---

# 17. 阶段里程碑

## M0：仓库初始化

完成：

- Python 工程
- 依赖管理
- 环境变量
- 测试
- Lint
- README
- 基础日志

## M1：结构化输出实验完成

能够稳定输出业务对象。

## M2：Tool Calling 实验完成

能够调用工具并处理异常。

## M3：Agent 对照实验完成

能够明确回答 Agent 与固定流程的差异。

## M4：RAG 实验完成

能够评价检索增强是否有效。

## M5：LangGraph 工作流完成

能够暂停、恢复、持久化并输出最终 Markdown。

## M6：阶段 Review

集中回答：

- 哪个实验最有真实使用价值？
- 是否出现重复模式？
- 是否需要 Recipe？
- 是否需要前端？
- 是否需要 Java 后端？
- 是否需要部署到 ECS？
- 哪条流程值得成为正式产品的第一条业务链路？

---

# 18. 进入产品化阶段的条件

只有满足以下多数条件，才开始设计 React、Spring Boot 和 ECS 部署：

- 至少一条工作流被真实重复使用
- CLI 或 Notebook 已明显影响使用体验
- 需要保存任务历史
- 需要管理多次运行
- 需要编辑和版本化最终产物
- 需要长期保存用户输入
- 需要权限或 API Key 管理
- 需要异步执行
- 需要可靠部署
- 需要 Java 业务服务承接真实需求

若条件不满足，则继续保持实验项目，不强行产品化。

---

# 19. 产品化阶段的候选形态

本阶段仅保留方向，不进入实施。

如果实验验证成功，未来可能演化为：

```text
React 前端
    ↓
Spring Boot 业务后端
    ↓
Python LangChain / LangGraph Runtime
    ↓
模型、搜索、RAG、MCP、外部工具
```

Spring Boot 负责：

- 任务
- 用户配置
- 运行记录
- 产物
- 版本
- 事务
- 权限
- API

Python Runtime 负责：

- LangChain
- LangGraph
- 模型
- Tool
- RAG
- Checkpoint
- AI 工作流

但这不是当前阶段的交付目标。

---

# 20. 风险与控制

## 20.1 过早产品化

风险：

- 把时间耗在前端、CRUD 和部署
- 尚未验证 AI 工作流价值
- 产生大量无用基础设施

控制：

- M5 前禁止建设完整前后台

## 20.2 为学习框架强行使用框架

风险：

- 简单任务被过度复杂化
- 无法判断框架真实价值

控制：

- 每个复杂实验都保留普通 Python 对照实现

## 20.3 Agent 不可控

风险：

- 无限循环
- 重复工具调用
- Token 成本失控
- 输出不稳定

控制：

- 限制步数
- 限制时间
- 限制工具调用
- 记录完整轨迹

## 20.4 RAG 伪准确

风险：

- 检索结果不相关
- 模型仍然编造
- 引用与结论不一致

控制：

- 保留来源
- 建立对照问题
- 无相关结果时允许明确回答“不知道”

## 20.5 追逐新技术

风险：

- 不断更换框架
- 实验无法完成
- 只学 API，不理解范式

控制：

- 五个核心实验完成前不增加新的 AI 框架

---

# 21. 最终成功标准

本阶段成功不以“做出一个完整产品”为标准。

成功标准是：

1. 能独立搭建 LangChain 项目
2. 能稳定使用结构化输出
3. 能设计和调试 Tool Calling
4. 能判断 Agent 是否适合某个任务
5. 能实现并评价最小 RAG
6. 能使用 LangGraph 完成有状态工作流
7. 能实现人工中断与恢复
8. 能记录执行轨迹、错误和成本
9. 能对普通代码与 AI 工作流进行理性比较
10. 能明确判断下一步是否值得产品化

---

# 22. 当前结论

AI Workflow Lab 的第一阶段不是“开发个人 AI 工作台”，而是：

> 通过五个连续实验，系统理解 LangChain / LangGraph，并发现一条值得重复使用和进一步产品化的真实工作流。

当前只建设 Python 实验仓库。

React、Spring Boot、ECS、自用工作台、Recipe 和通用内核，全部留到实验完成后的阶段 Review 再决定。
