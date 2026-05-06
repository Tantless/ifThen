# brainstorm: original topic facts for branch replies

## Goal

让改写后的分支回复能够利用“原时间线同一话题中对方当时真实状态/正在做什么”作为客观参考，从而在用户把 `A: 在干嘛` 改成 `A: 在看动漫吗` 时，LLM 扮演的 `B` 能合理回答类似 `是的，你怎么知道？`，体现更接近“创世神”视角的反事实能力，同时避免把不该由角色知道的未来事实直接泄漏到台词里。

## What I already know

* 用户指出当前截断式分支让 LLM 只知道 cutoff 前聊天，导致 `B` 不知道原历史里此刻自己实际在做什么、想什么。
* 用户建议推理时把当前话题的原历史作为客观事实传给 LLM，让它理解该时间段 `B` 的实际状态。
* 已有 realism roadmap 实现过 layered evidence、future evidence、branch facts 和 modeler-only 护栏；本任务需要复用或扩展这些边界，而不是简单把未来聊天原文塞给角色。
* 期望不是让 B 机械复述原时间线，而是在反事实分支中对用户改写有“命中真实状态”的自然反应。
* 当前 `BranchSession.session_memory_pack.layered_context_pack` 只有 `cutoff_safe_facts`、`future_evidence_digests`、`branch_facts` 和 `evidence_policy`；没有“原时间线当下隐藏状态”这一层。
* `compatibility.cutoff_safe_context_pack` 会刻意排除 `future_evidence_digests`、`branch_facts` 和 `evidence_policy`，这是正确的泄漏防线，但也让 realtime branch reply 没有可台词化使用的原时间线当下事实。
* `future_evidence_digests` 目前来自 cutoff 后 `SegmentSummary + TopicLink`，用途是 modeler-only 风险/保守约束；如果直接复用为角色已知事实，会破坏既有 `realism-05` 泄漏护栏。
* realtime worker 会在创建 branch session 时冻结 `context_pack_snapshot/session_memory_pack`，后续 `run_next_branch_reply_job()` 只用该 memory pack、branch transcript、pending self 和 current branch state 生成 other 回复。因此新能力应在创建 branch session 的 context pack 阶段注入，并随 memory pack 持久化。

## Assumptions (temporary)

* “当前话题原历史”应只选取目标消息附近/同话题的有限事实，不应把整个 cutoff 后聊天都暴露给生成 prompt。
* 这些事实更像 modeler-provided objective state：可用于让 B 的内心状态和外部状态一致，但台词不能说出 B 在角色视角下不可能知道的证据来源。
* MVP 优先覆盖首条 other reply 和 realtime branch reply；多轮分支可继承同一 evidence pack。

## Open Questions

* 已回答：这些原历史事实应作为“人物彼时现实背景描述”给 LLM 做必要参考。LLM 需要知道此刻扮演的 `other` 在现实中正在做什么、正在想什么、处于什么状态；这些背景可以由后文客观事实推得，但应作为背景而不是聊天证据来源暴露。

## Requirements (evolving)

* 审阅现有 branch reply、simulation prompt、context_builder、retrieval/topic 结构。
* 识别当前截断式上下文为什么缺少“原时间线当前状态”。
* 提出 2-3 个可实施方案，比较泄漏风险、实现成本和“创世神能力感”。
* 明确 MVP 范围、验收样例和不做事项。
* 新增事实层必须能表达“other 在目标时刻或同一小话题里的客观状态”，例如正在看动漫、在路上、刚醒、情绪卡住等。
* 新增事实层不得表达或台词化后续才形成的关系结论、拒绝解释、偏好声明或原时间线后续对话内容。
* realtime branch reply prompt 必须允许这些“当下状态事实”影响 other 的私有状态和自然回复，但禁止引用证据来源、原时间线、cutoff 后原文。
* 这层事实的产品语义是“background reference for the character's real moment”，不是 `cutoff_safe_facts`，也不是普通 `future_evidence_digests`。
* 背景描述可包含两类内容：现实活动/处境（正在看动漫、在外面、忙作业）和当时脑内关注点/情绪状态（正在纠结某事、还没从上一件事缓过来），但必须由近目标后文客观事实支撑。
* 台词生成时，LLM 可以把这些背景当成 `other` 的私有现实状态来回应用户命中的内容；例如用户改成“在看动漫吗”，而背景显示 other 正在看动漫时，回复可以自然承认并带一点惊讶。
* 背景事实不能作为台词的直接依据被复述、引用或解释来源；它只用于帮助 LLM 理解 `other` 此刻处境、注意力、情绪底色和反应合理性。
* 若背景事实没有被用户当前 self 输入自然触发，LLM 不应主动把该背景说出来。

## Acceptance Criteria

* [x] 明确需要新增/复用的数据结构位置。
* [x] 明确原历史事实的检索窗口和预算策略。
* [x] 明确 prompt 中角色可知信息 vs modeler-only 客观事实边界。
* [x] 给出推荐技术方案和小 PR 实施计划。
* [x] 实现后，动漫样例中 branch reply prompt 能包含 `other_current_activity` / `other 此刻在看动漫` 这类事实，并允许回复 `是的，你怎么知道？`。
* [x] 实现后，已有 future evidence 泄漏测试仍能证明拒绝、边界、关系结论不会进入角色台词。

## Definition of Done (team quality bar)

* [x] PRD 记录需求、方案、决策和验收标准。
* [x] `.trace/05.06.md` 记录本次 brainstorm 与实现进展。
* [x] 补充后端测试，验证目标动漫类样例和 future leakage 护栏。
* [x] 完整后端 pytest 通过。

## Out of Scope (explicit)

* 不把完整 cutoff 后原文无筛选暴露给 LLM。
* 不改变“LLM 只生成 other”的 realtime 分支原则。
* MVP 不做全量长程心理状态推断，不引入新的数据库表或长期记忆模型。
* MVP 不让模型改写/补写 self 消息，也不让 branch 自动追随原时间线后续剧情。

## Technical Notes

* Repository status at start: clean and synced with `origin/main`.
* Related user example: original `A: 在干嘛` / `B: 在看动漫`; rewrite `A: 在看动漫吗`; ideal `B: 是的，你怎么知道？`.
* Files to inspect: `src/if_then_mvp/context_builder.py`, `src/if_then_mvp/retrieval.py`, `src/if_then_mvp/simulation.py`, `src/if_then_mvp/branch_sessions.py`, `src/if_then_mvp/worker.py`, and related tests.
* `src/if_then_mvp/context_builder.py` already knows target segment and topic ids. This is the right place to load a new near-target original-timeline fact layer.
* `src/if_then_mvp/retrieval.py::build_context_pack()` is the right place to expose the new field in top-level context, `evidence_policy`, `retrieval_trace`, `retrieval_budget`, and `retrieval_warnings`.
* `src/if_then_mvp/branch_sessions.py::_build_session_memory_pack()` should carry the new field under `layered_context_pack` but should not add it to `compatibility.cutoff_safe_context_pack` unless its policy is explicitly separate from character-known cutoff-safe facts.
* `src/if_then_mvp/simulation.py::_build_branch_reply_prompt()` currently says cutoff-after evidence can only affect risk/conservatism. It will need a new subsection for “objective moment facts” with narrower permissions.

## Research Notes

### Root Cause

The current evidence model has a missing middle category:

* `cutoff_safe_facts`: known before the rewritten self message, safe for character context.
* `future_evidence_digests`: after cutoff, modeler-only, safe only for risk and conservatism.
* `branch_facts`: facts created inside the live branch.

The desired case is neither generic future evidence nor normal cutoff-safe fact. `B 在看动漫` is a fact about B's private present state at the moment being rewritten. It may be unknown to A, but it is known to B. The product needs a dedicated “objective moment state” layer.

### Feasible Approaches

**Approach A: Re-label selected future evidence in prompt only**

* How it works: keep data structures unchanged, add prompt text telling the model that very near same-topic future evidence may describe B's state.
* Pros: lowest implementation cost.
* Cons: high semantic ambiguity. It weakens existing future leakage guardrails because `future_evidence_digests` currently also contains later rejection, preferences and relationship outcomes.

**Approach B: Add `objective_moment_facts` layer** (Recommended MVP)

* How it works: during context building, select a small near-target original-timeline window from the target segment and immediately following same-topic/nearby messages. Convert only present-state facts into structured facts with policy `may_inform_other_private_state_not_source_disclosure`. Carry it through `context_pack`, `session_memory_pack`, retrieval trace/budget and branch reply prompt.
* Pros: preserves existing future evidence boundary while giving B access to what B objectively was doing/feeling then. Easy to test with deterministic fixtures.
* Cons: first version needs careful heuristics/window limits and may miss some subtle states unless summaries or an extractor improve later.

**Approach C: Add an LLM hidden-state extractor**

* How it works: create a separate extraction step that summarizes “other's private state at the target moment” from nearby original messages and summaries, with labels for usable vs modeler-only facts.
* Pros: best long-term quality and can capture feelings/intent not explicit in one message.
* Cons: slower, introduces another provider call, more failure modes, and needs stronger evals before being trusted.

## Recommended MVP

Use Approach B.

Add a new context field tentatively named `objective_moment_facts`. Product semantics: this is a background description of the character's real situation at that moment, used to help the LLM inhabit `other`, not a transcript that characters cite and not direct material for dialogue.

```json
{
  "source_scope": "original_timeline_near_target_window",
  "use_policy": "background_reference_for_other_private_moment_not_source_disclosure",
  "facts": [
    {
      "fact_kind": "other_current_activity",
      "speaker_role": "other",
      "fact_text": "other 此刻正在看动漫",
      "confidence": "high",
      "supporting_message_ids": [123],
      "time_relation_to_target": "immediate_after_target_same_segment"
    }
  ]
}
```

Suggested extraction budget for MVP:

* Target segment messages after the rewritten self message, capped at 8 messages or 10 minutes.
* If target segment after-window is empty, optionally inspect the next segment only when it starts within 10 minutes and shares at least one target topic id.
* Prefer `other` messages and short self/other adjacency that reveals other state.
* Exclude facts whose kind is later relationship outcome, future preference/拒绝, meta explanation, or long-term conclusion.
* Keep fact text as compact background statements rather than original-message quotes.

Prompt policy:

* May use these facts as `other`'s private current reality/background.
* May answer naturally when self happens to name that state, e.g. “是的，你怎么知道？”
* Must treat the facts as situation/background only, not as phrases to quote, paraphrase or explain.
* If user input does not naturally touch the background, do not proactively reveal it.
* Must not mention “原时间线/证据/后面你说过/我之后才说”等来源。
* Must not force later original timeline events into branch after the immediate reply.

## Decision (ADR-lite)

**Context**: The existing cutoff model prevents future leakage but makes realtime branch replies blind to the character's real present state. This damages the “创世神能力感” when a rewrite directly touches what `other` was actually doing or thinking.

**Decision**: Add a separate `objective_moment_facts` layer as character-moment background. It may inform `other`'s private reality, attention and immediate response, but it must not be treated as dialogue source material, is not exposed as a source, is not mixed into cutoff-safe facts, and is not used to import future relationship outcomes.

**Consequences**: This preserves the current future evidence guardrail while enabling more realistic “you guessed my real state” replies. The MVP should start with a small near-target window and structured facts; a later version can add an LLM extractor if deterministic heuristics miss subtle thoughts.

## Implementation Plan

* [x] PR1: add `objective_moment_facts` plumbing in context builder/retrieval/memory pack, with retrieval trace and budget.
* [x] PR2: update realtime branch reply prompt to distinguish objective moment facts from modeler-only future evidence.
* [x] PR3: add regression tests for the anime case and for preserving future evidence leakage guardrails.

## Implementation Summary

Implemented.

* `src/if_then_mvp/context_builder.py` now extracts objective moment facts from target-segment messages after the rewritten self message, capped to a near-target 8-message / 10-minute window; if needed, it can inspect the next same-topic segment within the same window.
* `src/if_then_mvp/retrieval.py` exposes `objective_moment_facts` in the context pack, evidence policy, retrieval trace and retrieval budget.
* `src/if_then_mvp/branch_sessions.py` persists the new layer under `session_memory_pack.layered_context_pack` while keeping it out of `compatibility.cutoff_safe_context_pack`.
* `src/if_then_mvp/simulation.py` adds realtime branch prompt guardrails that treat objective moment facts as other-background only, not as dialogue source material.
* `tests/test_branch_sessions.py` adds the anime regression through the real API/worker path and preserves future evidence modeler-only checks.
* `tests/test_retrieval.py` updates the context-pack contract for the new trace/budget slot.
