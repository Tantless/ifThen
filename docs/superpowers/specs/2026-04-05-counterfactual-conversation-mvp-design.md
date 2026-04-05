# “如果那时” MVP 设计文档

## 1. 项目目标

“如果那时”是一个面向真实聊天历史关键节点的反事实对话模拟系统。

用户导入一段真实发生过的 QQ 私聊聊天记录后，系统需要支持：

- 浏览历史聊天记录
- 定位某个过去时间点的某条自己发出的消息
- 修改这条消息的内容
- 在严格不泄漏该时间点之后信息的前提下，推演对方可能会如何回复
- 在 MVP 模式下，自动推演双方后续若干轮对话可能会如何发展

本项目的核心不是“复刻一个聊天对象”，而是：

- 尽量还原目标时间点下的真实关系状态
- 在时间边界内重建对方的回复倾向
- 先判断状态变化，再生成文本回复

## 2. MVP 边界

### 2.1 本期范围

MVP 第一版聚焦验证完整闭环，范围固定为：

- 平台：Windows
- 形态：本地运行的后端核心，不做前端页面
- 输入格式：`QQChatExporter V5` 导出的 QQ 私聊文本文件
- 非文本消息策略：
  - 保留图片/文件资源名
  - 将消息作为占位内容参与上下文
  - 不做图片语义理解
- 分析模式：导入后异步完整分析
- 检索模式：先不用 embedding，MVP 使用规则检索
- 推演模式：
  - 支持 `单轮回复`
  - 支持 `自动短链推演`
- 模型方式：接入 OpenAI 兼容聊天模型 API
- 代码语言：Python

### 2.2 本期不做

以下内容不属于本期 MVP：

- 前端页面或桌面 GUI
- 微信导入
- 图片内容识别
- embedding 检索
- 多分支树状推演
- 交互式分支续聊
- 云端多用户部署
- 分布式任务队列

### 2.3 后续扩展方向

MVP 验证闭环后，后续优先扩展：

- 交互式分支续聊
- 前端页面或桌面应用壳
- embedding 检索
- 更细粒度主题与关系阶段分析

## 3. 交付形态

本项目第一阶段的工程形态为：

- 一个 Python 项目
- 两个运行入口：
  - API 进程
  - Worker 进程
- 使用 SQLite 作为本地数据库
- 使用本地文件目录保存原始导入文件、日志与缓存

这一形态虽然当前不带前端，但已经按“未来 Windows 本地应用”的方向设计：

- API 进程未来可以作为桌面应用的本地后台服务
- Worker 进程未来可以作为桌面应用内置后台任务执行器
- SQLite 和本地文件目录可以直接随应用分发

## 4. 整体架构

### 4.1 架构概览

系统拆为五个核心模块：

1. 解析与规范化模块
2. 分析流水线模块
3. 检索与上下文组装模块
4. 推演模块
5. 任务执行与运行时模块

### 4.2 核心链路

完整处理链路如下：

1. 用户上传 QQ 私聊导出文本
2. API 创建 `conversation` 与 `analysis_job`
3. Worker 异步执行：
   - 导入校验
   - 参与者识别
   - 消息解析与规范化
   - 会话段切分
   - 离散段合并
   - 会话段摘要
   - 基础主题归并
   - 人格与关系特定模式抽取
   - 时间点关系状态快照生成
4. 用户基于某条历史消息发起改写推演
5. 系统按时间边界组装上下文
6. 推演模块先判断状态变化，再生成首轮回复与自动短链结果
7. 结果结构化保存

## 5. API 边界

### 5.1 导入与任务

- `POST /imports/qq-text`
  - 作用：上传 QQ 私聊导出文本，创建会话与分析任务
- `GET /jobs/{job_id}`
  - 作用：查询分析任务状态
- `GET /conversations`
  - 作用：列出已导入会话
- `GET /conversations/{conversation_id}`
  - 作用：查看单个会话的基础信息与分析进度

### 5.2 消息浏览

- `GET /conversations/{conversation_id}/messages`
  - 作用：按时间分页浏览消息，支持时间方向和关键词过滤
- `GET /messages/{message_id}`
  - 作用：查看单条消息与邻近上下文

### 5.3 分析产物查看

- `GET /conversations/{conversation_id}/segments`
  - 作用：查看会话段与合并后的离散段
- `GET /conversations/{conversation_id}/topics`
  - 作用：查看基础主题归并结果
- `GET /conversations/{conversation_id}/profile`
  - 作用：查看双方人格与关系特定互动模式摘要
- `GET /conversations/{conversation_id}/timeline-state`
  - 作用：查看某个时间点之前最近的关系状态快照

### 5.4 推演

- `POST /simulations`
  - 作用：对某条历史消息发起改写推演
  - 支持模式：
    - `single_reply`
    - `short_thread`

### 5.5 配置与健康检查

- `GET /health`
  - 作用：健康检查
- `GET /settings`
  - 作用：读取本地模型与运行配置
- `PUT /settings`
  - 作用：更新本地模型与运行配置

## 6. 核心数据对象

### 6.1 conversations

`conversation` 表示一段逻辑上的聊天历史数据集，是所有消息、分析产物和推演结果的归属对象。

关键字段：

- `conversation_id`
  - 用途：表示这条逻辑会话的唯一标识，所有下游数据都按它归属
- `title`
  - 用途：表示会话名称，通常取聊天名称，供展示和检索使用
- `chat_type`
  - 用途：表示聊天类型，MVP 固定为私聊
- `self_display_name`
  - 用途：表示导入时指定的“我方显示名”，用于把消息归一化成 `self`
- `other_display_name`
  - 用途：表示对方显示名，供展示和角色识别使用
- `source_format`
  - 用途：表示导入来源格式，MVP 固定为 `qq_chat_exporter_v5`
- `status`
  - 用途：表示该会话当前整体状态，例如是否分析完成
- `created_at`
  - 用途：表示会话创建时间

### 6.2 imports

`import` 表示一次具体的导入批次，用来区分“逻辑会话”和“某次导入动作”。

关键字段：

- `import_id`
  - 用途：表示一次导入批次的唯一标识
- `conversation_id`
  - 用途：表示这次导入属于哪个逻辑会话
- `source_file_name`
  - 用途：表示导入的原始文件名
- `source_file_path`
  - 用途：表示原始文件在本地数据目录中的保存路径
- `source_file_hash`
  - 用途：表示原始文件哈希，便于识别重复导入或做回溯
- `message_count_hint`
  - 用途：表示导出文件头里声明的消息总数，供校验用
- `created_at`
  - 用途：表示导入批次创建时间

### 6.3 messages

`message` 是解析与规范化后的最小时间线单元，是后续所有分析的输入源。

关键字段：

- `message_id`
  - 用途：表示单条消息的稳定唯一标识，供定位、改写和关联分析产物使用
- `conversation_id`
  - 用途：表示这条消息属于哪段会话
- `import_id`
  - 用途：表示这条消息来自哪次导入批次
- `sequence_no`
  - 用途：表示导出文件中的原始顺序号，保证同一秒多条消息时仍能稳定排序
- `speaker_name`
  - 用途：表示原始说话人名称，保留展示用信息
- `speaker_role`
  - 用途：表示归一化角色，限定为 `self / other / unknown / system`
- `timestamp`
  - 用途：表示消息发生时间，用于切段、截断与检索
- `content_text`
  - 用途：表示规范化后的消息正文，是后续摘要与推演的主输入
- `message_type`
  - 用途：表示消息类型，限定为 `text / image / file / system / unknown`
- `resource_items`
  - 用途：表示资源列表，如图片文件名，供上下文与展示使用
- `parse_flags`
  - 用途：表示解析标记，如异常说话人或资源存在，用于后续降权与调试
- `raw_block_text`
  - 用途：表示原始消息块文本，供回溯和排查解析问题使用
- `raw_speaker_label`
  - 用途：表示原始说话人标签，供调试使用
- `source_line_start`
  - 用途：表示原始文件中的起始行号，便于定位原文
- `source_line_end`
  - 用途：表示原始文件中的结束行号，便于定位原文

### 6.4 segments

`segment` 表示从消息时间线切分出来的会话段，是摘要、主题和检索的中间粒度。

关键字段：

- `segment_id`
  - 用途：表示单个会话段的唯一标识
- `conversation_id`
  - 用途：表示该会话段属于哪段会话
- `start_message_id`
  - 用途：表示该段第一条消息的标识，便于回溯原文范围
- `end_message_id`
  - 用途：表示该段最后一条消息的标识，便于回溯原文范围
- `start_time`
  - 用途：表示该段起始时间
- `end_time`
  - 用途：表示该段结束时间
- `message_count`
  - 用途：表示该段包含的消息数，供切段校验和摘要决策使用
- `self_message_count`
  - 用途：表示该段内我方消息数，供互动平衡分析使用
- `other_message_count`
  - 用途：表示该段内对方消息数，供互动平衡分析使用
- `segment_kind`
  - 用途：表示段类型，限定为 `normal / isolated / merged_isolated`
- `source_segment_ids`
  - 用途：仅在 `merged_isolated` 时使用，表示它由哪些原始 `isolated` 段合并而成
- `source_message_ids`
  - 用途：仅在 `merged_isolated` 时使用，表示被合并的原始消息列表

### 6.5 segment_summaries

`segment_summary` 表示会话段级别的结构化理解结果。

关键字段：

- `segment_id`
  - 用途：表示该摘要对应哪个会话段
- `summary_text`
  - 用途：表示该段的自然语言摘要，供检索和人工查看
- `main_topics`
  - 用途：表示该段的主要话题标签，供主题归并使用
- `self_stance`
  - 用途：表示我方在该段中的主要立场或姿态
- `other_stance`
  - 用途：表示对方在该段中的主要立场或姿态
- `emotional_tone`
  - 用途：表示该段整体情绪基调
- `interaction_pattern`
  - 用途：表示该段互动模式，如试探、安抚、调侃、回避
- `has_conflict`
  - 用途：表示该段是否包含明显冲突
- `has_repair`
  - 用途：表示该段是否包含修复或缓和动作
- `has_closeness_signal`
  - 用途：表示该段是否包含升温或靠近信号
- `outcome`
  - 用途：表示该段是否形成结论或停留在悬而未决
- `relationship_impact`
  - 用途：表示该段对关系的影响方向
- `confidence`
  - 用途：表示系统对该摘要结果的把握程度

### 6.6 topics

`topic` 表示跨时间的长期主题主线，用于补足长期关系史。

关键字段：

- `topic_id`
  - 用途：表示一个长期主题的唯一标识
- `conversation_id`
  - 用途：表示该主题属于哪段会话
- `topic_name`
  - 用途：表示主题名称，供展示和检索使用
- `topic_summary`
  - 用途：表示该主题的长期总结，供查看与调试
- `first_seen_at`
  - 用途：表示该主题首次出现时间
- `last_seen_at`
  - 用途：表示该主题最近一次出现时间
- `segment_count`
  - 用途：表示被归入该主题的会话段数量
- `topic_status`
  - 用途：表示主题当前状态，如 `ongoing / resolved / sensitive_recurring / dormant`

### 6.7 topic_links

`topic_link` 表示会话段和主题之间的关联关系。

关键字段：

- `topic_id`
  - 用途：表示关联到哪个主题
- `segment_id`
  - 用途：表示哪个会话段属于该主题
- `link_reason`
  - 用途：表示系统为什么将该段归到这个主题
- `score`
  - 用途：表示归并匹配度，供排序和调试使用

### 6.8 persona_profiles

`persona_profile` 表示稳定人格特征和关系特定互动模式，不承载未来具体事件。

关键字段：

- `profile_id`
  - 用途：表示人格画像记录的唯一标识
- `conversation_id`
  - 用途：表示该画像属于哪段会话
- `subject_role`
  - 用途：表示这份画像描述的是 `self` 还是 `other`
- `global_persona_summary`
  - 用途：表示该角色的全局稳定人格总结
- `style_traits`
  - 用途：表示该角色的表达风格特征
- `conflict_traits`
  - 用途：表示该角色在冲突中的常见反应模式
- `relationship_specific_patterns`
  - 用途：表示该角色面对当前对象时的特定互动模式
- `evidence_segment_ids`
  - 用途：表示该画像主要参考了哪些段，供回溯与调试
- `confidence`
  - 用途：表示系统对该画像的把握程度

### 6.9 relationship_snapshots

`relationship_snapshot` 表示沿时间线滚动生成的关系状态快照。

关键字段：

- `snapshot_id`
  - 用途：表示关系快照的唯一标识
- `conversation_id`
  - 用途：表示该快照属于哪段会话
- `as_of_message_id`
  - 用途：表示该快照截止到哪条消息
- `as_of_time`
  - 用途：表示该快照对应的时间点
- `relationship_temperature`
  - 用途：表示关系整体温度
- `tension_level`
  - 用途：表示关系紧张度
- `openness_level`
  - 用途：表示彼此愿意继续聊或深入聊的程度
- `initiative_balance`
  - 用途：表示当前互动主动性主要偏向哪一方
- `defensiveness_level`
  - 用途：表示对方或双方的防御程度
- `unresolved_conflict_flags`
  - 用途：表示当前是否存在未解决的冲突点
- `relationship_phase`
  - 用途：表示关系处于升温、平稳、冷却、冲突或修复等哪个阶段
- `snapshot_summary`
  - 用途：表示对这一时点状态的短摘要

### 6.10 simulations

`simulation` 表示一次对历史消息发起的反事实推演。

关键字段：

- `simulation_id`
  - 用途：表示一次推演的唯一标识
- `conversation_id`
  - 用途：表示该推演属于哪段会话
- `target_message_id`
  - 用途：表示用户改写的是哪条原始消息
- `mode`
  - 用途：表示推演模式，是单轮还是自动短链
- `replacement_content`
  - 用途：表示用户输入的新内容
- `context_pack_snapshot`
  - 用途：表示本次推演实际使用的上下文冻结快照，便于复现
- `branch_assessment`
  - 用途：表示本次推演的状态变化判断结果
- `first_reply_text`
  - 用途：表示对方第一条回复
- `impact_summary`
  - 用途：表示这次分支短期影响说明
- `status`
  - 用途：表示推演任务当前状态
- `error_message`
  - 用途：表示推演失败时的错误信息
- `created_at`
  - 用途：表示推演创建时间

### 6.11 simulation_turns

`simulation_turn` 表示自动短链推演中的单轮结果。

关键字段：

- `simulation_id`
  - 用途：表示该轮属于哪次推演
- `turn_index`
  - 用途：表示第几轮
- `speaker_role`
  - 用途：表示这一轮是谁在说话
- `message_text`
  - 用途：表示这一轮生成的文本内容
- `strategy_used`
  - 用途：表示这一轮采用了什么策略
- `state_after_turn`
  - 用途：表示这一轮之后的临时状态变化
- `generation_notes`
  - 用途：表示这一轮的简短生成说明，供调试使用

### 6.12 analysis_jobs

`analysis_job` 表示一次异步分析任务。

关键字段：

- `job_id`
  - 用途：表示任务唯一标识
- `conversation_id`
  - 用途：表示该任务属于哪段会话
- `job_type`
  - 用途：表示任务类型，支持全量分析和局部重跑
- `status`
  - 用途：表示任务当前状态
- `current_stage`
  - 用途：表示任务执行到哪个阶段
- `progress_percent`
  - 用途：表示粗粒度进度
- `retry_count`
  - 用途：表示已重试次数
- `error_message`
  - 用途：表示失败原因
- `payload_json`
  - 用途：表示任务参数和运行上下文
- `started_at`
  - 用途：表示任务开始时间
- `finished_at`
  - 用途：表示任务结束时间

### 6.13 app_settings

`app_setting` 表示本地运行配置。

关键字段：

- `setting_key`
  - 用途：表示配置项名称
- `setting_value`
  - 用途：表示配置项值
- `is_secret`
  - 用途：表示该配置是否为敏感信息
- `updated_at`
  - 用途：表示最后修改时间

## 7. 模块一：解析与规范化

### 7.1 目标

解析模块负责将 `QQChatExporter V5` 私聊文本稳定转换为规范化消息流。

它只负责结构化，不负责主题、情绪或人格判断。

### 7.2 解析原则

- 严格保真，不在解析层去重
- 识别不了的块不丢弃，保留为 `unknown`
- 保留资源名、原始块文本和原始行号
- 支持图片资源占位参与后续上下文

### 7.3 解析策略

采用基于行的状态机按块解析：

1. 识别消息块起点：如 `某人:`
2. 读取 `时间:`
3. 读取 `内容:`
4. 读取可选资源区块
5. 遇到下一个消息块或文件结束时提交当前块

### 7.4 特殊情况

- 类似 `0:` 的异常说话人块：
  - 不强行推断身份
  - 记为 `speaker_role = unknown`
  - `message_type = unknown`
  - 保留原始内容供后续判断
- 文件头与文件尾的说明信息：
  - 识别后跳过，不写入消息表

### 7.5 失败处理

- 单条消息块解析失败，不中断整次导入
- 失败块转为 `unknown` 并保留原始文本
- 仅当整份文件完全不符合 QQ 导出格式时，导入任务失败

## 8. 模块二：分析流水线

### 8.1 总原则

- 所有状态类信息必须从前往后生成
- 每个阶段独立落库，允许重跑
- 局部失败允许降级，不导致整条链路报废

### 8.2 Stage 1：导入校验与参与者识别

导入时必须要求用户提供：

- `self_display_name`
  - 用途：明确哪一个说话人代表“我”，用于归一化 `speaker_role`

这一阶段负责：

- 校验文件格式
- 提取文件头信息
- 建立 `conversation`
- 建立 `import`
- 建立 `analysis_job`

### 8.3 Stage 2：解析与规范化

该阶段产出 `messages`，是所有后续分析的唯一输入源。

### 8.4 Stage 3：首次切分

首次切分只基于消息时间连续性形成原始会话段。

规则：

- 若相邻两条消息间隔不超过阈值，则归入同一段
- 若超过阈值，则开启新段

段类型仅允许：

- `normal`
  - 含义：正常成组消息块
  - 条件：`message_count >= 2`
- `isolated`
  - 含义：单条消息成块
  - 条件：`message_count == 1`

首次切分阶段不生成 `merged_isolated`。

### 8.5 Stage 4：相邻 isolated 合并

该阶段只处理 Stage 3 产出的 `isolated` 段。

严格规则：

- 只看段序列中连续出现的 `isolated`
- 若一串连续 `isolated` 的数量为 `1`，保持原样
- 若数量 `>= 2`，还需满足：
  - 首条消息时间到末条消息时间不超过 `24 小时`
- 满足条件时：
  - 生成一个 `merged_isolated`
  - 将这串原始 `isolated` 段替换为该合并段
  - 原始 `isolated` 段不再进入后续分析使用的最终段列表
- 若连续 `isolated` 跨度超过 `24 小时`，则不合并

### 8.6 Stage 5：会话段摘要

对最终段列表中的每个段生成结构化摘要。

摘要需要覆盖：

- 主要话题
- 双方姿态
- 情绪基调
- 互动模式
- 是否有冲突、修复或升温信号
- 对关系的影响

当前段摘要不得用于当前段中间截断点的推演上下文。

### 8.7 Stage 6：基础主题归并

将多个段的摘要弱监督归并为长期主题。

MVP 归并依据：

- 段摘要话题标签
- 关键词重叠
- 情绪与互动模式的连续性

### 8.8 Stage 7：人格与关系特定模式抽取

该阶段允许参考全量历史，但只能产出“稳定倾向”，不得带入未来具体事件。

需要分别为 `self` 与 `other` 生成画像：

- 全局人格特征
- 表达风格
- 冲突反应模式
- 关系特定互动模式

### 8.9 Stage 8：时间点关系状态快照

按时间线生成关系状态快照。

MVP 方案：

- 以“每个最终段结束时”为一个快照生成点

快照需要表达：

- 当前关系温度
- 当前紧张度
- 当前开放程度
- 当前主动性平衡
- 当前防御性
- 是否存在未解决冲突
- 当前关系阶段

### 8.10 Stage 9：可推演条件

满足以下条件即可允许发起推演：

- 消息解析完成
- 会话段切分完成
- 至少部分段摘要已完成
- 至少一份人格画像已完成
- 至少存在一个可用关系快照

## 9. 模块三：检索与上下文组装

### 9.1 目标

检索模块负责在严格时间边界内，从多层记忆中组装可推演的安全上下文。

该模块的目标不是“尽可能找更多内容”，而是：

- 不泄漏未来
- 选择最相关上下文
- 形成可复现的 `ContextPack`

### 9.2 核心子模块

- `CutoffResolver`
  - 作用：根据 `timestamp + sequence_no` 计算严格截断点
- `CurrentSegmentCollector`
  - 作用：收集目标消息所在段里、严格早于目标消息的前文
- `SameDayContextCollector`
  - 作用：收集目标消息当天更早的相邻历史段
- `TopicRebuilder`
  - 作用：基于截断点之前的历史段重建安全主题摘要
- `SnapshotResolver`
  - 作用：获取截断点之前最近的关系状态快照
- `MomentStateComposer`
  - 作用：结合当前段前文对最近快照做时点修正
- `PersonaLoader`
  - 作用：加载双方稳定人格和关系特定互动模式
- `ContextAssembler`
  - 作用：拼装最终 `ContextPack`

### 9.3 硬性防泄漏规则

- 当前段不能直接使用完整段摘要
- 长期主题不能直接使用全局主题总结
- 关系状态不能只照搬旧快照，必须结合当前段前文修正

### 9.4 规则检索顺序

1. 锁定 `conversation_id`
2. 依据 `timestamp + sequence_no` 做硬截断
3. 获取当前段前文
4. 获取当天更早相邻段
5. 获取相关长期主题
6. 获取最近关系快照和时点修正状态
7. 加载双方人格画像

### 9.5 ContextPack

`ContextPack` 是推演模块唯一输入对象。

关键字段：

- `conversation_id`
  - 用途：表示本次上下文属于哪段会话
- `target_message_id`
  - 用途：表示本次改写的原始目标消息
- `cutoff_timestamp`
  - 用途：表示时间截断点
- `cutoff_sequence_no`
  - 用途：表示同一秒内的顺序截断值
- `original_message_text`
  - 用途：表示原始那句话的文本，仅供对比与记录
- `replacement_content`
  - 用途：表示用户的新说法，是本次分支起点
- `current_segment_history`
  - 用途：表示当前段中目标消息之前的原始前文列表
- `current_segment_brief`
  - 用途：表示当前段前文的临时短摘要
- `same_day_prior_segments`
  - 用途：表示当天更早相关段的摘要列表
- `related_topic_digests`
  - 用途：表示截断安全的长期主题摘要列表
- `base_relationship_snapshot`
  - 用途：表示截断点之前最近的关系状态快照
- `moment_state_estimate`
  - 用途：表示结合当前段前文修正后的“此刻状态”
- `persona_self`
  - 用途：表示用户自己的稳定表达画像
- `persona_other`
  - 用途：表示对方的稳定表达画像
- `retrieval_warnings`
  - 用途：表示本次组装过程中产生的降级或风险提示
- `strategy_version`
  - 用途：表示当前检索策略版本，便于复现实验结果

### 9.6 related_topic_digests

关键字段：

- `topic_id`
  - 用途：表示主题标识
- `topic_name`
  - 用途：表示主题名称
- `cutoff_safe_summary`
  - 用途：表示只基于截断前历史重建的安全主题摘要
- `supporting_segment_ids`
  - 用途：表示该主题摘要依赖的历史段
- `relevance_reason`
  - 用途：表示为什么判定该主题与当前改写点相关
- `recency_score`
  - 用途：表示时间接近度得分
- `rule_match_score`
  - 用途：表示规则检索匹配分

### 9.7 moment_state_estimate

关键字段：

- `relationship_temperature`
  - 用途：表示此刻关系温度
- `tension_level`
  - 用途：表示此刻紧张度
- `openness_level`
  - 用途：表示此刻开放程度
- `initiative_balance`
  - 用途：表示当前主动性平衡
- `defensiveness_level`
  - 用途：表示此刻防御程度
- `active_sensitive_topics`
  - 用途：表示此刻被激活的敏感主题
- `state_rationale`
  - 用途：表示状态判断依据

## 10. 模块四：推演模块

### 10.1 目标

推演模块负责基于 `ContextPack` 进行反事实分支模拟。

本模块遵循两阶段原则：

1. 先判断状态变化
2. 再生成文本回复

### 10.2 核心子模块

- `CounterfactualBranchBuilder`
  - 作用：构建反事实分支起点
- `StateShiftEvaluator`
  - 作用：判断新说法带来的状态变化
- `ReplyStrategyPlanner`
  - 作用：先确定对方回复策略
- `FirstReplyGenerator`
  - 作用：生成对方第一条回复
- `ShortThreadSimulator`
  - 作用：逐轮自动推演后续若干轮对话
- `ImpactSummarizer`
  - 作用：生成短期影响说明
- `SimulationRecorder`
  - 作用：落库本次推演输入与结果

### 10.3 输入边界

推演模块只接受：

- `ContextPack`
- 推演参数：
  - `mode`
  - `turn_count`
  - `explanation_level`
  - `temperature_profile`

推演模块不直接访问数据库。

### 10.4 分支起点规则

- 历史上下文只包含目标消息之前的内容
- 原始目标消息不作为“已发生事实”喂给模型
- `replacement_content` 作为此刻刚发送的新内容进入分支

### 10.5 BranchAssessment

`BranchAssessment` 表示推演第一阶段的状态变化判断结果。

关键字段：

- `branch_direction`
  - 用途：表示这次改写后分支整体更可能朝哪个方向走
- `state_shift_summary`
  - 用途：表示新说法相较原话带来的关键状态变化说明
- `other_immediate_feeling`
  - 用途：表示对方看到新说法后的即时感受
- `reply_strategy`
  - 用途：表示对方最可能采用的回应策略
- `risk_flags`
  - 用途：表示这次分支仍存在的风险点
- `confidence`
  - 用途：表示系统对该判断的把握程度

### 10.6 GeneratedBranch

`GeneratedBranch` 表示第二阶段的文本生成结果。

关键字段：

- `first_reply_text`
  - 用途：表示对方第一条回复文本
- `first_reply_style_notes`
  - 用途：表示这条回复为何采用该语气与长度
- `simulated_turns`
  - 用途：表示自动短链推演结果列表
- `impact_summary`
  - 用途：表示该分支对短期关系走势的简短说明
- `stopping_reason`
  - 用途：表示自动短链推演为何停止

### 10.7 simulated_turns

关键字段：

- `turn_index`
  - 用途：表示第几轮
- `speaker_role`
  - 用途：表示这一轮是谁发言
- `message_text`
  - 用途：表示这一轮的生成文本
- `strategy_used`
  - 用途：表示这一轮采用的回应策略
- `state_after_turn`
  - 用途：表示这一轮之后的临时状态变化
- `generation_notes`
  - 用途：表示这一轮的简短生成说明

### 10.8 自动短链推演规则

MVP 的 `short_thread` 为自动短链推演，不等待用户逐轮输入。

但内部实现必须采用逐轮推进方式：

- 每次只生成一轮
- 每轮后更新临时状态
- 每轮结构化落库

这样可以为后续“交互式分支续聊”保留扩展路径。

### 10.9 防止无依据生成的约束

Prompt 必须明确要求模型：

- 不得引用截断点之后发生的事实
- 不得引入历史毫无痕迹的新重大事件
- 不得过度理想化人物表达能力
- 不得为了戏剧性强行反转关系
- 在上下文不足时选择更保守、更贴近历史互动密度的回复

## 11. 模块五：任务执行与运行时

### 11.1 运行形态

第一版采用两个本地进程：

- API 进程
- Worker 进程

两者共享：

- 同一套代码
- 同一份 SQLite 数据库
- 同一份本地数据目录

### 11.2 本地数据目录

建议采用以下目录结构：

- `app_data/db/`
  - 用途：存放 SQLite 数据库文件
- `app_data/uploads/`
  - 用途：存放原始导入文件
- `app_data/logs/`
  - 用途：存放 API、worker 和模型调用日志
- `app_data/cache/`
  - 用途：存放临时缓存或未来可能的向量缓存

### 11.3 配置项

MVP 重点配置：

- `llm.base_url`
  - 用途：表示模型服务地址
- `llm.api_key`
  - 用途：表示模型服务密钥
- `llm.chat_model`
  - 用途：表示聊天模型名称
- `analysis.segment_gap_minutes`
  - 用途：表示首次切段时的时间间隔阈值
- `analysis.isolated_merge_window_hours`
  - 用途：表示相邻 isolated 合并的窗口时长，MVP 固定为 24 小时
- `simulation.max_turn_count`
  - 用途：表示自动短链最大轮数

### 11.4 Worker 执行方式

MVP 的 worker 采用 DB 驱动任务执行：

1. 扫描 `queued` 任务
2. 抢占任务并标记为 `running`
3. 依次执行分析阶段
4. 每完成一阶段更新任务状态
5. 成功则标记为 `completed`
6. 失败则记录错误并标记为 `failed`

### 11.5 日志

建议日志按三类拆分：

- `api.log`
  - 用途：记录接口调用与错误
- `worker.log`
  - 用途：记录分析任务的阶段执行情况
- `llm.log`
  - 用途：记录模型调用摘要、耗时和错误

### 11.6 降级策略

分析阶段降级：

- 段摘要失败时，保留原始段供推演直接使用
- 主题归并失败时，推演仅依赖当前段、当天上下文与关系快照
- 人格画像失败时，推演退回更保守的状态驱动模式

推演阶段降级：

- 当前段临时摘要失败时，直接使用原始前文
- 主题为空时继续推演，但写入 `retrieval_warnings`
- 关系快照缺失时，临时根据最近段摘要估计简化状态

### 11.7 Windows 本地应用演进

虽然 MVP 不做前端，但当前结构已经为未来 Windows 本地应用预留了稳定基础：

- SQLite 无需额外安装数据库
- 本地数据目录可直接随应用分发
- API 可作为桌面应用本地后台
- Worker 可作为桌面应用后台任务执行器

未来新增 UI 壳时，不需要重写分析和推演内核。

## 12. 测试策略

### 12.1 解析测试

覆盖：

- 正常文本消息
- 图片资源消息
- 异常说话人块，如 `0:`
- 文件头尾跳过

### 12.2 切段测试

覆盖：

- `normal` 段识别
- `isolated` 段识别
- `merged_isolated` 合并
- `24 小时` 合并窗口边界

### 12.3 时间截断测试

验证：

- 目标消息之后的内容不会进入 `ContextPack`
- 同一秒内后续消息不会因为只比较时间而误入上下文

### 12.4 推演链路测试

使用 mock 模型响应验证：

- 从改写请求到上下文组装的链路
- 从状态判断到首轮回复生成的链路
- 自动短链逐轮推进与落库

### 12.5 人工验收

使用真实聊天历史关键节点做人审，重点观察：

- 是否严格不泄漏未来
- 是否符合当时关系状态
- 改写内容变化是否带来合理的状态变化与回复变化

## 13. 设计决策摘要

本次设计确认了以下关键决策：

- MVP 第一版为 Windows 本地后端核心，不做前端
- 技术路线为 Python + FastAPI + SQLite + 本地 Worker
- 输入格式固定为 `QQChatExporter V5` 私聊导出文本
- 非文本消息保留资源名，不做图片理解
- 导入后异步完整分析
- 检索先使用规则检索，不上 embedding
- 推演主模式为：
  - 单轮回复
  - 自动短链推演
- 自动短链内部必须逐轮推进，为未来交互式分支续聊保留扩展基础
- 首次切分只产生 `normal` 与 `isolated`
- `merged_isolated` 只在后续阶段由相邻 `isolated` 严格按 `24 小时` 窗口合并得到

## 14. 实施前检查结论

该设计已完成以下收敛：

- 明确了 MVP 范围与非范围
- 明确了输入格式与消息类型处理策略
- 明确了切段、检索、推演和本地运行的核心约束
- 明确了未来从本地后端核心演进到 Windows 应用的路径

该设计可以进入实施计划编写阶段。
