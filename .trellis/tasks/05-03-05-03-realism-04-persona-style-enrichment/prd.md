# implement realism-04 persona style enrichment

## Goal

在不新增 LLM 分析调用和不显著增加完整分析耗时的前提下，为 simulation / realtime branch 共用的 context pack 增补第一版 deterministic style profile，让回复长度、拆泡倾向、语气词/标点和压力下的表达强度更像真实对方。

## Requirements

- 基于 cutoff-safe 原消息确定性计算 `self` / `other` 的 style profile，不调用新的 LLM 分析。
- 区分全局风格与当前关系中的近期互动风格，并把结果并入 `persona_self` / `persona_other` 的 persona/style 区域。
- 为生成侧输出显式 `reply_envelope` / `generation_hints`，至少覆盖：长度上限、单泡/多泡倾向、常见语气词、常见标点、压力下表达强度边界。
- 保持 `build_conversation_context_pack()`、`session_memory_pack`、`single_reply` / `short_thread` / realtime branch 现有消费路径兼容，不新增存储表，不修改外部 API 合同。
- prompt 必须显式要求生成侧优先遵守 `persona_other` 的 deterministic style profile；`persona_self` 只用于理解，不覆盖用户实时输入。

## Acceptance Criteria

- [ ] `context_pack["persona_self"]` / `context_pack["persona_other"]` 包含 deterministic style profile，且仅使用 cutoff-safe 消息计算。
- [ ] style profile 能区分全局风格与近期互动风格，并提供可直接消费的 `reply_envelope` / `generation_hints`。
- [ ] 首轮回复、短链续写和 realtime branch reply prompt 都能拿到 other 的 style 约束。
- [ ] 偏短句、偏简短的角色，prompt 会明确限制长篇分析式回复和无限拆泡。
- [ ] `PYTHONPATH=src pytest tests/test_simulations.py tests/test_branch_sessions.py -q` 通过。
- [ ] `PYTHONPATH=src pytest -q` 通过。

## Definition of Done

- Tests added or updated where behavior changes.
- Relevant prompts and context-pack contract updated together.
- Trellis notes / PRDS updated so需求、实现和交付记录可追溯。

## Technical Approach

- 在 `src/if_then_mvp/context_builder.py` 中集中实现 cutoff-safe style profile 计算，直接复用已加载的 `Message`、`RelationshipSnapshot` 与现有敏感 topic 信号，不新增持久化模型。
- 通过扩展 `persona_to_context_dict()` 把 deterministic style profile 合并进 `persona_self` / `persona_other`，让 `src/if_then_mvp/retrieval.py`、`src/if_then_mvp/branch_sessions.py` 保持现有字段路径兼容。
- 在 `src/if_then_mvp/simulation.py` 的首轮回复、多轮续写和 realtime branch reply prompt 中显式引用 `deterministic_style_profile.reply_envelope` / `generation_hints`，用 prompt 护栏约束长度、拆泡和表达强度。
- 首版不新增前端专用拆泡协议；仍复用现有按聊天标点拆泡的 UI 逻辑，通过 prompt 把 `max_bubble_count` 约束在 2 条短泡以内。

## Decision (ADR-lite)

**Context**: `realism-04` 需要让回复“更像这个人”，但当前项目只有 LLM 归纳出来的 persona 文本，缺少可执行、低成本、cutoff-safe 的表达风格约束。  
**Decision**: 先在共享 context builder 里增加 deterministic style profile，覆盖长度、拆泡、语气词/标点和压力下强度边界，并把这些结果以内嵌字段并入 `persona_self` / `persona_other`。  
**Consequences**: generation prompt 会获得更强的风格约束且不增加分析链路成本，但首版仍主要依赖 prompt 服从，不在这一轮引入额外后处理重写器或新的持久化缓存。

## Out of Scope

- 不新增 style profile 持久化表或 analysis 阶段 LLM 调用。
- 不重写 frontend 拆泡协议或新增专门的 bubble metadata 字段。
- 不修改 `single_reply` / `short_thread` / branch session 的外部 API 结构。
- 不把 style profile 扩展为 embedding 检索或复杂序列建模。

## Technical Notes

## Relevant Specs

- `.trellis/spec/shared/code-quality.md`: 约束本轮改动保持类型明确、范围收敛，不引入模糊兜底。
- `.trellis/spec/shared/git-conventions.md`: 任务完成后保持原子提交和规范 commit message。
- `.trellis/spec/guides/cross-layer-thinking-guide.md`: context pack 新字段会跨 retrieval、simulation、branch session 边界传播，需要保持合同兼容。
- `.trellis/spec/guides/code-reuse-thinking-guide.md`: deterministic style profile 必须集中在共享 builder，避免 prompt 路径各自重算。

## Code Patterns Found

- `src/if_then_mvp/context_builder.py`: 已是 simulation / realtime branch 共用的 context-pack 装配入口，适合承接 cutoff-safe 风格统计。
- `src/if_then_mvp/simulation.py`: 所有生成 prompt 都集中在这里，适合统一接入 style envelope 护栏。
- `src/if_then_mvp/branch_sessions.py`: realtime memory pack 会把 persona 字段透传给 worker，因此风格字段应复用现有 persona 路径，避免另开合同。
- `desktop/src/lib/frontUiAdapters.ts`: branch / simulation 结果已按聊天标点拆泡，说明后端只需提供 `max_bubble_count` 约束即可先完成 MVP。

## Files to Modify

- `src/if_then_mvp/context_builder.py`: 计算 cutoff-safe deterministic style profile，并合并进 persona context。
- `src/if_then_mvp/simulation.py`: 在生成 prompt 中加入 style envelope / generation hints 约束。
- `tests/test_simulations.py`: 补 style profile 计算与 prompt 约束回归。
- `tests/test_branch_sessions.py`: 验证 realtime branch prompt 能拿到 persona_other style 约束。
- `PRDS/PRD007-人格风格增强.md`: 绑定终版 PRD 与工作记录。
