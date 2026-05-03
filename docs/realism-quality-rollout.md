# Realism Quality Rollout

## Scope

This rollout covers the realism pipeline after `realism-02` through `realism-05`: layered evidence, retrieval ranking, deterministic persona/style profiles, prompt leakage guardrails, and realtime branch sessions.

The primary product path is realtime branch chat: the user continues as `self`, and the model only generates `other`. The legacy `single_reply` and `short_thread` simulation modes remain compatibility paths during rollout.

## Feature Flag

`IF_THEN_ENABLE_FUTURE_EVIDENCE` controls whether cutoff-after evidence is loaded into context packs.

- Default: enabled.
- Disable: set `IF_THEN_ENABLE_FUTURE_EVIDENCE=0`, `false`, `off`, or `no`.
- Rollback effect: `future_evidence_digests` and future-evidence trace rows are empty; cutoff-safe related topics, persona/style profiles, branch facts, and legacy simulation modes remain available.

## Required Checks

Run these before shipping realism changes:

```bash
PYTHONPATH=src pytest tests/test_realism_quality_gate.py -q
PYTHONPATH=src pytest tests/test_realism_baseline_fixtures.py -q
PYTHONPATH=src pytest tests/test_simulations.py tests/test_branch_sessions.py tests/test_worker.py -q
PYTHONPATH=src pytest -q
```

For desktop-side realtime interaction changes, also run the desktop test suite from `desktop/`:

```bash
npm test -- desktop/tests/visualShell.test.tsx
npm test
```

For live-provider realism validation, run the fixed baseline provider regression from the repo root:

```bash
python scripts/run_realism_provider_regression.py \
  --env-file llm_config.env \
  --output-json .pytest-tmp/realism-provider-regression.json \
  --output-markdown .pytest-tmp/realism-provider-regression.md
```

The runner defaults to `llm_config.env` and uses `API_BASE_URL`, `API_KEY`, and `MODEL_NAME` with the Responses API JSON object format. Use `--require-provider` in a blocking validation environment. Without provider configuration the command writes a skipped report instead of claiming live validation passed.

## Quality Gates

- Context packs must keep `cutoff_safe_facts`, `future_evidence_digests`, and `branch_facts` separate.
- Future evidence must not appear inside cutoff-safe compatibility packs.
- Branch assessment may use future evidence only for risk, confidence, and conservative direction fields.
- Reply prompts must mark future evidence as modeler-only and must not instruct the model to quote or reveal it.
- Realtime branch sessions must keep only one active reply job per session; newer self input or newer jobs supersede older jobs.
- Branch reply prompts must include committed branch transcript messages in sequence.
- Deleting a conversation must remove branch sessions, branch messages, and reply jobs.
- Baseline fixtures must retain explicit future leakage labels so regressions can be detected.
- Provider regression reports must have `leakage_case_count = 0` before live validation is accepted.
- Realism validation datasets must come from the committed synthetic corpus under `D:\ifThen\tests\fixtures\realism_synthetic`.
- Desktop realtime branch tests must cover debounce, queued/running merge behavior, typing/error/retry states, delayed split-bubble delivery, and legacy simulation result compatibility.

## Manual Acceptance

- The generated `other` should not become suddenly more mature, articulate, intimate, or therapeutic than the historical persona supports.
- Reply length and bubble rhythm should match `persona_other.deterministic_style_profile`.
- If future evidence shows a clear later refusal, a softer rewrite may reduce pressure but must not flip the relationship into obvious success.
- If the original timeline failed mainly because wording was abrupt, a warmer rewrite may improve first-reply catchability but should not overstate long-term change.
- In realtime branch chat, users must be able to send consecutive `self` messages without the model racing to answer stale input.

## Rollout Steps

1. Ship with `IF_THEN_ENABLE_FUTURE_EVIDENCE` enabled in development and internal builds.
2. Run the required checks and manually inspect high-risk baseline cases for leakage.
3. Keep `single_reply` and `short_thread` available as compatibility fallbacks.
4. Treat realtime branch chat as the primary entry after rewrite once branch reply jobs, typing/error/retry states, and transcript ordering pass verification.
5. If future leakage is observed, set `IF_THEN_ENABLE_FUTURE_EVIDENCE=0` and rerun the quality gate before investigating prompt or retrieval changes.

## Observability

Track these during rollout:

- Simulation and branch reply latency.
- Context pack character length or token estimate.
- Future evidence hit rate.
- Future leakage quality-gate failures.
- Branch reply job supersede/conflict counts.
- User retry count and branch reply failure count.

## Latest Local Verification

2026-05-04 local gates:

```bash
PYTHONPATH=src pytest -q
python scripts/report_realism_baseline.py
python scripts/run_realism_provider_regression.py --require-provider --max-cases 1 --output-json .pytest-tmp/realism-provider-live-smoke.json --output-markdown .pytest-tmp/realism-provider-live-smoke.md
cd desktop && npm test
cd desktop && npm run typecheck
```

Results:

- Backend: 122 pytest cases passed.
- Baseline report: 12 fixed cases across 3 scenarios and 8 failure types.
- Provider regression runner: reads `llm_config.env`, uses Responses API, and completed a 1-case live smoke with 0 leakage and 0 errors.
- Desktop: 128 Vitest cases passed.
- Desktop TypeScript: typecheck passed.

Remaining non-local validation:

- Run live provider regression for fixed baseline samples with `--require-provider` and inspect future leakage.
- Run manual realism review for over-optimistic, over-mature, and over-therapeutic replies.
- Rerun full-analysis performance sampling on the committed synthetic realism corpus under `D:\ifThen\tests\fixtures\realism_synthetic`.
