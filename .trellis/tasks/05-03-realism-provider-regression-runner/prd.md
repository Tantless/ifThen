# Realism Provider Regression Runner

## Goal

Add an executable regression runner for live-provider realism validation so the remaining roadmap checks can be run consistently once provider configuration is available.

## Requirements

- Load fixed realism baseline cases from `tests/fixtures/realism_baseline/cases.json`.
- Run selected cases through a live-provider-compatible generation path or injectable fake provider.
- Detect forbidden future-knowledge leakage using each case's `modeler_only_evidence.forbidden_character_knowledge`.
- Emit machine-readable JSON and concise Markdown reports with leakage, risk-alignment, style/persona review notes, and skip status.
- Skip cleanly with a clear message when `local_llm_config.py` or equivalent provider environment is unavailable.
- Keep the runner independent from realtime branch production behavior and avoid new database schema changes.

## Acceptance Criteria

- [x] A command under `scripts/` can run provider regression for fixed baseline cases.
- [x] The command supports deterministic tests using fake generated outputs without calling a real LLM.
- [x] Missing provider configuration exits successfully with an explicit skipped report.
- [x] JSON report includes per-case leakage findings and summary counts.
- [x] Roadmap and rollout docs point to the new command as the provider/manual validation entry.

## Technical Notes

- This task does not claim live provider validation is complete unless the provider configuration exists and the command is run against it.
- The first implementation should prefer a small script with injectable provider behavior over changing worker/API contracts.
- Use fixed baseline fixture metadata as the single source of truth for forbidden future terms.
