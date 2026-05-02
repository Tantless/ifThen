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
* Treat `single_reply` / `short_thread` as migration-period compatibility and regression surfaces, not the future primary experience.
* Use `persona_other` as the main generation constraint and `persona_self` as supporting context for interpreting user/self behavior.
* Support burst self messages by combining them into one reply window; if a new self message arrives before an LLM reply is committed, supersede the stale reply job and regenerate from the merged input.
* Use the committed synthetic realism corpus as the privacy-safe source for baseline evaluation samples.
* Preserve a fixed realism baseline fixture with current failure snapshots, failure taxonomy labels, and modeler-only evidence boundaries.

## Acceptance Criteria

* [x] A recommended MVP direction is selected.
* [x] `plan/TODO.md` marks the performance item complete and breaks realism into executable TODOs.
* [x] The chosen direction has explicit in-scope and out-of-scope items.
* [x] Implementation can be decomposed into small PR-sized steps.
* [x] Any realism change defines how future facts are labeled and constrained.
* [x] The recommended MVP specifies how to improve realism without adding a large full-analysis cost.
* [x] The real-time MVP defines stale reply cancellation/superseding behavior.
* [x] The realism baseline has 10+ fixed samples with cutoff, original text, rewrite, current output snapshot, and failure labels.
* [x] The baseline samples cover the current failure taxonomy and can be traced back to committed synthetic source conversations.

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
2. Active first priority: real-time branch chat as the main product direction, because it improves perceived realism and avoids asking the model to invent both sides of a long branch.
3. Active second priority: realtime-safe context and memory pack design, because long-term memory must be available without blocking every reply on heavy analysis.
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

* Status: completed with privacy-safe synthetic fixtures instead of real private conversations.
* Created 12 fixed evaluation samples from committed synthetic conversations and current simulation failure snapshots.
* Categorized failures: future fact blindness, future fact leakage, over-optimistic relationship shift, persona mismatch, unnatural verbosity, poor topic retrieval, short-thread incoherence, and relationship state jumps.
* Added regression checks around baseline fixture integrity, source-message traceability, explicit future leakage labeling, and report generation.

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
* Enforce one active LLM job per branch session; later user messages supersede stale uncommitted replies instead of spawning parallel replies.
* Track session `input_revision` so old LLM results cannot write into a newer branch state.
* Carry forward branch state after every `other` reply so each next turn starts from the latest counterfactual state.
* Persist a session-level memory pack at branch creation so each real-time reply can use stable context without re-running heavy full-analysis work.

### 6. Real-Time Branch Chat Frontend

* Replace the primary short-thread experience with an interactive branch chat view while preserving `single_reply` / `short_thread` compatibility.
* Batch user messages after a short idle window; MVP decision is 1.5 to 2 seconds, backed by stale reply superseding when users add messages during generation.
* If a new user message arrives while the LLM reply is running but not yet committed, mark that reply stale and trigger a new reply over the merged self messages.
* Show delayed split bubbles for generated `other` replies and a lightweight typing state while the LLM is waiting/generating.
* Keep all generated branch bubbles visually distinct from original timeline bubbles.

### 7. Quality Guardrails

* Future evidence leakage tests: future facts may affect risk and probability but must not appear as character-known content.
* Persona adherence tests: generated length, tone, and directness should respect persona/style constraints.
* Concurrency tests: branch session never commits stale reply jobs after `input_revision` changes.
* Regression tests for existing `single_reply` and `short_thread` behavior during migration.

## Research Notes

### What similar realtime systems suggest

* OpenAI Realtime models keep an ongoing session/conversation and support interrupting an in-progress response, including truncating assistant audio/text so the conversation state matches what the user actually observed: https://platform.openai.com/docs/guides/realtime-model-capabilities
* OpenAI Realtime cost guidance documents session truncation and retention-ratio truncation, which maps to our need for stable memory packs plus rolling transcript windows rather than sending unbounded history every turn: https://platform.openai.com/docs/guides/realtime-costs
* Google Gemini Live API documents realtime bidirectional sessions, session resumption, and context-window compression, which supports the same pattern: durable session state, resume after disconnect, and summarize older context when windows grow: https://ai.google.dev/gemini-api/docs/live
* Anthropic prompt caching guidance emphasizes keeping large reusable context stable and earlier in the prompt, with dynamic turn content later. That maps to our branch memory pack prefix plus latest transcript suffix: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching

### Mapping to this project

* The product should own durable branch memory locally. Provider session memory can be used later, but branch sessions/messages/revisions must live in SQLite so the desktop app can resume and audit behavior.
* The hot path should use cached or preassembled context: target rewrite, cutoff-safe nearby history, relationship snapshot, both personas, style stats, and selected evidence digests.
* Long-term memory should enter as compact evidence classes, not raw full history. Realtime response quality depends more on the right few constraints than on sending all messages.
* Stale replies must be guarded by data model state, not only frontend timers. The backend needs input revisions or equivalent optimistic concurrency.

## Feasible Approaches

### Approach A: Layered Evidence First, Then Real-Time Branch Chat

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

### Approach B: Real-Time Branch Chat First (Recommended)

How it works:

* Build branch sessions, append-message APIs, serial LLM jobs, and chat UI first.
* Keep existing cutoff-safe context pack initially.
* Add a session-level memory pack immediately, then enrich future evidence and style retrieval after the interaction model works.

Pros:

* Fastest path to the product direction the user described.
* Immediately avoids the biggest realism issue in short-thread mode: the model inventing both sides.
* Creates the right architecture for cancellation, interruption, and long-term memory before tuning prompts.

Cons:

* The model may still miss future objective constraints until layered evidence lands.
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
* Build the first real-time branch session backend: `BranchSession`, `BranchMessage`, `BranchReplyJob`, append self message, generate other reply, and stale reply superseding.
* Build the first real-time branch UI: rewrite enters branch chat, self messages use a 1.5 to 2 second idle window, other reply shows typing and split bubbles.
* Use the current cutoff-safe context pack plus a session-level memory pack that includes `persona_other` as primary and `persona_self` as supporting context.
* Keep future evidence modeler-only; if layered evidence is not complete in the first realtime PR, the prompt must state that no cutoff-after facts may appear as role-known content.
* Preserve `/simulations` and current desktop short-thread rendering as compatibility while the primary entry moves to branch sessions.

## Decisions

* MVP idle window: use 1.5 to 2 seconds for stronger realtime feel.
* Burst-message fallback: if the user sends another self message before an LLM reply is committed, supersede the stale reply job and regenerate from the merged self input.
* Realism baseline source: use committed synthetic conversations rather than real private chats, so the evaluation set can live in the repository.

## Implementation Status

* Performance pipeline optimization: completed.
* `realism-01-pre` synthetic corpus: completed.
* `realism-01` baseline and failure taxonomy: completed with `tests/fixtures/realism_baseline/cases.json`, `tests/test_realism_baseline_fixtures.py`, and `scripts/report_realism_baseline.py`.
* Next implementation target: `realism-06` realtime branch backend minimum loop.

## Out of Scope

* Replacing the LLM provider or model selection strategy.
* Adding embedding infrastructure in the first realism PR.
* Re-running full analysis with additional LLM stages solely for realism.
* Letting future original-timeline facts appear in generated character dialogue.
* Parallelizing LLM replies inside the same real-time branch session.
* Continuing to expand multi-turn auto-generated `short_thread` as the primary product direction.
