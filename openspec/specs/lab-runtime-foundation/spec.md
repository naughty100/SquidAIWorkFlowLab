# lab-runtime-foundation Specification

## Purpose

定义 AI Workflow Lab 的可复现本地运行基座、安全边界、运行记录与大文本 artifact 行为。

## Requirements

### Requirement: 可复现的本地 Python 工程
系统 SHALL 使用 Python 3.12、`uv`、`src` layout 和受版本控制的锁文件提供统一的本地运行环境。

#### Scenario: 锁定环境运行检查
- **WHEN** 开发者在依赖声明和锁文件一致的仓库中执行锁定模式检查
- **THEN** 系统 SHALL 在不修改锁文件的前提下运行静态检查和测试

#### Scenario: 锁文件已过期
- **WHEN** 依赖声明与锁文件不一致
- **THEN** 锁文件检查 SHALL 失败并提示先显式更新依赖锁

### Requirement: 最小 CLI 基座
系统 SHALL 提供名为 `lab` 的 CLI，并且本 change 仅暴露 `doctor` 命令。

#### Scenario: 查看 CLI 帮助
- **WHEN** 用户运行 `lab --help`
- **THEN** 系统 SHALL 显示 doctor 命令且不得显示尚未实现的实验、Tool、RAG 或 Graph 命令

### Requirement: 默认离线执行
所有未显式指定 live 的命令和测试 MUST 不得访问模型 Provider、搜索服务或其他外部网络。

#### Scenario: 执行本地 doctor
- **WHEN** 用户运行不带 `--live` 的 `lab doctor`
- **THEN** 系统 SHALL 只检查本地配置、依赖和目录，并且不创建真实模型请求

### Requirement: 敏感配置不得落盘
系统 MUST 在写入日志、Trace、异常和运行摘要前移除 API Key、Authorization、Cookie 及已登记的敏感字段和值。

#### Scenario: 异常包含 API Key
- **WHEN** 外部客户端异常文本或请求对象包含当前配置的 API Key
- **THEN** 所有持久化文件 SHALL 只包含脱敏占位符而不得包含原始 Key

### Requirement: 运行记录具备可复现元数据
每次受记录的命令执行 SHALL 创建独立 `run_id`，并保存 Git commit、Python 版本、依赖锁 hash、模型标识、base URL host 和 Trace schema version。

#### Scenario: 创建运行摘要
- **WHEN** Run Recorder 开始并结束一次命令执行
- **THEN** 对应运行目录 SHALL 包含可解析的 summary 且所有必需元数据字段存在

### Requirement: Trace 与大文本 artifact 分离
系统 SHALL 以 JSONL 追加事件，并将大文本作为内容寻址 gzip JSON artifact 保存；Trace 只保留 artifact reference、hash、长度和短预览。

#### Scenario: 写入大文本事件
- **WHEN** Recorder 接收到超过内联阈值的文本 payload
- **THEN** 系统 SHALL 写入以内容 hash 命名的 artifact，并在事件中用相对引用替代完整正文

#### Scenario: 重复写入相同正文
- **WHEN** 同一运行内再次写入规范化后 hash 相同的正文
- **THEN** 系统 SHALL 复用同一个 artifact reference，而不创建内容重复的文件

### Requirement: Trace 可重建
系统 MUST 保留足够的事件顺序和 artifact reference，使调试工具能够重建当时提供给执行器的逻辑输入。

#### Scenario: 重建外置消息
- **WHEN** Trace 事件包含有效 artifact reference
- **THEN** 读取器 SHALL 能加载 artifact、校验 hash 并恢复事件所引用的完整文本
