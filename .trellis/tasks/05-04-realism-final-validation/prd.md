# Realism Final Validation

## Goal

Close the remaining non-manual realism validation gap after implementation is complete by:

- running live provider regression on the committed baseline cases with the local `llm_config.env` configuration; and
- running full-analysis performance sampling on the committed synthetic realism corpus under `tests/fixtures/realism_synthetic`.

## Requirements

- Reuse the existing provider regression runner and keep API keys out of committed files and logs.
- Add a reusable command entrypoint for synthetic full-analysis performance sampling instead of a one-off ad hoc shell sequence.
- Performance sampling must run in an isolated `IF_THEN_DATA_DIR` so it does not mutate the user's normal `.data` database.
- Record enough non-PII performance diagnostics to compare elapsed time, stage timings, and artifact counts across synthetic cases.
- Update roadmap/rollout/TODO documents so the remaining blocked items are only the human realism sign-off.
- Commit the completed work.

## Acceptance Criteria

- [ ] `python scripts/run_realism_provider_regression.py --require-provider` completes on more than the prior 1-case smoke sample and writes JSON/Markdown reports.
- [ ] `python scripts/run_realism_analysis_performance.py` runs against `tests/fixtures/realism_synthetic` and writes JSON/Markdown reports from isolated data directories.
- [ ] Tests cover the new performance sampling runner without requiring live provider access.
- [ ] Roadmap and rollout docs reflect the new provider/performance validation results and remaining human-only review boundary.
- [ ] Completed work is committed with a task-scoped commit.

## Technical Notes

- Prefer direct reuse of `parse_qq_export()`, `AnalysisJob`, `ImportBatch`, `run_next_job()`, and existing runtime LLM config loading over reimplementing the analysis pipeline.
- Performance reports must not persist raw prompt text, API keys, or chat file paths beyond the committed synthetic fixture paths already in repo.
