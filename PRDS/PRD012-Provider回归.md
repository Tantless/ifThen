# PRD012-Provider回归

## prd-provider回归-完成情况

### 背景

真实性路线图的自动化与本地门禁已经完成，但仍剩真实 provider 输出验收、人工拟真性审查和合成真实性测试集完整分析性能复测。本项目本地 LLM 配置来自 `llm_config.env`，因此需要把 provider 回归收敛成可执行、可测试并能产出报告的命令入口。

### 目标

新增固定基线样例的 provider 回归运行器，让后续可以基于 `D:\ifThen\tests\fixtures\realism_synthetic` 的合成语料验证 future leakage、风险对齐和人格风格风险，并在配置缺失时明确记录 skipped 状态。

### 需求

- 从 `tests/fixtures/realism_baseline/cases.json` 读取固定拟真性基线样例。
- 基于样例中的 `modeler_only_evidence.forbidden_character_knowledge` 检测 future evidence 是否泄漏到角色回复。
- 支持真实 provider 可用时运行，也支持测试中注入 fake 输出。
- 输出 JSON 与 Markdown 报告，包含 summary、per-case 结果、泄漏命中、人工审查提示和跳过原因。
- 默认读取 `llm_config.env`，使用 `API_BASE_URL`、`API_KEY`、`MODEL_NAME` 和 Responses API JSON object 格式请求 LLM。
- 在缺少 `llm_config.env` 或等价 provider 环境时成功退出，并明确标记为 skipped。
- 不修改生产实时分支会话逻辑，不新增数据库 schema。

### 验收标准

- [x] 可以通过 `python scripts/run_realism_provider_regression.py` 执行。
- [x] 缺少 provider 配置时能生成 skipped 报告。
- [x] 单元测试能用 fake provider 验证泄漏检测和报告结构。
- [x] 文档中记录 provider/人工验收的执行入口。

## 工作记录及完成情况

- 新增 `scripts/run_realism_provider_regression.py`，从固定 baseline fixture 读取样例，并为每个样例构造 prompt-level context pack，复用现有 `assess_branch()` 与 `generate_first_reply()` 验证真实 provider 的首轮输出。
- 实现 future leakage 检测：脚本读取 `modeler_only_evidence.forbidden_character_knowledge`，只把出现在 `first_reply_text` 中的 forbidden term 视为角色台词泄漏，并在 JSON summary 中统计 `leakage_case_count`。
- 实现 env-file provider：默认读取 `llm_config.env`，用 Responses API JSON object 格式请求 LLM，并保留 runtime config 作为兼容回退。
- 实现 skipped 报告：缺少 `llm_config.env` 或等价环境变量时，命令成功退出并输出 provider `missing`、case `skipped`、`skip_reason` 和 Markdown/JSON 报告。
- 新增 replay/fake provider 测试：`tests/test_realism_provider_regression.py` 覆盖泄漏检测、生产 prompt builder 调用、skipped 报告和 replay 输出报告。
- 更新 rollout 与路线图文档，将真实 provider/人工验收入口指向 `python scripts/run_realism_provider_regression.py`，并保留“配置可用后才能完成真实验收”的边界。
