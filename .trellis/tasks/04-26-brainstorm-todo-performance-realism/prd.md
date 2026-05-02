# Brainstorm: TODO Performance and Realism

## Goal

Discuss and prioritize the ideas in `plan/TODO.md` around reducing analysis wait time, improving simulation realism, and moving from short generated branches toward interactive counterfactual chat. The performance portion is now treated as completed; the active brainstorm focus is improving realism without materially increasing the full analysis pipeline time.

## What I Already Know

* The user's TODO has two major goals: reduce total analysis/runtime waiting time, and improve realism by using broader knowledge without violating the counterfactual cutoff.
* The first performance implementation has already landed: bounded LLM concurrency, parallelized downstream branches, structured progress, and a 5000-message retest showing 52.51% lower total analysis time than the old chain.
* The current backend already has persisted messages, segments, segment summaries, topics, topic links, persona profiles, relationship snapshots, simulations, simulation turns, and queued simulation jobs.
* Simulation is currently queued through `POST /simulations`, processed by `run_next_simulation_job()`, and displayed in the desktop UI only after the job completes.
* Current simulation context retrieval is strictly cutoff-safe: `_load_related_topic_digests()` only returns topic evidence from segments ending before the target message.
* `build_context_pack()` already has a clean boundary for assembling current segment history, same-day prior segment digest, related topic digests, base relationship snapshot, and persona profiles.
* Persona profiles are currently generated from all segment summaries in the analysis job, but the prompt and retrieval contract do not separate full-history stable evidence from cutoff-time character knowledge.
* The desktop adapter already splits generated simulation text into multiple chat rows, but it displays final results after job completion and does not model delayed sending, typing state, or user input batching.

## Assumptions

* The target product direction is still counterfactual conversation: users rewrite one of their own past messages and explore what might plausibly happen from that point.
* Future objective facts may be used as modeling evidence only if they are clearly labeled and are not treated as knowledge available to either character at the cutoff time.
* For near-term implementation, preserving cutoff safety and perceived realism is more important than adding more raw analysis work.
* The next realism work should reuse existing analysis artifacts first: messages, segment summaries, topics, persona profiles, and relationship snapshots.

## Requirements

* Mark the performance TODO complete and preserve its completion record.
* Break the realism TODO into PR-sized implementation tasks.
* Preserve the distinction between cutoff-safe character knowledge, full-history modeler evidence, and counterfactual branch facts.
* Treat future original-timeline facts as modeler-only evidence, never as character-known facts or directly quotable reply content.
* Prefer retrieval-time ranking and deterministic style statistics over adding new LLM-heavy analysis stages.
* Move the primary product experience toward real-time branch chat where the user writes `self` messages and the LLM only writes `other` messages.

## Acceptance Criteria

* [ ] A recommended MVP direction is selected.
* [ ] `plan/TODO.md` marks the performance item complete and breaks realism into executable TODOs.
* [ ] The chosen direction has explicit in-scope and out-of-scope items.
* [ ] Implementation can be decomposed into small PR-sized steps.
* [ ] Any realism change defines how future facts are labeled and constrained.
* [ ] The recommended MVP specifies how to improve realism without adding a large full-analysis cost.

## Definition of Done

* Tests added or updated where behavior changes.
* Lint, typecheck, and relevant test suites pass.
* Docs or Trellis notes updated if the workflow or data contract changes.
* Rollback behavior considered for persisted jobs or new tables.

## Technical Notes

### Current Analysis Dependencies

* `src/if_then_mvp/worker.py` summarizes segments with bounded concurrent LLM calls and persists `SegmentSummary` rows.
* Topic resolution still depends on sequentially built `topics_by_id` state.
* Persona generation for `self` and `other` is independent after segment summaries exist and currently consumes all segment summaries.
* Relationship snapshot generation is still a serial branch because each snapshot uses the previous snapshot summary.
* The completed performance work already lets topic/persona and snapshot branches progress concurrently under the global LLM limiter.

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

1. Completed priority: performance pipeline optimization and diagnostics.
2. Active first priority: layered evidence retrieval for realism, because it can reuse existing analysis outputs and should not materially slow full analysis.
3. Active second priority: real-time branch chat as the main product direction, because it improves perceived realism and avoids asking the model to invent both sides of a long branch.
4. Active third priority: deterministic style/persona enrichment, because it can make replies more like the real person without extra LLM analysis stages.
5. Lower priority: embedding-based retrieval, because it adds dependency/index complexity and should wait until structured topic/snapshot retrieval proves insufficient.

## Implementation Step 1

Add backend worker diagnostics that persist, per analysis job:

* input size: message count and segment count;
* stage elapsed seconds for parsing, segmenting, summarizing, topic resolution, topic merge review, persona, snapshots, and finalizing;
* LLM call counts by operation type and total;
* elapsed seconds in console progress output.

Status: completed in the performance task and recorded in `plan/TODO.md`.

## Realism Decomposition

### 1. Realism Baseline and Failure Taxonomy

* Create a small fixed evaluation set from real imported conversations and current simulation outputs.
* Categorize failures: future fact blindness, future fact leakage, over-optimistic relationship shift, persona mismatch, unnatural verbosity, poor topic retrieval, and short-thread incoherence.
* Add regression checks around prompt/context packs where possible, especially for future fact leakage.

### 2. Layered Evidence Context Pack

* Extend the simulation context pack with explicit evidence classes:
  * `cutoff_safe_facts`: events and summaries before the target message, character-knowable.
  * `future_evidence_digests`: original-timeline facts after the target message, modeler-only evidence.
  * `branch_facts`: generated events after the rewrite inside the counterfactual branch.
* Retrieve future evidence from existing segment summaries, topics, and snapshots instead of running new full-analysis LLM work.
* Add prompt contracts that future evidence can adjust probability, risk, confidence, and conservatism, but cannot be quoted or treated as something the character knows.

### 3. Retrieval Ranking and Budgeting

* Rank evidence by topic overlap, relationship-state relevance, sensitivity, target-time proximity, and whether it describes a stable preference or one-off event.
* Enforce per-class token budgets so current segment history and cutoff-safe state remain dominant.
* Keep embedding retrieval out of the MVP unless structured retrieval cannot find relevant evidence.

### 4. Persona and Style Enrichment

* Keep full-history persona as stable modeling evidence, but add cutoff-time persona slices or labels where needed.
* Add deterministic style statistics from messages: average length, short-message ratio, punctuation/emoji/particle habits, burst sending tendency, and response delay buckets.
* Attach evidence IDs to persona/style constraints so simulation prompts can cite compact, relevant support instead of broad summaries.

### 5. Real-Time Branch Chat Backend

* Add persistent branch session and branch message records linked to the target message and rewrite.
* Add append-message endpoints where the user can only add `self` messages and the LLM job only appends `other` messages.
* Enforce one active LLM job per branch session; later user messages wait for the next input window instead of spawning parallel replies.
* Carry forward branch state after every `other` reply so each next turn starts from the latest counterfactual state.

### 6. Real-Time Branch Chat Frontend

* Replace the primary short-thread experience with an interactive branch chat view while preserving `single_reply` / `short_thread` compatibility.
* Batch user messages after a short idle window, currently proposed as 5 seconds.
* Show delayed split bubbles for generated `other` replies and a lightweight typing state while the LLM is waiting/generating.
* Keep all generated branch bubbles visually distinct from original timeline bubbles.

### 7. Quality Guardrails

* Future evidence leakage tests: future facts may affect risk and probability but must not appear as character-known content.
* Persona adherence tests: generated length, tone, and directness should respect persona/style constraints.
* Concurrency tests: branch session rejects or queues overlapping LLM reply jobs.
* Regression tests for existing `single_reply` and `short_thread` behavior during migration.

## Feasible Approaches

### Approach A: Layered Evidence First, Then Real-Time Branch Chat (Recommended)

How it works:

* First, add future-evidence retrieval and prompt constraints to the existing simulation flow.
* Then add deterministic persona/style statistics.
* Finally build persistent real-time branch chat on top of the improved context pack.

Pros:

* Improves realism early without taking on the full chat architecture immediately.
* Reuses existing artifacts and avoids new full-analysis LLM stages.
* Reduces leakage risk before future evidence reaches the interactive UI.

Cons:

* Users still experience the old short-thread flow until the branch chat PRs land.
* Requires careful tests around evidence labels and prompt wording.

### Approach B: Real-Time Branch Chat First

How it works:

* Build branch sessions, append-message APIs, serial LLM jobs, and chat UI first.
* Keep existing cutoff-safe context pack initially.
* Add future evidence and style retrieval after the interaction model works.

Pros:

* Fastest path to the product direction the user described.
* Immediately avoids the biggest realism issue in short-thread mode: the model inventing both sides.

Cons:

* The model may still miss future objective constraints at first.
* Larger backend/frontend surface area before the leakage contract is hardened.

### Approach C: Retrieval and Persona Only

How it works:

* Upgrade context retrieval, future evidence labels, and persona/style constraints.
* Keep `single_reply` / `short_thread` as the only simulation modes for now.

Pros:

* Smallest architectural change.
* Best for validating whether context quality alone improves realism.

Cons:

* Does not solve the core issue that long branch conversations are model-authored on both sides.
* Less aligned with the desired real-time conversation product direction.

## Recommended MVP Scope

* Mark the performance TODO complete.
* Define and test the layered evidence contract.
* Add retrieval-time future evidence digests from existing topics/segment summaries/snapshots.
* Update simulation prompts to use future evidence only as modeler-only constraints.
* Add deterministic style statistics if it can be implemented without extra LLM calls.
* Create the first backend shape for real-time branch sessions, but keep full UI migration as a follow-up if scope needs to stay small.

## Open Questions

* Which MVP direction should be selected: Approach A layered evidence first, Approach B real-time branch chat first, or Approach C retrieval/persona only?

## Out of Scope

* Replacing the LLM provider or model selection strategy.
* Adding embedding infrastructure in the first realism PR.
* Re-running full analysis with additional LLM stages solely for realism.
* Letting future original-timeline facts appear in generated character dialogue.
* Parallelizing LLM replies inside the same real-time branch session.
