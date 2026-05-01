# brainstorm: TODO performance report solution

## Goal

Analyze the first item in `plan/TODO.md` against the real 5,000-message worker performance report, then converge on a practical solution for reducing analysis time, inference time, and user-visible waiting time.

## What I already know

* The user wants the solution to be based on `docs/analysis-performance-5000-20260426.md`.
* `plan/TODO.md` first item says the current pipeline is too linear for large histories: coarse time segmentation -> LLM segment analysis -> LLM topic aggregation -> topic analysis -> time-window snapshots.
* The TODO proposes parallelizing per-topic/per-segment analysis, branching `2 -> 3 -> 4` and `2 -> 5`, and parallelizing topic analysis plus snapshot generation.
* The 5,000-message report measured 1204.812 seconds wall-clock time with 157 total LLM calls.
* The top stages were `topic_resolution` at 446.489 seconds, `summarizing` at 374.135 seconds, and `snapshots` at 330.114 seconds; together they accounted for 95.51% of runtime.
* Parsing and segmenting were effectively not bottlenecks in the report.
* The report also identified a progress-display bug: progress reached about 97% after parsing/segmenting even though about 20 minutes of model work remained.
* Current git state is dirty and `main` is ahead 1 / behind 9 relative to `origin/main`; this brainstorm should avoid touching unrelated work.

## Assumptions (temporary)

* The target solution should prioritize an implementable MVP rather than a full redesign of the analysis model.
* Existing snapshot and summary dependencies may be stricter than the TODO assumes; code inspection is needed before selecting a safe concurrency design.
* User-facing progress accuracy is part of the solution because the report explicitly calls it out.

## Open Questions

* Which MVP scope should be chosen after we compare the feasible approaches?

## Requirements (evolving)

* Base recommendations on the measured stage timing and call counts from the performance report.
* Identify which TODO concurrency ideas are safe, unsafe, or need dependency changes.
* Produce at least two feasible implementation approaches with trade-offs.
* Include a progress-reporting fix in the recommended scope unless explicitly excluded.
* Treat `topic_resolution` as the highest-value backend bottleneck because it was the largest measured stage.
* Treat progress weighting as an MVP requirement because the current unit model makes parsing dominate the progress percentage even though parsing is not the runtime bottleneck.
* Segment summary should not remain serial; the user confirmed the summary step does not need to wait for the previous segment.
* After segment summaries are complete, the user agrees the topic/persona path and snapshot path can be split into parallel branches.
* Replace the always-visible analysis progress bar with a compact clickable progress/status area that shows the active step and that step's percent.
* Clicking the compact progress/status area should open a modal listing every analysis step and its completion state; the currently running step should have its own progress bar.
* The detail modal must support multiple stages being `running` at the same time, because the post-summary topic/persona branch and snapshot branch can run concurrently.

## Acceptance Criteria (evolving)

* [x] The proposed solution directly addresses the largest measured bottlenecks.
* [x] The proposal distinguishes safe parallelism from dependency-breaking parallelism.
* [x] The proposal defines an MVP implementation path that can be verified with tests and a repeat performance run.
* [x] The proposal includes expected impact and residual risks.
* [x] Segment summaries no longer depend on the previous segment summary in worker execution.
* [x] Worker progress payload includes structured per-stage progress data.
* [x] Frontend analysis progress UI no longer shows an always-visible horizontal progress bar.
* [x] Progress detail UI supports multiple running stages.

## Definition of Done (team quality bar)

* Tests added/updated if implementation changes behavior.
* Lint / typecheck / relevant test suite green.
* Docs/notes updated if analysis behavior or user-visible progress changes.
* Rollout/rollback considered if risky.

## Out of Scope (explicit)

* Implementing the optimization during this brainstorm step.
* Rewriting the product's analysis semantics without a separate requirements decision.

## Technical Notes

* Inspected `plan/TODO.md`.
* Inspected `docs/analysis-performance-5000-20260426.md`.
* Inspected `src/if_then_mvp/worker.py`: the analysis pipeline is currently implemented in one synchronous `run_next_job` flow.
* Inspected `src/if_then_mvp/analysis.py`: summary, topic assignment, topic creation, topic merge, persona, and snapshot prompts are separate synchronous LLM calls.
* Current progress total is `message_count + (4 * segment_count) + 3`, so a 5,000-message / 47-segment run reports roughly 97% complete after parsing and segmenting even though most wall-clock time remains.
* `summarizing` is serial because `build_segment_summary` receives `previous_snapshot_summary`; the current code passes the previous segment summary into that parameter.
* `topic_resolution` is serial because every segment assignment depends on the current in-memory `topics_by_id` catalog, and topic creation mutates that catalog.
* `snapshots` is serial because each `build_snapshot_payload` call receives `prior_snapshot`.
* `persona` generation for `self` and `other` is independent after summaries exist.
* The LLM client is synchronous but stateless enough for bounded thread-pool calls because each transport call creates its own `httpx.Client`.
* Implemented `IF_THEN_ANALYSIS_LLM_MAX_CONCURRENCY` with a default of 4 for bounded summary/persona LLM concurrency.
* Implemented structured `progress.stages` in worker payloads and exposed it through `JobRead.stages`.
* Implemented concurrent segment summary generation and a post-summary branch where snapshot generation runs on a background thread while topic/persona work continues on the main thread.
* Implemented the compact clickable frontend progress entry and detail modal in `desktop/src/frontui/ChatWindow.tsx`; list progress is now text-only.
* Validation passed for full Python tests and targeted frontend tests; full desktop typecheck/build is blocked by pre-existing conflict markers in `desktop/src/lib/services/conversationService.ts`.
* Review follow-up: summary generation now submits only a bounded in-flight window and cancels unfinished summary futures after the first failure.
* Review follow-up: analysis LLM calls now share a single concurrency limiter across summary, topic resolution, persona, and snapshot branches so `IF_THEN_ANALYSIS_LLM_MAX_CONCURRENCY=1` is honored globally.

## User Feedback

* 2026-04-30: User agreed that segment summaries do not need to be serial.
* 2026-04-30: User agreed that splitting the post-summary pipeline into topic/persona and snapshot branches is correct.
* 2026-04-30: User asked for clearer explanations of progress weighting, topic-resolution dependency, and snapshot dependency.
* 2026-04-30: User accepted the topic-resolution and snapshot dependency judgments.
* 2026-04-30: User proposed a frontend progress design: no always-visible progress bar in the analysis area; show current step and percent, and open a modal on click with all step statuses plus a dedicated progress bar for the active step.
* 2026-04-30: User confirmed the modal can show multiple stages as running simultaneously, each with its own progress bar.

## Progress UI Proposal

### Compact analysis area

* Show a status label such as `摘要生成 18/47 · 38%` or `关系快照 7/47 · 15%`.
* Do not show a horizontal progress bar in the always-visible header/list area.
* Make the whole area clickable with hover and focus states.
* Use `current_stage_percent` as the visible percent, not the old misleading overall percentage.
* For failed jobs, show failed state text and allow the same click target to open details.

### Detail modal

* Display a fixed ordered stage list:
  * 数据清洗
  * 对话分段
  * 片段摘要
  * 话题整理
  * 人设归纳
  * 关系快照
  * 完成
* Each stage should show one of: waiting, running, completed, failed.
* Running stages should show visible progress bars; multiple running stages are allowed.
* Completed stages should show completed counts or timestamps if available.
* Pending stages should show planned work count when available; otherwise show waiting.
* The modal should rely on structured job progress data, not parse human-readable `status_message` strings.

### Backend data implication

* Current `JobRead` exposes only the active stage plus aggregate unit counts.
* Current `topic_persona_snapshot` collapses topic resolution, persona, and snapshots into one backend stage.
* To support the modal robustly, add structured stage progress to `job.payload_json["progress"]`, for example a `stages` array with stable IDs, labels, status, completed units, and total units.
* The frontend can still keep `current_stage_percent` for the compact entry, but the modal should read the stage list.

## Research Notes

### Constraints from the measured report

* 5000 messages -> 47 segments -> 157 LLM calls -> 1204.812 seconds.
* The top three stages were `topic_resolution` (446.489s), `summarizing` (374.135s), and `snapshots` (330.114s).
* Pure parsing/segmentation is not worth optimizing first.
* The progress bar currently overweights message parsing and underweights LLM work.

### Constraints from current code

* Safe direct parallelism is limited: `persona self/other` can be parallelized without semantic changes, but it only saves about one persona call's wall time.
* Summary parallelism requires deciding that segment summaries should be local segment extraction rather than continuity-aware relationship-state updates.
* Topic-resolution parallelism requires changing the algorithm, not just wrapping the existing loop in threads.
* Snapshot parallelism conflicts with the current continuous-state prompt unless snapshot semantics change to independent window snapshots plus a later reconciliation pass.

### Feasible approaches here

**Approach A: Progress + branch pipeline + limited safe concurrency**

* How it works: fix progress units around expected LLM work; after summaries finish, run topic/persona path and snapshot path concurrently; parallelize `persona self/other`; keep topic resolution and snapshot internals serial.
* Pros: lowest semantic risk; directly implements the TODO's `2 -> 3 -> 4` and `2 -> 5` branch idea; likely cuts the measured run from about 1205s to about 875s before any prompt redesign.
* Cons: does not solve the biggest stage (`topic_resolution`) and leaves summary calls serial.

**Approach B: Independent segment summaries + branch pipeline + progress fix** (Recommended MVP)

* How it works: make `segment_summary` depend only on the current segment; run summaries with bounded concurrency; after all summaries finish, branch topic/persona and snapshots concurrently; keep snapshots serial; keep topic resolution serial for the first MVP.
* Pros: large measured win with contained semantic change; preserves snapshot continuity where the relationship-state dependency belongs; avoids risky concurrent mutation of `topics_by_id`.
* Cons: summary prompt semantics change and need regression tests; topic resolution remains the largest remaining bottleneck.

**Approach B+UI: Independent segment summaries + branch pipeline + structured progress modal** (Current recommended MVP)

* How it works: Approach B plus structured per-stage progress data and the compact clickable progress UI/modal described above.
* Pros: reduces real waiting time and fixes perceived progress honesty at the same time; keeps the visible UI calmer than a constantly filling global bar.
* Cons: requires both backend progress payload changes and frontend UI/tests.

**Approach C: Batch/topic-induction redesign**

* How it works: replace rolling per-segment topic assignment/creation with chunked global topic induction: summarize segments, ask the model to propose a topic catalog and segment-topic links for a chunk, then merge chunk catalogs.
* Pros: directly attacks the largest measured stage and can reduce call count more than concurrency alone.
* Cons: bigger algorithm change; token limits and chunk merge quality become core risks; harder to verify quickly.

**Approach D: Parallel snapshot windows**

* How it works: generate independent snapshots per coarse time window or key event, then reconcile them into a chronological state chain.
* Pros: can reduce the 47 serial snapshot calls or parallelize them.
* Cons: changes relationship-state semantics and risks lower realism; better as a later realism/performance redesign than the first MVP.
