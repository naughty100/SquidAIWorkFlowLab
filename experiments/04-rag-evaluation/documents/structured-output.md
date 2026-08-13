# 结构化输出的稳定性边界

结构化输出的目标不是得到“看起来像 JSON”的文本，而是得到经过业务 Schema 校验的对象。常见路径包括 Prompt 后解析、Provider 原生 JSON Schema、Tool Calling 和 JSON mode。不同 Provider 对这些机制的支持不同，因此运行开始时应探测并冻结具体机制，不能把 unknown 当成 unsupported，也不能依赖自动策略在运行中漂移。

评估时需要分开记录传输成功率与成功响应中的 Schema 合法率。网络失败、限流和鉴权错误不是 Schema 失败。稳定实验还要记录输入、Prompt、Schema、模型配置和依赖锁文件的 hash，并使用确定性 renderer 控制最终 Markdown。

即使 Provider 声称支持严格 Schema，应用仍需执行 Pydantic 校验、字段范围检查和业务引用校验。结构合法不代表内容正确，语义质量要由独立 Rubric 或人工审阅评估。
