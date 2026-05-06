# TODO 08：质量验收与回归策略

## 问题

真实性提升不是单一功能，涉及检索、prompt、后端状态、前端交互和并发。没有统一验收策略，容易出现一处变真实、另一处泄漏未来或破坏旧入口。

## 目标

建立质量护栏和 rollout 策略，让每个阶段都能验证：

- 拟真性是否提升。
- 未来事实是否泄漏。
- persona 是否被遵守。
- 实时会话是否串行。
- 旧推演入口是否兼容。

## 自动测试矩阵

### 后端

- [x] context pack 分层字段存在且含义正确。
- [x] future evidence 不混入 cutoff-safe topic digest。
- [x] future evidence 能影响 assessment 风险字段。
- [x] first reply 不引用 future evidence 原文。
- [x] realtime branch session 同一时间只有一个 running job。
- [x] branch transcript 按顺序进入下一轮 prompt。
- [x] 删除会话/重跑分析能清理或失效相关 branch 数据。

### 前端

- [x] 用户连续消息触发 debounce，而不是每条都请求 LLM。
- [x] running job 时不会并行触发新 job。
- [x] other 回复拆泡延迟展示。
- [x] typing、error、retry 状态展示正确。
- [x] 原 simulation result 展示不回归。

当前前端自动化覆盖集中在 `desktop/tests/visualShell.test.tsx` 和 `desktop/tests/frontUiAdapters.test.ts`。完整 Playwright/E2E 不纳入本轮实现，仍以 Vitest 集成测试和人工验收矩阵为主。

### 评估样例

- [x] 固定样例能批量跑出当前输出。
- [x] 每个样例能标注是否出现未来泄漏。
- [x] 每个样例能标注是否存在 persona 违背。
- [x] 高风险未来证据样例不会轻易翻盘。
- [x] 固定样例已有 provider 回归入口：`python scripts/run_realism_provider_regression.py`。

## 人工验收标准

- [ ] 对方不像突然换了一个更成熟、更会沟通的人。
- [ ] 回复长度和拆句节奏接近真实历史。
- [ ] 当原时间线后续证明对方明确拒绝时，轻微措辞修改不会让关系突然成功。
- [ ] 当原时间线只是因为表达唐突导致失败时，温和改写可以改善首轮可接性，但仍不夸大长期结果。
- [ ] 实时会话里用户能自然连续输入，不被 LLM 抢答。

## Rollout 策略

- 第一阶段在现有 `/simulations` 上增加分层证据，默认可关闭。
- 第二阶段加入 style profile，但保持旧字段兼容。
- 第三阶段新增 realtime branch session，不删除 `single_reply` / `short_thread`。
- 第四阶段如果实时分支稳定，再把它设为主入口。

## 观测指标

- 推演请求平均耗时。
- context pack token/字符长度。
- future evidence 命中率。
- future leakage 测试失败数。
- branch reply job 冲突/409 次数。
- 用户触发重试次数。

## 实施 TODO

- [x] 建立后端测试矩阵。
- [x] 建立前端测试矩阵。
- [x] 将固定评估样例接入回归流程。
- [x] 增加 feature flag 或设置项，允许关闭 future evidence。
- [x] 增加 rollout 文档，记录如何从短链入口切到实时分支入口。
- [x] 增加合成真实性测试集 audit：`python scripts/validate_realism_synthetic_corpus.py`，用于检查导出时间、时间语义、future evidence 边界和重复线索。
- [x] 每完成一个 realism TODO，就在本文件勾选对应测试和验收项。

## 验收标准

- [x] 所有新增后端测试通过。
- [x] 所有新增前端测试通过。
- [ ] 固定样例无未来泄漏。（2026-05-04 已跑 12 个 live baseline case，11 个 completed 中 0 泄漏；另 1 个瞬时 provider `HTTPStatusError` 在单 case 重试后通过。仍需结合人工拟真性验收最终签收。）
- [x] 旧推演入口兼容。
- [x] 实时分支会话在失败和切换会话场景下可恢复或可重试。

## 2026-05-03 本地验证记录

- `PYTHONPATH=src pytest -q`：122 项通过。
- `npm test`（在 `desktop/` 下）：13 个测试文件 128 项通过。
- `npm run typecheck`（在 `desktop/` 下）：通过。
- `python scripts/report_realism_baseline.py`：输出 12 个固定基线样例，覆盖 3 个场景和 8 类失败类型。
- 当前真实性测试集定位为 `D:\ifThen\tests\fixtures\realism_synthetic`，固定基线样例均回指该目录下的合成语料。
- `python scripts/run_realism_provider_regression.py --require-provider --max-cases 1 --output-json .pytest-tmp/realism-provider-live-smoke.json --output-markdown .pytest-tmp/realism-provider-live-smoke.md`：使用本地 `llm_config.env` 的 Responses API 配置完成 1 个 provider 回归抽样，0 泄漏、0 错误。
- `python scripts/run_realism_provider_regression.py --require-provider --output-json .pytest-tmp/realism-provider-live-full.json --output-markdown .pytest-tmp/realism-provider-live-full.md`：12 个固定 baseline case 中 11 个 completed、0 泄漏、0 risk-review flag、1 个瞬时 `HTTPStatusError`；失败样例单独重试通过。
- `python scripts/run_realism_analysis_performance.py --require-provider --analysis-llm-max-concurrency 1 --case-id case-01-hidden-trauma-confession --output-json .pytest-tmp/realism-analysis-performance-case01-c1.json --output-markdown .pytest-tmp/realism-analysis-performance-case01-c1.md`：性能抽样 runner 已建成并能驱动真实 worker 全分析链路，但 live provider 长跑在 summary 阶段遭遇 `HTTPStatusError` / `ReadTimeout`，因此完整性能验收仍未完成。
