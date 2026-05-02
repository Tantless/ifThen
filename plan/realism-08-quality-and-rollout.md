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

- [ ] context pack 分层字段存在且含义正确。
- [ ] future evidence 不混入 cutoff-safe topic digest。
- [ ] future evidence 能影响 assessment 风险字段。
- [ ] first reply 不引用 future evidence 原文。
- [ ] realtime branch session 同一时间只有一个 running job。
- [ ] branch transcript 按顺序进入下一轮 prompt。
- [ ] 删除会话/重跑分析能清理或失效相关 branch 数据。

### 前端

- [ ] 用户连续消息触发 debounce，而不是每条都请求 LLM。
- [ ] running job 时不会并行触发新 job。
- [ ] other 回复拆泡延迟展示。
- [ ] typing、error、retry 状态展示正确。
- [ ] 原 simulation result 展示不回归。

### 评估样例

- [ ] 固定样例能批量跑出当前输出。
- [ ] 每个样例能标注是否出现未来泄漏。
- [ ] 每个样例能标注是否存在 persona 违背。
- [ ] 高风险未来证据样例不会轻易翻盘。

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

- [ ] 建立后端测试矩阵。
- [ ] 建立前端测试矩阵。
- [ ] 将固定评估样例接入回归流程。
- [ ] 增加 feature flag 或设置项，允许关闭 future evidence。
- [ ] 增加 rollout 文档，记录如何从短链入口切到实时分支入口。
- [ ] 每完成一个 realism TODO，就在本文件勾选对应测试和验收项。

## 验收标准

- [ ] 所有新增后端测试通过。
- [ ] 所有新增前端测试通过。
- [ ] 固定样例无未来泄漏。
- [ ] 旧推演入口兼容。
- [ ] 实时分支会话在失败和切换会话场景下可恢复或可重试。
