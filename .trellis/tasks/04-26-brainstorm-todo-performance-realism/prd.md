# Brainstorm: TODO Performance and Realism

## Goal

Discuss and prioritize the ideas in `plan/TODO.md` around reducing analysis wait time, improving simulation realism, and moving from short generated branches toward interactive counterfactual chat.

## What I Already Know

* The user's TODO has two major goals: reduce total analysis/runtime waiting time, and improve realism by using broader knowledge without violating the counterfactual cutoff.
* The current backend already has persisted messages, segments, segment summaries, topics, topic links, persona profiles, relationship snapshots, simulations, simulation turns, and queued simulation jobs.
* Full analysis is currently executed in `run_next_job()` as a mostly linear worker pipeline: parse messages, create segments, summarize each segment, resolve topics, merge topics, build persona profiles, then build relationship snapshots.
* Simulation is currently queued through `POST /simulations`, processed by `run_next_simulation_job()`, and displayed in the desktop UI only after the job completes.
* The desktop rewrite UI currently supports `single_reply` and `short_thread`, with polling every 1500 ms for simulation job progress.

## Assumptions

* The target product direction is still counterfactual conversation: users rewrite one of their own past messages and explore what might plausibly happen from that point.
* "Future objective facts" may be used as modeling evidence only if they are clearly labeled and are not treated as knowledge available to either character at the cutoff time.
* For near-term implementation, preserving cutoff safety and perceived realism is more important than maximizing raw parallelism.

## Requirements (Evolving)

* Rank the TODO ideas by product value, technical feasibility, risk, and dependency order.
* Separate low-risk performance wins from architecture-changing realism features.
* Identify which existing files and concepts would likely be affected by each implementation path.
* Preserve the distinction between cutoff-safe character knowledge and full-history modeler evidence.
* First implementation step: make long analysis jobs measurable before changing concurrency semantics.

## Acceptance Criteria (Evolving)

* [ ] A recommended MVP direction is selected.
* [ ] The chosen direction has explicit in-scope and out-of-scope items.
* [ ] Implementation can be decomposed into small PR-sized steps.
* [ ] Any realism change defines how future facts are labeled and constrained.
* [ ] Any concurrency change defines which stages are safe to parallelize and which must stay serial.

## Definition of Done

* Tests added or updated where behavior changes.
* Lint, typecheck, and relevant test suites pass.
* Docs or Trellis notes updated if the workflow or data contract changes.
* Rollback behavior considered for persisted jobs or new tables.

## Technical Notes

### Current Analysis Dependencies

* `src/if_then_mvp/worker.py` summarizes segments in a loop and passes `previous_snapshot_summary` to the next segment summary call.
* Topic resolution is sequential because each segment assignment sees the `topics_by_id` state built by earlier segments.
* Persona generation for `self` and `other` is independent after segment summaries exist.
* Relationship snapshot generation is sequential because each snapshot uses the previous snapshot summary.
* The current `topic_persona_snapshot` stage combines topic resolution, persona generation, and snapshots into one progress stage.

### Current Simulation Dependencies

* `run_next_simulation_job()` runs branch assessment, first reply, and optional short-thread generation in order.
* `SimulationTurn` persists generated turns only after the simulation completes.
* Desktop polling watches job progress and fetches the final simulation result once completed.
* Real-time counterfactual chat would need a persistent branch chat session/message model, append-message endpoints, session-scoped locking, and UI state beyond the current final-result simulation view.

### Realism Constraint

The current README and prompts emphasize not leaking future information. The user's new idea is compatible only if the system separates:

* cutoff-safe facts: known to the characters at the rewritten moment;
* future objective facts: known to the model as evidence about stable personality or future constraints, but not known to the characters;
* counterfactual branch events: generated after the rewrite and not part of the original timeline.

## Priority Decision

1. First priority: low-risk performance instrumentation around the existing worker pipeline.
2. Second priority: real-time branch chat as the main product direction, because it improves perceived realism and reduces the need for long fully-generated branches.
3. Third priority: full-history objective fact labeling, because it is valuable but high-risk and needs strict prompt/data contracts.
4. Lower priority: fully parallel snapshot generation, because current snapshots are intentionally sequential state updates.

## Implementation Step 1

Add backend worker diagnostics that persist, per analysis job:

* input size: message count and segment count;
* stage elapsed seconds for parsing, segmenting, summarizing, topic resolution, topic merge review, persona, snapshots, and finalizing;
* LLM call counts by operation type and total;
* elapsed seconds in console progress output.

This keeps the first change diagnostic-only. It does not alter segmentation, prompts, LLM behavior, or persistence schema.

## Open Questions

* After collecting real job diagnostics, which bottleneck should be optimized first: segment summary parallelism, topic resolution redesign, snapshot strategy, or segment granularity?

## Out of Scope

* Implementing code during this brainstorm.
* Replacing the LLM provider or model selection strategy.
* Building a full theme hierarchy unless selected as part of a later implementation scope.
