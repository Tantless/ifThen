# Brainstorm: realism-02 layered evidence context

## Goal

Define the next roadmap step after realtime branch chat by extending the context contract so the system can represent three evidence layers explicitly: cutoff-safe character-known facts, future original-timeline modeler-only evidence, and facts generated inside the counterfactual branch. The immediate goal is to land a realistic, testable MVP boundary for `realism-02` without silently drifting into the broader prompt-guardrail or retrieval-ranking tasks.

## What I Already Know

* The current roadmap has a minor ordering mismatch: `plan/TODO.md` still mentions realtime prompt guardrails in the first enhancement batch, but both `AGENTS.md` and `plan/realism-00-roadmap.md` mark `realism-02` as the next step to execute now.
* `src/if_then_mvp/retrieval.py` already provides a single `build_context_pack()` boundary, but it only emits cutoff-safe fields such as `current_segment_history`, `same_day_prior_segments`, `related_topic_digests`, `base_relationship_snapshot`, and persona summaries.
* `src/if_then_mvp/api.py` and `src/if_then_mvp/worker.py` each assemble simulation context separately and each maintain a local `_load_related_topic_digests()` implementation, so any new layered evidence loader will otherwise need to be added in two places.
* `src/if_then_mvp/branch_sessions.py` already persists both `context_pack_snapshot` and `session_memory_pack`, but the current session memory pack only wraps `cutoff_safe_context_pack` and persona priority metadata.
* `src/if_then_mvp/simulation.py` already contains prompt text that says future evidence must be modeler-only, but that rule is only verbal today; there is no explicit `future_evidence_digests` or `branch_facts` structure feeding the prompts.
* `tests/test_retrieval.py` already verifies that target and future messages do not leak into cutoff-safe fields.
* `tests/test_branch_sessions.py` already verifies branch session persistence and prompt construction for realtime replies, so this task can extend those tests instead of starting from scratch.

## Assumptions (temporary)

* We should follow the current Trellis temporary roadmap ordering and treat `realism-02` as the next active task, even though one TODO overview section still lists `realism-05` earlier.
* The first implementation should reuse existing persisted artifacts only: messages, segments, segment summaries, topic links, relationship snapshots, persona profiles, and branch transcript rows.
* We should avoid a database schema change for `realism-02` unless an existing JSON field cannot carry the layered structure cleanly.
* We should keep old keys such as `related_topic_digests` working during the transition so existing simulation and branch-session tests do not all need to move at once.

## Open Questions

* None. The first-pass budget is fixed to at most 3 topic-linked future evidence items.

## Requirements (evolving)

* Add explicit layered fields to the context contract:
  * `cutoff_safe_facts`
  * `future_evidence_digests`
  * `branch_facts`
  * `evidence_policy`
* Preserve current cutoff-safe behavior and compatibility fields while the new layered fields are introduced.
* Load future evidence only from existing post-cutoff analysis artifacts; do not add a new full-history LLM analysis stage.
* The first MVP source set for `future_evidence_digests` is:
  * `SegmentSummary`
  * `Topic` / `TopicLink`
* The first MVP does not include `RelationshipSnapshot` as a future-evidence source.
* Ensure every future evidence item carries origin metadata and a modeler-only usage label.
* Cap future evidence volume in the first version so token growth stays bounded; the first-pass budget is at most 3 topic-linked future evidence items.
* Persist the layered snapshot into `Simulation.context_pack_snapshot` and into the realtime branch session memory pack when relevant to the chosen MVP boundary.
* Keep the system working when no future evidence exists.
* Add tests that prove future evidence does not get mixed into character-known fields.
* This task owns the layered contract and the realtime branch-session memory-pack upgrade.
* This task does not own the main prompt-consumption behavior change; prompt guardrails remain a follow-up concern for `realism-05`, except for compatibility adjustments that are required to keep existing prompts reading a cleaner structure.

## Acceptance Criteria (evolving)

* [x] `build_context_pack()` returns explicit layered evidence fields alongside legacy-compatible fields.
* [x] Future evidence items include source metadata, time bounds, evidence kind, summary, and a modeler-only usage policy.
* [x] Future evidence items can be assembled from post-cutoff `SegmentSummary` rows and `Topic` / `TopicLink` relevance, without depending on `RelationshipSnapshot`.
* [x] When the target message has relevant post-cutoff summaries/topics/snapshots, the new context contract includes bounded future evidence.
* [x] When no relevant post-cutoff evidence exists, the contract still builds successfully.
* [x] Realtime branch sessions can persist the layered context/memory structure according to the selected MVP scope.
* [x] Tests verify that future evidence never appears inside legacy character-known fields such as `related_topic_digests` or `current_segment_history`.
* [x] The MVP boundary is fixed to Approach B: layered contract plus realtime memory-pack upgrade, without folding the main prompt-guardrail work into this task.

## Definition of Done

* Tests added or updated for the changed contract and persistence behavior.
* Lint, typecheck, and relevant Python tests pass.
* Trellis notes updated if the accepted scope changes the roadmap contract between `realism-02`, `realism-03`, and `realism-05`.
* Existing branch-session and legacy simulation paths remain backward compatible or are intentionally migrated with tests.

## Research Notes

### Constraints from the current repo

* `build_context_pack()` is already the narrowest shared contract boundary; changing it is cheaper than inventing a second context format.
* Loader logic is duplicated across `api.py` and `worker.py`, which creates a maintenance risk if future evidence loading becomes more complex.
* Prompts in `simulation.py` already assume the concept of modeler-only future evidence, which means the data contract is lagging behind prompt intent.
* `BranchSession.session_memory_pack` already exists as JSON, so the realtime path can usually absorb a richer structure without a schema migration.

### Feasible approaches here

**Approach A: Contract-first only**

* How it works:
  * Extend `build_context_pack()` and supporting loaders with layered evidence fields.
  * Persist the richer `context_pack_snapshot` where simulations already store it.
  * Keep realtime branch-session memory-pack semantics unchanged for now, which means the realtime path continues to consume only the existing cutoff-safe subset or a compatibility projection.
  * Do not let new future-evidence fields flow into `session_memory_pack` under the misleading key name `cutoff_safe_context_pack`.
* Pros:
  * Smallest blast radius.
  * Clean separation from `realism-05`.
  * Lowest risk of prompt regressions.
* Cons:
  * Realtime branch chat gets little immediate product value from the new contract.
  * A follow-up task must still thread the new fields into `session_memory_pack`.
  * Requires an explicit compatibility decision so the realtime path does not accidentally receive future evidence inside a cutoff-safe wrapper.

**Approach B: Contract + realtime memory-pack update** (Recommended)

* How it works:
  * Extend `build_context_pack()` with layered evidence fields.
  * Update branch-session creation so `session_memory_pack` explicitly stores layered context and policy metadata, while keeping current compatibility keys available for existing prompt builders.
  * Reframe the realtime memory pack so branch facts live at the top level as first-class branch-session data rather than being implicitly derived from transcript-only state.
  * Keep prompt behavior mostly unchanged beyond reading a cleaner structure; do not expand into a full prompt-guardrail rewrite.
* Pros:
  * Matches the roadmap statement that `realism-02` should also strengthen the realtime session memory pack.
  * Gives `realism-03` and `realism-05` a stable structure to build on.
  * Still keeps prompt-guardrail work mostly separate.
* Cons:
  * Slightly wider surface than a pure contract change.
  * Requires careful compatibility handling for existing branch-session tests.

**Approach C: Small end-to-end slice**

* How it works:
  * Implement the layered contract and also wire a minimal prompt consumer in branch assessment or realtime reply generation.
  * Add behavioral tests that prove the model becomes more conservative when future evidence suggests risk, while still not leaking that evidence into direct character speech.
* Pros:
  * Immediate observable behavior change.
  * Easier to prove the new data matters, not just that it exists.
* Cons:
  * Blurs the boundary between `realism-02` and `realism-05`.
  * Higher regression risk and harder review scope.

### Practical file impact by approach

**Approach A**

* Core changes:
  * `src/if_then_mvp/retrieval.py`
  * `src/if_then_mvp/api.py`
  * `src/if_then_mvp/worker.py`
  * `tests/test_retrieval.py`
  * `tests/test_simulations.py`
* Realtime branch-session code:
  * ideally untouched, or touched only to keep future evidence out of the current cutoff-safe wrapper.

**Approach B**

* Everything in Approach A, plus:
  * `src/if_then_mvp/branch_sessions.py`
  * `tests/test_branch_sessions.py`
* Realtime branch-session behavior:
  * session creation stores an explicit layered memory structure that later prompt work can consume safely.

**Approach C**

* Everything in Approach B, plus:
  * `src/if_then_mvp/simulation.py`
  * likely more assertions in `tests/test_branch_sessions.py` and `tests/test_simulations.py`
* Realtime / simulation behavior:
  * prompt semantics change in the same task, not only the data structure.

## Decision (ADR-lite)

**Context**

The roadmap requires `realism-02` to strengthen both the context contract and the realtime session memory pack, but there is a risk of overlapping too much with the later prompt-guardrail task if this work also changes reply-generation behavior.

**Decision**

Use **Approach B** for the MVP:

* extend the context contract with explicit layered evidence fields;
* upgrade realtime `session_memory_pack` so it stores layered evidence and policy metadata explicitly;
* preserve compatibility projections for current prompt builders;
* do not treat this task as the place to rewrite prompt semantics or leakage behavior beyond compatibility.
* restrict the first future-evidence source set to post-cutoff `SegmentSummary` plus `Topic` / `TopicLink` relevance, leaving `RelationshipSnapshot` out of the first MVP.

**Consequences**

* `realism-03` and `realism-05` will inherit a cleaner and more honest data contract.
* The branch-session path becomes first-class in the realism work instead of lagging behind the old simulation contract.
* The review surface is larger than a pure retrieval contract change, but still materially smaller and easier to reason about than combining this with prompt-behavior changes.
* Excluding `RelationshipSnapshot` from the first MVP keeps loader complexity and test setup lower while still preserving topic-based relevance for future evidence selection.

## Technical Approach

1. Extend `build_context_pack()` so it can emit layered evidence fields while keeping current callers alive.
2. Add post-cutoff evidence loaders from `SegmentSummary` plus `Topic` / `TopicLink`, and apply a bounded first-pass selection policy capped at 3 items.
3. Upgrade `BranchSession.session_memory_pack` to store explicit layered memory, including policy metadata and branch facts scaffolding.
4. Keep existing prompt builders on compatibility keys for now, unless a small adapter is needed to read the new structure safely.
5. Add regression tests around retrieval separation and branch-session persistence.

## Out of Scope (explicit)

* Embedding-based retrieval or vector indexing.
* Full retrieval ranking and trace scoring logic from `realism-03`.
* Broader persona/style enrichment from `realism-04`.
* Full prompt-contract rewrite and future-leakage behavior tuning from `realism-05`, unless a tiny compatibility adjustment is unavoidable.
* Database schema changes unless JSON storage proves insufficient.

## Technical Notes

* Relevant files already identified:
  * `src/if_then_mvp/retrieval.py`
  * `src/if_then_mvp/api.py`
  * `src/if_then_mvp/worker.py`
  * `src/if_then_mvp/branch_sessions.py`
  * `src/if_then_mvp/simulation.py`
  * `tests/test_retrieval.py`
  * `tests/test_simulations.py`
  * `tests/test_branch_sessions.py`
* Current branch-session memory pack shape:
  * `strategy_version`
  * `cutoff_safe_context_pack`
  * `persona_priority`
* Current compatibility risk:
  * prompt builders read legacy keys like `related_topic_digests`, `same_day_prior_segments`, `current_segment_history`, and raw `session_memory_pack`.
* Current roadmap risk:
  * if we let this task expand into prompt semantics, review scope will overlap heavily with `realism-05`.
* Implementation landed:
  * `src/if_then_mvp/context_builder.py` now owns the shared context-pack assembly path for both API and worker callers.
  * `src/if_then_mvp/retrieval.py` now emits `cutoff_safe_facts`, `future_evidence_digests`, `branch_facts`, and `evidence_policy`, while keeping legacy keys available.
  * `src/if_then_mvp/branch_sessions.py` now persists a layered realtime `session_memory_pack` plus a compatibility projection for existing prompt builders.
  * Regression coverage was updated in `tests/test_retrieval.py`, `tests/test_branch_sessions.py`, and `tests/test_simulations.py`.
