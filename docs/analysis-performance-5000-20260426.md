# 5000 条消息分析性能采样报告

日期：2026-04-26

本报告基于一次真实 worker 运行结果，测试对象是 MVP 测试集中的 `聊天记录-5000条.txt`。运行时使用隔离数据目录，没有修改应用正常使用的 `.data` 数据库。

## 运行配置

| 项目 | 值 |
| --- | --- |
| 数据集 | `聊天记录-5000条.txt` |
| 文件大小 | 446,350 bytes |
| 文件声明消息数 | 5,000 |
| 实际解析消息数 | 5,000 |
| 时间范围 | 2025-03-02 20:18:03 至 2025-03-09 23:53:47 |
| 分段数 | 47 |
| 模型 | `gpt-5.4-mini` |
| Provider host | `new.myouo.online` |
| 隔离数据目录 | `.data/perf-runs/analysis-5000-20260426-155914/app-data` |
| 原始日志 | `.data/perf-runs/analysis-5000-20260426-155914/worker.log` |
| 原始结果 JSON | `.data/perf-runs/analysis-5000-20260426-155914/result.json` |

本次 worker 任务成功完成。

## 结果概览

| 指标 | 值 |
| --- | ---: |
| Worker 墙钟耗时 | 1204.812 s |
| 持久化性能耗时 | 1204.800 s |
| LLM 调用总数 | 157 |
| 全任务平均每次 LLM 调用耗时 | 7.674 s |
| 持久化消息数 | 5,000 |
| 分段摘要数 | 47 |
| Topic 数 | 13 |
| Topic link 数 | 61 |
| Persona profile 数 | 2 |
| Relationship snapshot 数 | 47 |

## 阶段耗时

| 阶段 | 秒数 | 占比 |
| --- | ---: | ---: |
| topic_resolution | 446.489 | 37.06% |
| summarizing | 374.135 | 31.05% |
| snapshots | 330.114 | 27.40% |
| persona | 29.561 | 2.45% |
| topic_merge_review | 24.061 | 2.00% |
| parsing | 0.427 | 0.04% |
| segmenting | 0.009 | 0.00% |
| finalizing | 0.000 | 0.00% |

前三个阶段 `topic_resolution`、`summarizing`、`snapshots` 合计耗时 1150.738 秒，占总耗时的 95.51%。

## LLM 调用次数

| 调用类型 | 次数 | 相关阶段 | 近似阶段平均耗时 |
| --- | ---: | --- | ---: |
| segment_summary | 47 | summarizing | 7.960 s/call |
| topic_assignment | 47 | topic_resolution | 见下一行合并统计 |
| topic_creation | 13 | topic_resolution | assignment + creation 合计 7.441 s/call |
| topic_merge_review | 1 | topic_merge_review | 24.061 s/call |
| persona | 2 | persona | 14.781 s/call |
| relationship_snapshot | 47 | snapshots | 7.024 s/call |

这次任务的耗时主要由串行 LLM 调用决定。解析 5,000 条消息并写入 SQLite 在本次运行中不到半秒。

## 分段形态

| 指标 | 值 |
| --- | ---: |
| 分段数 | 47 |
| 单段最少消息数 | 2 |
| 单段最多消息数 | 1,177 |
| 单段平均消息数 | 106.383 |
| 单段消息数中位数 | 42 |
| 单段消息数 P90 | 251.6 |

持久化的 47 个分段全部是 `normal` 类型。

## 这次结果说明了什么

实测瓶颈不是原始文件解析、消息插入或分段落库。实测瓶颈是分段之后的串行模型调用数量。

对这个数据集来说，47 个分段触发了 157 次 LLM 调用：

- 47 次分段摘要调用。
- 60 次 topic resolution 调用：47 次 topic assignment，加上 13 次新 topic creation。
- 1 次 topic merge review。
- 2 次 persona generation。
- 47 次 relationship snapshot。

这解释了为什么长聊天记录会让用户感觉等待很久：只要对话被切成很多段，当前 worker 基本就是按段逐个调用模型。即使单次调用平均只有 7 到 8 秒，累计到上百次调用后也会变成很长的等待。

不要把这次 5,000 条消息的结果当成对 100,000 条消息的精确线性预测。分段数取决于真实聊天时间线、消息间隔和消息密度；topic creation 次数也取决于内容本身。但这次实测机制很清楚：运行时间更接近“串行 LLM 工作量”，而不是简单接近“原始消息条数”。

## 进度显示问题

worker 在约 0.4 秒时已经显示 overall progress 到 `97%`，也就是刚完成 parsing 和 segmenting 后，进度条就接近完成了。但此时后面仍然还有约 20 分钟的模型调用工作。

原因是当前进度公式对原始消息解析权重过高，而解析在真实墙钟耗时里非常便宜。对用户界面来说，这个进度会造成明显误导。进度应该按预期 LLM 工作量重新加权，或者至少展示更清晰的阶段级进度。

## 基于本次实测的优化优先级

1. 第一优先级：topic resolution。

   它是本次最大阶段，耗时 446.489 秒。当前设计对每个 segment 做一次 topic assignment，并在必要时额外做 topic creation。减少这里的调用次数或改变处理方式，收益最高。

2. 第二优先级：segment summarization。

   它对 47 个 segment 做了 47 次串行调用，耗时 374.135 秒。这里如果能安全批处理或并发，会明显减少等待时间；但当前实现里有 `previous_snapshot_summary` 依赖，需要先明确是否真的必须保留这种串行上下文。

3. 第三优先级：relationship snapshots。

   它对 47 个 segment 做了 47 次串行调用，耗时 330.114 秒。这个阶段当前是顺序状态更新，因为每个 snapshot 都依赖上一个 snapshot summary。更现实的优化方向可能是降低 snapshot 频率，或者改成按关键事件生成 snapshot，而不是每个 segment 都生成。

4. 同步修复用户感知进度。

   即使暂时不降低总耗时，也应该避免在昂贵 LLM 阶段刚开始时就显示接近完成。这个问题会直接影响用户对等待时间的预期。

## 证据文件

- 原始 worker 日志：`.data/perf-runs/analysis-5000-20260426-155914/worker.log`
- 原始结果 JSON：`.data/perf-runs/analysis-5000-20260426-155914/result.json`
- 隔离 SQLite 数据库：`.data/perf-runs/analysis-5000-20260426-155914/app-data/db/if_then_mvp.sqlite3`
