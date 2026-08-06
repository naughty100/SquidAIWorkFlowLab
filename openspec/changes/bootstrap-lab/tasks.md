## 1. 工程初始化

- [ ] 1.1 使用 Python 3.12 和 `uv` 创建 `pyproject.toml`、`.python-version`、`src/ai_workflow_lab` 包及 `uv.lock`
- [ ] 1.2 配置 Typer 的 `lab` 入口、pytest、ruff、pyright 和 development dependency group
- [ ] 1.3 补充 `.env.example`、`.gitignore` 与本地 `data/outputs`、runtime/cache 目录约定

## 2. 配置与模型能力

- [ ] 2.1 实现 Pydantic Settings、配置校验和 `base_url_host` 规范化
- [ ] 2.2 实现字段名与实际秘密值双重脱敏器，并覆盖异常、请求头和嵌套对象
- [ ] 2.3 定义能力三态、探测诊断和具体 `StructuredOutputMethod` 解析器
- [ ] 2.4 实现默认离线的 `lab doctor`，检查解释器、锁文件、配置和运行目录
- [ ] 2.5 实现 `lab doctor --live` 的 chat、streaming、tool calling、JSON mode、JSON schema 最小探测及报告保存

## 3. Run Recorder 与 Artifact

- [ ] 3.1 实现 run ID、运行目录、summary 元数据和版本化 JSONL 事件写入
- [ ] 3.2 实现内容规范化、SHA-256、gzip JSON artifact 写入和同内容复用
- [ ] 3.3 实现大文本事件外置及通过 artifact reference 重建逻辑输入
- [ ] 3.4 提供固定响应的 Mock Model，并确保默认路径不会构造真实网络请求

## 4. 验证与交付

- [ ] 4.1 为配置错误、三态判断、机制解析、秘密泄漏、artifact 去重和 Trace 重建编写单元测试
- [ ] 4.2 配置并通过 `ruff check`、`pyright`、`uv lock --check` 和 `uv run --locked pytest -m "not live"`
- [ ] 4.3 更新 README，记录安装、离线 doctor、live 探测、数据目录和安全边界
- [ ] 4.4 执行一次脱敏后的本地/可用时 live 验证，完成 `docs/reviews/bootstrap-lab.md` 后再进入下一 change
