# “如果那时”桌面前端产品壳改造设计

日期：2026-04-07

## 1. 目标

在已经完成的 Electron M2 桌面壳之上，把当前 `desktop/` renderer 从 boot screen + placeholder 升级为**真实可用的桌面产品前端**，打通以下主链路：

- 首次进入应用后的欢迎引导
- 模型配置
- 导入聊天记录
- 会话列表与分析状态展示
- 历史聊天浏览
- 选择历史消息进行改写与推演
- 在聊天区内查看反事实分支结果

本阶段的目标是做出 **M3：主产品流跑通**，不是最终发布版 `.exe` 打包阶段。

---

## 2. 设计边界

### 2.1 本阶段包含

- 将 `desktop/src/` 从占位界面改造成真实应用界面
- 建立 renderer 内部的数据服务层与状态分层
- 接入现有 Python API
- 将 `D:\frontUI\src` 的视觉结构转译为本项目真实产品语义
- 打通“配置 → 导入 → 分析 → 浏览 → 推演”主闭环

### 2.2 本阶段不包含

- Windows 安装器 / 自动更新 / 正式 release 打包流程
- Python 运行时内嵌分发
- 本地模型完整运行链路
- 多窗口
- 多分支树状并行推演
- 把 `D:\frontUI\src` 整包直接搬进仓库

---

## 3. 已确认产品前提

基于前序讨论，以下决策已固定：

- 桌面宿主继续使用 **Electron**
- renderer 继续使用 **React + TypeScript**
- 业务核心继续复用现有 **Python API / worker**
- 在线 API 是主路径，本地模型只预留产品入口
- 首次进入时应弹出欢迎引导
- 初始会话列表允许为空；导入聊天记录后新增联系人/会话
- 设置通过左下角入口或首次引导进入
- 主界面为三栏桌面应用结构

---

## 4. 方案比较

### 方案 A：直接把 `frontUI` 整包迁入 `desktop/`

优点：

- 最快看到“像样”的界面
- 能最大化复用现成 Figma 导出结果

缺点：

- 会一并带入 `mockData`、即时聊天器假设、无关 UI 组件与样式依赖
- renderer 会被原型结构牵着走，而不是围绕真实业务数据建模
- 后续接 API 时改造成本高

结论：

- **不采用**

### 方案 B：完全抛开 `frontUI`，从 `desktop/src` 白手重做

优点：

- 语义最干净
- 架构最容易围绕真实产品重新设计

缺点：

- 会浪费已经做好的视觉稿与成熟布局
- 首轮 UI 还原成本偏高

结论：

- **不作为推荐方案**

### 方案 C：保留 `frontUI` 作为视觉参考，重新按真实产品语义在 `desktop/` 内重建

优点：

- 既保留现有三栏视觉语言，又避免把原型代码债务直接引入产品代码
- 可以围绕真实 API、真实状态机、真实空态/错误态建立结构
- 更适合渐进接入桌面能力

缺点：

- 首轮会比直接复制更慢
- 需要明确哪些视觉元素复用、哪些交互必须重写

结论：

- **采用该方案**

---

## 5. 核心设计结论

### 5.1 不是“迁移 frontUI”，而是“用 frontUI 重新定义 desktop renderer”

`D:\frontUI\src` 的定位是：

- 提供三栏结构、颜色关系、间距、聊天视图氛围、侧边栏视觉层级
- 不提供真实业务状态设计
- 不提供真实数据模型
- 不提供可直接上线的组件边界

因此本阶段应：

- 参考其视觉骨架
- 丢弃其 `mockData`
- 丢弃其“即时发消息聊天器”假设
- 以桌面历史浏览器 + 反事实推演器的产品语义重建组件

### 5.2 首轮 renderer 不引入额外重型前端体系

当前 `desktop/` 已有最小 React + TS + CSS 结构。本阶段优先：

- 继续沿用现有工作区
- 按需增加少量本地组件、hooks、services、types
- 先把产品壳跑通

不在本阶段强行引入：

- 大型状态管理库
- 新 UI 组件库整包
- 复杂路由系统

原因：

- 当前是单窗口单主界面应用
- 主要复杂度在业务状态与桌面交互，不在页面路由
- 维持依赖克制有利于尽快闭环

---

## 6. 信息架构

主窗口仍采用三栏：

### 6.1 左栏：全局导航栏

保留 3 个首版入口：

- 会话
- 分析信息
- 设置

其中：

- “会话”是默认主入口
- “分析信息”不单独切页，而是用于打开信息侧板
- “设置”打开右侧设置抽屉

左栏底部还需要保留：

- 应用状态指示
- 设置按钮

### 6.2 中栏：会话列表栏

职责：

- 显示已导入的 conversation
- 显示联系人名、最后消息、时间、分析状态
- 提供搜索
- 提供导入按钮

状态：

- 空态：尚无聊天记录
- 分析中态：显示 `queued / running / completed / failed`
- 普通态：可点击切换会话

### 6.3 右栏：聊天主视图

包含 4 种状态：

- 未选中会话的欢迎占位态
- 历史聊天浏览态
- 分支结果浏览态
- 当前会话错误/空数据态

右栏上方需要保留：

- 当前联系人标题
- 当前分析状态
- 搜索 / 时间定位入口
- “查看分析信息”入口

---

## 7. 关键弹层与面板

### 7.1 欢迎引导弹层

触发条件：

- 没有模型配置，或
- 没有 conversation

内容：

- 产品一句话说明
- 当前缺失项提示
- `配置模型`
- `导入聊天记录`

可关闭；关闭后不阻塞使用设置入口。

### 7.2 设置抽屉

放在右侧抽屉中，至少包含：

- 在线 API 模型配置
- 本地模型占位配置
- 数据目录/桌面运行状态
- 保存动作与成功/失败反馈

### 7.3 导入弹窗

内容：

- 选择聊天文件
- 填写 `self_display_name`
- 发起导入

导入成功后：

- 立即把新会话插入列表
- 自动选中新会话
- 启动 job 轮询

### 7.4 改写推演面板

触发方式：

- 在“我发出的历史消息” hover 时展示操作入口

内容：

- 原消息
- 发送时间
- 替换文本输入区
- 模式选择（单轮 / 短链）
- 发起推演按钮

### 7.5 分析信息侧板

用于查看当前 conversation 的：

- Topics
- Persona / Profile
- Timeline Snapshot

定位是**辅助理解**，不喧宾夺主。

---

## 8. 前端模块划分

renderer 建议拆成以下层次。

### 8.1 app shell 层

职责：

- 全局布局
- boot → app ready 切换
- 首启引导判定
- 全局抽屉/弹窗开关

### 8.2 feature modules 层

按真实业务拆分：

- `bootstrap`
- `conversations`
- `messages`
- `jobs`
- `settings`
- `simulations`
- `inspector`

### 8.3 services 层

统一封装所有 HTTP 请求与桌面 bridge：

- `desktopService`
- `settingsService`
- `conversationService`
- `jobService`
- `simulationService`

约束：

- React 组件内不直写 `fetch('http://127.0.0.1:8000/...')`
- 本地服务地址只能在 service 层内部集中管理

### 8.4 types / adapters 层

职责：

- 定义 API 响应类型
- 把后端数据适配成 UI 视图模型

例如：

- conversation list item view model
- message bubble view model
- simulation branch view model

---

## 9. 状态设计

### 9.1 全局应用状态

需要维护：

- desktop service state
- 是否已完成 bootstrap
- 是否显示欢迎引导
- 设置抽屉是否打开
- 导入弹窗是否打开

### 9.2 会话域状态

需要维护：

- 会话列表
- 当前选中会话 ID
- 当前会话详情加载状态
- 每个会话对应的 job 轮询状态

### 9.3 聊天视图状态

需要维护：

- 当前消息列表
- 搜索词
- 定位目标
- hover 消息
- 当前是否在 `history` 还是 `branch`
- 当前 simulation 结果

### 9.4 信息面板状态

需要维护：

- 是否打开
- 当前 tab：`topics | persona | snapshot`
- 对应数据加载状态

### 9.5 状态策略

本阶段优先使用：

- `useState`
- `useReducer`
- 受控 hooks

只有当跨层共享状态明显失控时，再引入外部状态库。

---

## 10. 数据流设计

### 10.1 启动阶段

renderer ready 后按顺序执行：

1. 读取 desktop bridge 服务状态
2. 拉取 `/settings`
3. 拉取 `/conversations`
4. 判定是否自动打开欢迎引导

### 10.2 导入链路

1. 用户打开导入弹窗
2. 通过 desktop bridge 选择文件
3. 调用导入接口
4. 返回 conversation + job
5. 会话列表立即插入新项
6. 自动选中新会话
7. 若 job 仍在运行，则启动轮询

### 10.3 会话切换链路

1. 点击中栏会话
2. 拉取消息列表
3. 显示当前分析状态
4. 若分析已完成，允许查看信息面板与推演

### 10.4 推演链路

1. 在历史消息上点击“改写并推演”
2. 打开改写面板
3. 提交 `/simulations`
4. 返回 simulation 结果
5. 右栏切换到 `branch`
6. 展示原消息、改写内容、模拟回复与短链

### 10.5 返回历史链路

分支视图顶部必须提供：

- `返回原始历史`

点击后：

- 清空当前 branch 视图态
- 恢复历史聊天浏览态

---

## 11. `frontUI` 的具体复用策略

### 11.1 可以借鉴的内容

- 三栏整体比例
- 左侧深色导航栏视觉风格
- 中栏浅灰会话列表风格
- 右栏聊天气泡基础风格
- 桌面窗口级留白、边框、阴影关系

### 11.2 必须重做的内容

- `mockData`
- 即时发送输入框语义
- “当前活跃聊天器”式交互
- 假 unread 逻辑
- 假通讯录 / 文件 tab
- 与产品目标无关的大量通用 UI 组件

### 11.3 首版建议

首版 UI 只迁移**视觉语言**，不迁移整个组件目录。

这意味着：

- 不要把 `D:\frontUI\src\app\components\ui\` 整包复制到仓库
- 先在 `desktop/src/components/` 下构建本产品真正需要的最小组件集
- 对 `frontUI` 的参考以“看布局与样式”为主，不以“复制结构”为主

---

## 12. 组件级设计

首轮建议最少拆出以下组件：

- `AppShell`
- `SidebarNav`
- `ConversationListPane`
- `ConversationListItem`
- `ChatPane`
- `ChatHeader`
- `MessageTimeline`
- `MessageBubble`
- `ConversationEmptyState`
- `WelcomeModal`
- `ImportDialog`
- `SettingsDrawer`
- `RewritePanel`
- `AnalysisInspector`
- `AnalysisStatusBadge`

其中最关键的边界是：

- 会话列表和聊天主区分离
- 聊天主区再分历史态与分支态
- 弹层统一由 app shell 管理

---

## 13. API 接入结论

本阶段直接接现有后端接口，不新增 BFF。

首批接入：

- `GET /settings`
- `PUT /settings`
- `GET /conversations`
- `GET /conversations/{id}`
- `GET /conversations/{id}/messages`
- `GET /conversations/{id}/jobs`
- `GET /jobs/{id}`
- `POST /imports/qq-text`
- `GET /conversations/{id}/topics`
- `GET /conversations/{id}/profile`
- `GET /conversations/{id}/timeline-state`
- `POST /simulations`
- `DELETE /conversations/{id}`
- `POST /conversations/{id}/rerun-analysis`

如果个别接口字段与 UI 需要不完全匹配，则在 adapter 层做转换，不把后端响应形状直接散落到组件内部。

---

## 14. 视觉与交互原则

本产品应更像：

- Windows 桌面聊天工具
- 历史浏览器
- 反事实实验台

而不是：

- 网页后台
- 报表系统
- 通用 AI Chat App

因此界面原则为：

- 主界面始终以聊天视图为中心
- 分析信息是辅助面板，不抢主舞台
- 推演结果尽量嵌入聊天语境中显示
- 尽量少跳页，多用抽屉、弹层、侧板

---

## 15. 实施顺序

建议将前端产品壳拆成 4 个实现阶段：

### 阶段 A：App shell 与服务层

- 建立真实应用布局
- 建立 services / types / adapters
- 替换 placeholder

### 阶段 B：欢迎引导、设置、导入

- 首启判定
- 设置抽屉
- 导入弹窗
- job 轮询接线

### 阶段 C：会话列表与历史聊天浏览

- 会话列表
- 分析状态展示
- 聊天消息浏览
- 搜索/定位基础能力

### 阶段 D：推演与分析信息侧板

- 改写面板
- simulation 接入
- branch 视图
- topics/persona/snapshot 侧板

---

## 16. 测试策略

本阶段需要至少覆盖：

- service 层 API 封装测试
- adapter/view model 测试
- boot → ready → app shell 渲染测试
- 会话列表空态/加载态/分析中态测试
- 导入成功后会话插入与 job 轮询测试
- 历史视图 / 分支视图切换测试
- 设置保存与错误反馈测试

原则：

- 优先测真实产品行为
- 不围绕 `mockData` 写测试
- 不把 UI 结构测试成脆弱快照堆

---

## 17. 设计结论

下一阶段的正确方向不是“把 Figma 导出代码搬进桌面壳”，而是：

> **以 `frontUI` 作为视觉参考，在现有 `desktop/` renderer 中重建一个围绕真实 conversation、真实 job、真实 simulation 的桌面产品前端。**

这条路线能同时满足三件事：

- 保留“像 Windows 桌面应用”的视觉目标
- 避免把静态原型的结构债务带入产品代码
- 让本项目以最小依赖成本进入真正的 M3 主链路实现
