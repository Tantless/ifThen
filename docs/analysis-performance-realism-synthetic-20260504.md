# 合成真实性测试集完整分析性能抽样记录

日期：2026-05-04

## 目的

对仓库内合成真实性测试集 `D:\ifThen\tests\fixtures\realism_synthetic` 建立可复用的完整分析性能抽样命令入口，并验证它能通过隔离数据目录驱动真实 `run_next_job()` 全分析链路。

## 本次执行

- 新增命令：`python scripts/run_realism_analysis_performance.py`
- 默认数据集：`tests/fixtures/realism_synthetic`
- provider 来源：本地 `llm_config.env`
- 实际 provider 模型：`gpt-5.5`
- 运行方式：隔离 `IF_THEN_DATA_DIR`，每个 synthetic case 单独写入 `.data/perf-runs/realism-synthetic-*/<case>/app-data`

## 结果

本次没有拿到完整成功样本，因此**不能**用本次结果勾选“真实性改造没有显著增加完整 pipeline 耗时”。

但本次已经确认两件事：

1. 性能复测 runner 已经具备，可重复执行，不再依赖一次性手工命令。
2. 当前阻塞来自 live provider 通道稳定性，而不是分析链路缺少入口。

## 已观测到的阻塞

在 `case-01-hidden-trauma-confession` 的 live full-analysis 抽样中，摘要阶段多次遇到 provider 侧失败：

- `Responses request failed: ReadTimeout`
- `Responses request failed: HTTPStatusError`

对应样本：

- `.data/perf-runs/realism-synthetic-20260504-101554/`
- `.data/perf-runs/realism-synthetic-20260504-102445/`

其中一次单 case 抽样在失败前已经完成：

- 3523 条消息解析
- 108 个 segment 预览与落库
- 31 次 segment summary LLM 调用
- 746.329 秒 worker 记录耗时

但任务仍在 `summarizing` 阶段中断，尚未进入 topic / persona / snapshot / finalizing，因此该数值不能作为完整 pipeline 成功样本使用。

## 结论

- `scripts/run_realism_analysis_performance.py` 已可作为后续真实性路线图性能验收入口。
- 当前 `llm_config.env` 对应的 live provider 通道不稳定，无法在 2026-05-04 的这次会话中稳定完成 synthetic 长样本 full-analysis。
- 后续要完成该验收项，需要在更稳定的 provider 通道、可用模型配额或更合适的长任务运行窗口下重跑。

## 相关文件

- 运行脚本：`scripts/run_realism_analysis_performance.py`
- 最近单 case 结果：`.pytest-tmp/realism-analysis-performance-case01-c1.json`
- 最近完整 run 根目录：`.data/perf-runs/realism-synthetic-20260504-102445/`
