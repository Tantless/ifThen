# TODO 01：拟真性基线与失败样例集

## 问题

如果没有固定样例和分类标准，后续每次 prompt、检索、persona 或实时会话调整，都只能凭体感判断是否更真实。当前需要先把“失真”具体化，形成可复测基线。

## 目标

建立一组小而稳定的真实性评估样例，用来比较当前 `single_reply` / `short_thread` 和后续分层证据、实时会话方案的效果。

## 输入

- 已提交的合成拟真长消息语料，避免真实隐私聊天原文进入仓库。
- 当前推演风险快照：branch assessment、first reply、short thread turns 的失真样例。
- `rewrite-points.md` 已标注的关键改写点，以及从合成语料中补充定位的 self 关键消息。

## 输出

- 固定样例清单。
- 每个样例的目标消息、原文、改写文案、cutoff 时间、预期风险。
- 当前推演失败类型、严重程度和输出快照标注。
- 可用于自动或半自动回归的测试数据格式。

## 失败类型分类

- [x] 过度乐观：只是改了措辞，模型却判断关系明显翻盘。
- [x] 未来事实盲区：原时间线后续已经证明某个约束，但模型完全不知道。
- [x] 未来事实泄漏：模型让角色说出 cutoff 后才知道的内容。
- [x] 人格不符：对方突然变得更成熟、更会表达、更愿意承接。
- [x] 表达风格不符：回复长度、语气词、标点、短句节奏不像本人。
- [x] 检索不准：上下文没有命中真正相关的敏感议题或关系状态。
- [x] 短链不连贯：模型同时写双方，导致 self 的后续发言不像用户。
- [x] 关系状态跳变：单轮回复导致 relationship state 大幅跃迁。

## 实施 TODO

- [x] 从可提交合成语料中选 12 个关键改写点，覆盖告白、冲突、解释、日常靠近、冷淡收束等场景。
- [x] 为每个样例记录原始上下文：source fixture、target sequence no、原文、改写文本、cutoff timestamp。
- [x] 保存当前推演风险快照：branch assessment summary、first reply、short thread turns 和 state_after_turn。
- [x] 给每条推演结果标注失败类型和严重程度。
- [x] 整理成可复用数据文件或测试 fixture。
- [x] 写出最小评估脚本和测试帮助函数，能加载样例并生成对比报告。

## 可能涉及文件

- `tests/fixtures/realism_baseline/cases.json`
- `tests/test_realism_baseline_fixtures.py`
- `scripts/report_realism_baseline.py`
- `plan/` 下的评估记录文档

## 验收标准

- [x] 至少有 10 个固定样例。
- [x] 每个样例都包含 cutoff、原文、改写、当前输出、失败标注。
- [x] 后续实现可以复用这些样例验证是否改善。
- [x] 样例不会提交真实隐私原文；如必须保留，应脱敏或放入本地忽略目录。

## 完成产物

- `tests/fixtures/realism_baseline/cases.json`：12 个固定基线样例，覆盖三段合成关系场景和全部 8 类失败类型。
- `tests/test_realism_baseline_fixtures.py`：验证基线样例数量、失败分类覆盖、目标消息能回指到合成原语料、modeler-only evidence 边界和报告脚本输出。
- `scripts/report_realism_baseline.py`：输出样例总数、场景覆盖、失败类型覆盖和 case 表格，供后续 prompt、检索、persona 或实时分支改动前后对比。

## 风险

- 真实聊天数据高度敏感，不能把未脱敏内容提交到仓库。
- 如果样例过少，容易把后续优化调成只适配少数案例。
- 如果样例只覆盖关系升温场景，会忽视“合理失败”的拟真性。
