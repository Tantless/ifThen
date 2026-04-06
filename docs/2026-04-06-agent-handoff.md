# If Then MVP 项目交接文档

更新时间：2026-04-06

本文档用于让下一位 agent 在不重新梳理上下文的前提下，快速接手 `D:\newProj` 当前项目。

## 1. 项目目标

本项目是一个基于 QQ 私聊导出文本的本地 MVP，目标是验证下面这条完整闭环是否成立：

1. 导入 `QQChatExporter V5` 私聊文本
2. 解析为结构化消息
3. 切段并生成段摘要、topic、人格画像、关系快照
4. 在某条历史消息处做 cutoff-safe 改写
5. 调用 LLM 推演对方首轮回复和后续短链对话

当前版本是：

- `Windows` 本地运行
- `FastAPI + SQLite + 本地 worker`
- 无前端页面
- 无 embedding
- 支持真实 LLM 分析和真实 LLM 推演

## 2. 当前系统结构

核心代码位于 [src/if_then_mvp](/d:/newProj/src/if_then_mvp)。

- [api.py](/d:/newProj/src/if_then_mvp/api.py)
  对外 API 入口。包含导入、任务查询、消息浏览、topic/profile/snapshot 查询、`/simulations` 推演接口。

- [worker.py](/d:/newProj/src/if_then_mvp/worker.py)
  后台分析主流程。负责：
  - 原始文本解析
  - 分段
  - 段摘要
  - topic 归并
  - persona
  - relationship snapshot
  - 真实进度打印

- [analysis.py](/d:/newProj/src/if_then_mvp/analysis.py)
  所有分析阶段的 LLM payload、prompt、builder。

- [simulation.py](/d:/newProj/src/if_then_mvp/simulation.py)
  推演阶段的 LLM payload、prompt、首轮回复与逐轮短链模拟。

- [retrieval.py](/d:/newProj/src/if_then_mvp/retrieval.py)
  cutoff-safe 上下文组装。

- [llm.py](/d:/newProj/src/if_then_mvp/llm.py)
  OpenAI 兼容聊天调用与 JSON schema 修复逻辑。

- [runtime_llm.py](/d:/newProj/src/if_then_mvp/runtime_llm.py)
  统一加载本地 LLM 配置文件，分别给 API 与 worker 提供 client。

- [sim_cli.py](/d:/newProj/src/if_then_mvp/sim_cli.py)
  演示用 CLI，支持列出消息和发起推演。

- [models.py](/d:/newProj/src/if_then_mvp/models.py)
  ORM 模型。包括 `Message`、`Segment`、`SegmentSummary`、`Topic`、`TopicLink`、`PersonaProfile`、`RelationshipSnapshot`、`Simulation` 等。

## 3. 运行方式

### 3.1 配置来源

API 和 worker 都从项目根目录的 [local_llm_config.py](/d:/newProj/local_llm_config.py) 读取配置。

此文件中有两套配置：

- `API_LLM_CONFIG`
  给 `/simulations` 使用

- `WORKER_LLM_CONFIG`
  给导入分析阶段使用

注意：

- 这是本地私有配置文件，含敏感信息时不要外泄
- 启动失败时优先检查这个文件是否存在、是否字段齐全

### 3.2 启动命令

API：

```powershell
cd D:\newProj
.venv\Scripts\Activate.ps1
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
python scripts\run_api.py
```

worker：

```powershell
cd D:\newProj
.venv\Scripts\Activate.ps1
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
python scripts\run_worker.py
```

演示 CLI：

```powershell
python scripts\sim_cli.py list-self-text --conversation-id 5 --limit 20
python scripts\sim_cli.py simulate --conversation-id 5 --target-message-id 42 --replacement "没成" --mode short_thread --turn-count 4
```

## 4. 当前已经完成的能力

### 4.1 导入与分析

- QQ 文本导入接口已完成
- 解析器可处理文本、图片占位、资源名、异常说话人块
- 分段规则已完成：
  - 首切只产出 `normal / isolated`
  - 连续 `isolated` 在 24 小时内会合并成 `merged_isolated`
- 段摘要已使用真实 LLM
- 人格画像已使用真实 LLM
- 关系快照已使用真实 LLM

### 4.2 Topic 流程

topic 流程已从“单会话单 topic”重构为“多 topic 增量归并”。

当前实现逻辑：

1. 对每个 `SegmentSummary`
2. 调用 `segment-topic assignment`
3. 判断是否挂到已有 topic
4. 必要时调用 `topic creation`
5. 为 segment 建立一个或多个 `TopicLink`
6. 全部处理后调用 `topic merge review`
7. 合并过窄或重复 topic

这部分最新代码在：

- [analysis.py](/d:/newProj/src/if_then_mvp/analysis.py)
- [worker.py](/d:/newProj/src/if_then_mvp/worker.py)

### 4.3 推演

推演阶段已经不是占位实现。

当前 `/simulations` 已使用真实 LLM 完成：

- 分支判断
- 首轮回复
- 逐轮短链续写
- 重复内容提前停止

相关文件：

- [simulation.py](/d:/newProj/src/if_then_mvp/simulation.py)
- [api.py](/d:/newProj/src/if_then_mvp/api.py)

### 4.4 进度展示

worker 控制台已支持真实进度打印：

- 总进度 `overall`
- 当前阶段进度 `stage_progress`
- 30 秒心跳
- 非伪造百分比

逻辑在 [worker.py](/d:/newProj/src/if_then_mvp/worker.py) 的 `ConsoleProgressReporter` 与进度累计函数中。

### 4.5 演示工具

CLI 已完成：

- `list-self-text`
- `simulate`

相关文件：

- [scripts/sim_cli.py](/d:/newProj/scripts/sim_cli.py)
- [sim_cli.py](/d:/newProj/src/if_then_mvp/sim_cli.py)

## 5. Prompt 工程进度

### 5.1 已完成

所有运行时 prompt 已中文化。

已经做过较深入重写的 prompt：

- `segment summary`
  已拆成更清晰的 `system + user`
  已加入：
  - 任务目标
  - 字段语义
  - 边界纠偏
  - 示例
  - 自检

- topic 三件套
  - `segment-topic assignment`
  - `topic creation`
  - `topic merge review`

这些 prompt 已不再是只写一句任务标签，而是围绕：

- topic 中粒度命名
- 子问题挂到上位 topic
- 允许多归属但有限制
- merge 收敛到更合理的主题粒度

### 5.2 尚未细化完成

下面这些 prompt 仍然可以继续做更强的 prompt engineering：

- `persona`
- `snapshot`
- `branch assessment`
- `first reply`
- `next turn`

当前虽然已中文化且可用，但区分度和“味道”还可以继续增强。

## 6. 当前任务进度

### 6.1 主线任务进度

- [x] 导入 QQ 文本
- [x] 解析消息
- [x] 切段与 `merged_isolated`
- [x] 段摘要
- [x] 人格画像
- [x] 关系快照
- [x] cutoff-safe 检索
- [x] `/simulations` 真实 LLM 推演
- [x] 控制台真实进度打印
- [x] 本地文件式 LLM 配置
- [x] 演示 CLI
- [x] 多 topic 归并重构
- [ ] persona / snapshot / simulation prompt 进一步工程化
- [ ] 更贴近真人口气的推演风格调优
- [ ] 删除/重跑失败会话接口
- [ ] Windows 应用壳或前端页面

### 6.2 当前最适合继续做的方向

推荐优先级：

1. 继续逐条打磨 prompt
   先从：
   - `persona`
   - `snapshot`
   - `branch assessment`
   开始

2. 用真实聊天记录重复做对比实验
   验证：
   - 多 topic 结果是否符合预期
   - 推演“味道”是否像本人
   - 不同改写是否真的产生不同分支

3. 再考虑产品层能力
   比如：
   - 删除会话
   - 重跑会话
   - 可视化页面

## 7. 已知问题与注意事项

### 7.1 FastAPI warning

测试仍有 warning：

- `on_event("startup")` 已弃用

当前不影响功能，但后续可迁到 lifespan。

### 7.2 本地目录

不要误删这些目录或文件：

- [`.data/`](/d:/newProj/.data)
  用户本地运行数据

- [`_tmp_qce_review/`](/d:/newProj/_tmp_qce_review)
  用户本地目录

- [tests/test_models.py.premerge.bak](/d:/newProj/tests/test_models.py.premerge.bak)
  用户/本地备份文件

### 7.3 配置文件

[local_llm_config.py](/d:/newProj/local_llm_config.py) 是本地运行关键文件。

不要把里面的敏感值写进对话、README 或提交说明。

## 8. 当前验证状态

最近已验证：

```powershell
python -m pytest tests/test_analysis.py tests/test_worker.py -q
python -m pytest -q
```

结果：

- `54 passed`
- `26 warnings`

其中 warning 都不是本次 topic 改造导致的功能失败。

## 9. 当前未提交工作区状态

当前工作区有较多未提交修改，属于本轮 MVP 增量开发结果。

主要变更文件包括：

- [README.md](/d:/newProj/README.md)
- [pyproject.toml](/d:/newProj/pyproject.toml)
- [scripts/run_api.py](/d:/newProj/scripts/run_api.py)
- [scripts/run_worker.py](/d:/newProj/scripts/run_worker.py)
- [analysis.py](/d:/newProj/src/if_then_mvp/analysis.py)
- [api.py](/d:/newProj/src/if_then_mvp/api.py)
- [db.py](/d:/newProj/src/if_then_mvp/db.py)
- [llm.py](/d:/newProj/src/if_then_mvp/llm.py)
- [schemas.py](/d:/newProj/src/if_then_mvp/schemas.py)
- [simulation.py](/d:/newProj/src/if_then_mvp/simulation.py)
- [worker.py](/d:/newProj/src/if_then_mvp/worker.py)
- [tests/test_analysis.py](/d:/newProj/tests/test_analysis.py)
- [tests/test_queries.py](/d:/newProj/tests/test_queries.py)
- [tests/test_simulations.py](/d:/newProj/tests/test_simulations.py)
- [tests/test_worker.py](/d:/newProj/tests/test_worker.py)

新增的重要文件包括：

- [local_llm_config.py](/d:/newProj/local_llm_config.py)
- [runtime_llm.py](/d:/newProj/src/if_then_mvp/runtime_llm.py)
- [sim_cli.py](/d:/newProj/src/if_then_mvp/sim_cli.py)
- [scripts/sim_cli.py](/d:/newProj/scripts/sim_cli.py)
- [tests/test_runtime_llm.py](/d:/newProj/tests/test_runtime_llm.py)
- [tests/test_sim_cli.py](/d:/newProj/tests/test_sim_cli.py)
- [tests/test_packaging.py](/d:/newProj/tests/test_packaging.py)

## 10. 下一位 agent 的建议接手顺序

建议不要一上来继续改大块实现，先按下面顺序接手：

1. 读这份文档
2. 读 [README.md](/d:/newProj/README.md)
3. 读：
   - [2026-04-05-counterfactual-conversation-mvp-design.md](/d:/newProj/docs/superpowers/specs/2026-04-05-counterfactual-conversation-mvp-design.md)
   - [2026-04-06-simulation-llm-alignment-design.md](/d:/newProj/docs/superpowers/specs/2026-04-06-simulation-llm-alignment-design.md)
4. 优先看当前核心实现文件：
   - [analysis.py](/d:/newProj/src/if_then_mvp/analysis.py)
   - [worker.py](/d:/newProj/src/if_then_mvp/worker.py)
   - [simulation.py](/d:/newProj/src/if_then_mvp/simulation.py)
5. 先跑一次：
   - `python -m pytest -q`
6. 再决定是继续 prompt engineering，还是先做产品层能力

## 11. 一句话状态结论

这个项目当前已经不是“空壳 MVP”，而是：

- 可以真实导入
- 可以真实分析
- 可以生成多个 topic
- 可以真实推演

下一阶段的重点不再是“能不能跑通”，而是：

- prompt 工程质量
- topic / persona / snapshot / simulation 的拟真度
- 产品可用性与可视化能力
