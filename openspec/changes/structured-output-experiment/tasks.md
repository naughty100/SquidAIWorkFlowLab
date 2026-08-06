## 1. 实验契约与案例

- [ ] 1.1 定义 `IdeaBrief`、`TopicOption`、TopicOptions 及由代码生成 ID 的领域规则
- [ ] 1.2 创建版本化内容选题案例、公共 Prompt 和 Schema/Prompt hash 记录
- [ ] 1.3 实现运行前的具体结构化机制解析与冻结，拒绝 unknown/unsupported 的显式配置

## 2. 三种结构化输出路径

- [ ] 2.1 实现 `prompt-parse` 的 SDK 普通文本调用、JSON 提取和 Pydantic 校验
- [ ] 2.2 实现按 resolved method 调用 JSON Schema、强制 Tool Calling 或 JSON Mode 的 `sdk-native`
- [ ] 2.3 实现显式传入 `method` 的 `langchain-native`，禁止自动策略选择
- [ ] 2.4 对三个 variant 统一 timeout、token、最多两次传输重试及一次 Schema 重试

## 3. CLI、指标与产物

- [ ] 3.1 增加 `lab run exp01 --case --mode --variant` 并接入 Run Recorder
- [ ] 3.2 分别计算 transport success rate 和成功响应中的 Schema validity rate
- [ ] 3.3 增加 `lab runs show RUN_ID`，展示 variant、resolved method、指标和脱敏错误
- [ ] 3.4 保存输入、结果或校验错误、Prompt hash、调用计数和运行摘要

## 4. 验证与复盘

- [ ] 4.1 用 Mock Model 覆盖三个 variant、相同底层机制、不支持能力、非法 JSON、缺字段和重试上限
- [ ] 4.2 增加独立 live marker，验证传输失败不会计入 Schema 分母
- [ ] 4.3 通过全局 lint、类型、锁文件和离线测试门禁
- [ ] 4.4 对可用 Provider 各 variant 至少运行五次，完成 `docs/reviews/structured-output-experiment.md` 后再进入下一 change
