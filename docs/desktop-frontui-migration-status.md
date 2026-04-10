# desktop frontUI 视觉迁移状态

日期：2026-04-08  
范围：`desktop/` 渲染层主界面迁移  
原则：**视觉先统一到 frontUI，功能逐步回接；mock 只作为过渡，不在 UI 中显式标注。**

---

## 状态说明

- **Real**：前端入口与真实 desktop / backend 流程已经接通
- **Mock**：当前仍是纯占位或假数据
- **Mixed**：底层已有真实逻辑，但 frontUI 主壳里仍有 mock 过渡或入口未完全接回
- **Pending**：代码仍保留但尚未开始清理或正式切换

---

## 能力清单

| 前端入口 | 数据来源 / 实现来源 | 当前状态 | 说明 / 下一步 |
|---|---|---|---|
| 启动页 BootScreen | `desktop bridge` + 本地后端 health | Real | 保持现有桌面启动链路 |
| 欢迎引导 | settings / conversations 水位判断 | Real | 首次进入仍可引导配置模型或导入聊天 |
| 设置抽屉 | `/settings` API | Real | 功能真实可用，视觉暂沿用现有 drawer |
| 导入聊天记录 | desktop import bridge + `/imports/qq-text` | Real | 功能真实可用，frontUI 主壳已有入口 |
| frontUI 主壳 | `FrontAppShell` + `FrontSidebar` + `FrontChatList` + `FrontChatWindow` | Real | 已成为当前主聊天界面 |
| 微信式窗口壳 / Frameless window + custom title bar | Electron 无边框窗口 + 自定义标题栏 + 全窗口 frontUI 壳 | Real | 已完成 |
| 会话列表（chat tab） | `/conversations` + latest job | Real | 真实读取会话与分析状态 |
| 消息浏览 | `/conversations/{id}/messages` | Real | 右侧消息区真实显示历史消息 |
| 输入框发送 | renderer session 本地 mock state | Mixed | 当前只做本地追加，后续接真实发送 / 草稿能力 |
| 联系人 tab | `desktop/src/frontui/mockState.ts` | Mock | 后续接真实联系人 / 关系视图 |
| 文件 tab | `desktop/src/frontui/mockState.ts` | Mock | 后续接真实文件入口或替换为产品需要的能力 |
| 分析侧栏 | `/topics` / `/profile` / `/timeline-state` + 现有 inspector 逻辑 | Mixed | 已重新挂回 frontUI 主壳，并在分析完成后默认展开；后续可继续优化视觉形态 |
| 改写 / 推演 | `/simulations` + 现有 rewrite 流程 | Mixed | 已恢复从 frontUI 消息区触发；当前面板视觉仍沿用旧实现 |
| 分支视图 | branch state + simulation 结果 | Mixed | 已恢复从改写提交后进入；当前视觉仍沿用旧实现 |
| frontUI 样式管线 | Vite + Tailwind v4 + frontUI CSS 入口 | Real | 已接入并通过 build / test |
| 旧桌面壳组件 | 旧 `AppShell` / `SidebarNav` / `ConversationListPane` / `ChatPane` | Pending | 当前仍保留在仓库，待迁移稳定后清理 |

---

## 当前阶段结论

当前已经完成：

1. `desktop` 主聊天界面视觉切换到 frontUI 三栏壳
2. 真实会话列表与消息浏览已成功接回
3. 分析侧栏、改写推演、分支视图的入口已重新接回主壳
4. 欢迎引导、设置、导入等桌面主流程仍可继续使用
5. 通过文档而不是 UI 标签维护 real / mock / mixed 状态

当前尚未完成：

1. 输入区真实发送能力
2. 联系人 / 文件 tab 的真实数据接入
3. 分析 / 改写 / 分支相关面板的视觉 frontUI 化
4. 旧桌面壳组件清理

---

## 建议的后续顺序

1. 评估输入区真实发送或草稿持久化能力
2. 把联系人 / 文件 tab 从 mock 迁到真实能力
3. 将分析侧栏、改写面板、分支视图逐步 frontUI 化
4. 在迁移稳定后删除旧桌面壳组件与旧壳专属测试
