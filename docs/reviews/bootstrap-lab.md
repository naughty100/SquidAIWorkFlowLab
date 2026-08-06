# 阶段复盘：bootstrap-lab

## 实验目标

在不引入 Tool、Agent、RAG 或 LangGraph 的前提下，建立可复现、安全、默认离线的 Python 实验基座，为后续实验提供统一配置、能力报告和运行记录。

## 最终实现

- Python 3.12、`uv.lock`、`src` layout、Typer CLI、pytest、ruff 和 strict pyright。
- Pydantic Settings 与 OpenAI-compatible 基础配置校验。
- `supported`、`unsupported`、`unknown` 三态能力模型及显式结构化机制解析器。
- `lab doctor` 离线检查和 `lab doctor --live` 五项能力探测。
- 本地 Run Recorder、版本化 JSONL、summary 和内容寻址 gzip artifact。
- 字段名与实际秘密值双重脱敏，以及固定响应 Mock Model。

## 实际运行结果

- `uv` 自动准备并使用 CPython 3.12.13。
- 离线 doctor 成功检查 Python、锁文件、核心依赖和三个数据目录。
- 离线能力均为 `unknown / live_probe_not_requested`，未构造真实客户端。
- ruff、strict pyright、`uv lock --check` 均通过。
- 18 个离线测试全部通过。
- 当前环境没有项目模型凭据，因此未执行真实 live probe；这符合“live 必须显式启用”的安全边界。

## 基座带来的收益

- 后续实验能够记录相同的环境、模型 host、依赖锁和 Trace schema 信息。
- Provider 传输问题、明确不支持和未能判断不会再混为同一状态。
- 大正文不挤占 JSONL，同时保留可校验、可重建的调试信息。
- Mock 路径从设计上与真实客户端构造隔离，默认测试不会产生费用。

## 增加的复杂度

- Run Recorder 和 artifact store 引入了内容规范化、hash、压缩、引用校验和路径安全逻辑。
- strict pyright 对动态 SDK 返回类型需要通过边界适配器隔离。
- Typer 仅有一个命令时会把应用折叠为单命令，必须使用 callback 保持 `lab doctor` 命令组形态。

## 发现的问题与处理

- 中文字符串会触发 Ruff 的 ambiguous-unicode 标点规则；项目保留中文文档和用户消息，因此只禁用 `RUF001/RUF002`，其他 Ruff 规则继续启用。
- Windows 环境中 `uv` 无法对部分缓存文件创建 hardlink，会自动退回复制；只影响安装性能，不影响结果。
- `unknown` 必须保留独立语义；认证、网络和限流错误不能被记录成 Provider 不支持。

## 是否值得继续

值得。基座已保持在 run、event、artifact 和 capability 四个核心概念内，没有提前引入 Tool 或 Graph 专用抽象。下一阶段可以在此基础上公平实现结构化输出三种 variant。

## 下一步

完成并归档 `bootstrap-lab` 后，再应用 `structured-output-experiment`。在配置真实 Provider 凭据时补做 live doctor，并将脱敏能力报告作为实验一的前置记录。
