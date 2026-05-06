# brainstorm: synthetic realism fixture review

## Goal

重审 `tests/fixtures/realism_synthetic` 下三段 AI 生成的合成聊天记录，识别其时间连贯性、逻辑连贯性和真实聊天质感中的问题，并收敛出最有项目价值的可修改点，作为后续改写测试集或质量验收标准的依据。

## What I already know

* 用户明确指出三段记录目前 AI 味较重，时间连贯性和逻辑连贯性不足，不像真实聊天记录。
* 目标不是立即大规模改写，而是先重审、提出让聊天场景更真实的方法，并给出高价值修改点。
* 目标 fixtures 位于 `tests/fixtures/realism_synthetic`，包含三个 case：`case-01-hidden-trauma-confession`、`case-02-conflict-repair`、`case-03-missed-window`。
* 每个 case 当前包含 `conversation.txt`、`timeline.md`、`rewrite-points.md`、`truth-after-cutoff.md` 和 `generation-notes.md`。

## Assumptions (temporary)

* 本次 brainstorm 以分析和需求收敛为主，除任务 PRD 与 trace 记录外，暂不直接改写三段 `conversation.txt`。
* 高价值修改点需要兼顾“人读起来真实”和“仍能服务 realism roadmap 的测试目标”，不能只做文风润色。

## Open Questions

* 已确认：采用 validation-first 方向，先建立可执行真实性校验和显式 waiver，再为后续重生成/局部改写提供防回归机制。

## Requirements (evolving)

* 审阅三段聊天记录本体与配套 metadata。
* 找出破坏真实感的共性问题和每个 case 的特异问题。
* 提出可执行的改写方法，并按项目价值排序。
* 明确哪些修改能提升现有 realism 评估的有效性。
* 保留现有回归价值：三段仍需可被 `parse_qq_export()` 解析、保留 baseline 目标锚点，并继续覆盖 future evidence / cutoff-only 误判。

## Acceptance Criteria (evolving)

* [x] 三个 case 均有针对性问题诊断。
* [x] 输出至少一组共性真实性问题分类。
* [x] 输出按价值排序的修改点，说明原因、影响范围和建议做法。
* [x] 区分“可小修”和“建议重构生成方法”的范围。
* [x] 新增可运行 audit，当前 synthetic corpus 没有未豁免 finding。
* [x] 已知 corpus debt 以稳定 waiver key 记录，并由 pytest 断言。
* [x] 后续 generator 渲染不会再输出早于最后消息的 `导出时间`。

## Definition of Done (team quality bar)

* 任务发现和决策记录在本 PRD。
* `.trace/05.06.md` 记录本次 brainstorm 的关键进展。
* 若后续进入实现，再按项目工作流补充测试、文档和提交。

## Out of Scope (explicit)

* 本轮不直接提交完整 rewritten corpus，只修复不会影响 baseline target 的低风险正文/header 问题。
* 本轮不更改 provider、prompt 或评估 runner 的代码。
* 本轮不引入真实个人隐私聊天数据。

## Technical Notes

* Repository status at start: clean `main...origin/main`.
* Files to inspect: `tests/fixtures/realism_synthetic/**`.
* Related context: realism roadmap 已完成实现型阶段，当前剩余验收层关注 provider/人工拟真性验收、未来泄漏人工复核、完整分析 pipeline 性能复测。
* Current fixture tests in `tests/test_realism_synthetic_fixtures.py` only assert parser compatibility, message count, anchors, sorted timestamps, text-only messages, metadata markers, and simple PII absence.
* Current baseline tests in `tests/test_realism_baseline_fixtures.py` bind baseline targets to exact fixture message sequence/timestamp/content, so any corpus rewrite must either preserve target messages or update `tests/fixtures/realism_baseline/cases.json`.
* Generation script timestamp assignment creates 5-10 sessions per chunk and then distributes messages densely inside each session; this explains the repeated low median gap around 1.8 minutes.

## Inspection Findings

### Corpus-Level Issues

* **Time realism is too regular**: case-01 has 3523 messages across 85 active days, case-02 has 2584 messages across 51 active days, and case-03 has 2385 messages across 91 active days. Median adjacent-message gap is ~1.8 minutes in all three cases, which makes long periods read like uniformly packed chat bursts rather than real stop-start conversation.
* **Life outside the plot is thin**: the conversations mostly serve relationship beats. There are few logistics, unanswered messages, group context references, mundane obligations, screenshots/images/stickers, delayed replies with reasons, or topic residue that does not directly advance the evaluation scenario.
* **Key evidence is over-signposted**: anchors and hidden-state clues recur in clean wording, often with characters explicitly naming the issue. This improves testability but weakens realism because real signals are usually partial, awkward, contradictory, or buried in unrelated context.
* **Dialogue is too self-aware**: characters often describe their relational pattern in therapist-like summaries, for example “你现在想要我抱抱你，还是一起想办法” and “不是不能讲道理，是顺序不对”。These lines are useful as target concepts but too polished for natural historical chat.
* **Existing tests miss the main defects**: no current test catches export-time inconsistency, time-word contradictions, hidden facts revealed too early, overly dense session cadence, or over-repeated exact clue phrases.

### Case-Specific Issues

* **case-01-hidden-trauma-confession**:
  * Header export time is `2026-05-02 20:00:00`, but messages continue until `2026-05-05 22:03:04`; this is an impossible QQ export timeline.
  * The formal confession on `2026-04-22` is weakened because `我` already says `因为我喜欢你，不是要赢你` on `2026-04-20`, so the later “我喜欢你，你能不能做我女朋友” is not the first meaningful confession.
  * `别对我太好` appears many times and is repeatedly called out by `我` as “又来了”, making the supposedly weak hidden signal too explicit.
  * The post-cutoff truth line `以前那段关系让我一被确定就想逃` is a clean explanatory reveal; it should probably emerge through fragmented context, not one thesis sentence.
* **case-02-conflict-repair**:
  * The truth-after-cutoff says the family check is revealed on `2026-04-10`, but the corpus already contains `家里那个检查还没出结果` on `2026-03-29`, before the core `2026-04-08` conflict. The future evidence boundary is therefore compromised.
  * Some time semantics are inconsistent, for example `抱抱你，今天先撑过上午` appears at `2026-03-27 20:10:55`.
  * The conflict/recovery arc is too didactic: the pair quickly names “分析 / 讲道理 / 先接住 / 抱抱还是方案” as a clean rule system, which reads more like an intervention script than a messy repair.
  * `2026-04-08` contains 262 messages from morning to night, making the conflict day unusually dense and narratively exhaustive.
* **case-03-missed-window**:
  * The “深夜想你” key window happens at `2026-03-26 19:22:01`, not late night.
  * The missed windows are too explicit: `你要不要来陪我走一圈`, `这家店两个人套餐好像刚好`, and especially `如果我说我有点想你呢` are clear enough that the cutoff-only ambiguity is weaker than intended.
  * Follow-up lines such as `上次你走太慢的借口也上线了` and `稳定地绕开` make `我`'s avoidance pattern explicit too early.
  * The later reveal `后来几次也是，我不是随便问问` is useful for evaluation, but too compressed and explanatory as a real chat resolution.

## Project-Value Ranked Modification Points

1. **Add realism validation checks before rewriting full text**.
   * Why: the current tests allow impossible export time, time-word contradictions, early truth leakage, and over-signposted clues to pass.
   * Suggested checks: export time >= last message timestamp; no morning/late-night wording in incompatible hours; truth-after-cutoff anchors must not have equivalent facts before the declared reveal; repeated exact clue phrases must stay under a per-case threshold unless explicitly intentional.
   * Project value: prevents the same AI-flavored defects from returning after regeneration.
2. **Rebuild the generator around a session calendar instead of plot chunks**.
   * Why: the current chunk+target-count generation packs messages densely and linearly.
   * Suggested method: generate a private event calendar first, then derive irregular chat sessions with silence, missed replies, weekday constraints, meal/commute/work interruptions, and occasional one-sided runs; embed anchors afterward.
   * Project value: improves all three corpora and future fixture generation, not just manual polish.
3. **Redesign hidden/future evidence as dispersed, ambiguous evidence**.
   * Why: current clues and reveals are too direct, and case-02 leaks the family-check fact before the declared reveal.
   * Suggested method: maintain an evidence ledger per case with `character-known-before-cutoff`, `ambiguous-before-cutoff`, and `modeler-only-after-cutoff`; test against it.
   * Project value: directly supports realism roadmap's core contract: cutoff-only should plausibly misread, modeler-only evidence should calibrate without leaking.
4. **Manual pass over the three target arcs, not every message**.
   * Why: full manual rewrite of 8000+ messages is low leverage; the biggest damage is around anchors, reveals, and temporal seams.
   * Suggested scope: rewrite 30-80 messages around each RP/T truth reveal, plus adjust adjacent timeline metadata and baseline cases.
   * Project value: preserves performance-test volume while improving human evaluation quality.
5. **Inject controlled chat noise and off-plot texture**.
   * Why: real chat includes boring logistics and artifact references that do not always serve the plot.
   * Suggested additions: `内容: [表情]`, `内容: [图片]`, "刚开完会", "地铁没信号", "等我洗个澡", "刚看到", short unexplained topic jumps, and occasional unanswered messages. Keep them parser-safe and privacy-safe.
   * Project value: improves persona/style extraction and prevents the model from learning a too-clean relationship script.

## Feasible Approaches

**Approach A: Surgical Patch**

* How: manually fix impossible/contradictory lines, reduce repeated clue phrases, adjust the most obvious timestamps, and update affected baseline targets.
* Pros: fastest, low blast radius.
* Cons: leaves generator defects and much of the scripted feel intact.

**Approach B: Validation-First Regeneration** (Recommended)

* How: add validation rules for the realism defects above, revise generator session scheduling/evidence ledger, regenerate or selectively regenerate fixtures, then update baseline cases.
* Pros: highest long-term value; turns this review into durable project quality.
* Cons: larger change set and requires careful baseline migration.

**Approach C: Hybrid Corpus Repair**

* How: add the most important validation checks, then manually patch only RP/T windows and metadata instead of regenerating everything.
* Pros: moderate effort, improves human-readable quality near evaluation points.
* Cons: broader corpus may still feel synthetic outside reviewed windows.

## Decision (ADR-lite)

**Context**: The current synthetic corpus is useful for parser, baseline, and performance coverage, but it contains human-visible realism defects that existing tests do not catch.

**Decision**: Implement the validation-first foundation now. Add a reusable audit script, connect it to pytest, keep current known corpus debt visible through explicit waivers, and make only low-risk fixture fixes that do not move baseline targets.

**Consequences**: The corpus is not fully rewritten yet, but future regeneration or local repair now has an executable contract. Removing a waiver requires migrating the affected fixture and any baseline target that depends on it.

## Implementation Notes

* Added `scripts/validate_realism_synthetic_corpus.py`.
* Updated `tests/test_realism_synthetic_fixtures.py` to require zero unwaived findings and an exact waived-debt key set.
* Updated `scripts/generate_realism_synthetic_corpus.py` with strong time-word prompt constraints and safe export-time rendering.
* Fixed case-01 header export time and one case-02 evening/morning wording contradiction.
* Documented the audit in `docs/realism-quality-rollout.md`, `plan/realism-08-quality-and-rollout.md`, `PRDS/PRD016-语料拟真校验.md`, and `.trellis/spec/backend/quality.md`.
