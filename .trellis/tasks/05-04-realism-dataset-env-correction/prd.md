# Realism Dataset And Env Correction

## Goal

Correct the realism validation memory and provider regression runner so the committed synthetic realism fixtures are the test dataset and live LLM validation can use the project's local env file.

## Requirements

- Treat `D:\ifThen\tests\fixtures\realism_synthetic` as the realism validation dataset in roadmap, rollout, PRD, and trace memory.
- Remove or supersede stale references that frame `D:\聊天记录-mvp测试集\聊天记录-5000条.txt` as the current realism test dataset.
- Update provider regression tooling to read local env-file configuration from `llm_config.env`.
- Use the Responses API JSON-object response format when env-file configuration is used.
- Keep API keys and env values out of committed files and test output.
- Commit the completed work.

## Acceptance Criteria

- [x] `rg` finds no current roadmap/rollout memory that directs realism validation to the external `D:\聊天记录-mvp测试集` path.
- [x] `scripts/run_realism_provider_regression.py` can load `llm_config.env` with `API_BASE_URL`, `API_KEY`, and `MODEL_NAME`.
- [x] The provider regression runner can call an injectable Responses API transport and parse JSON into existing pydantic response models.
- [x] Tests cover env-file config loading, Responses API JSON parsing, and the no-secret report behavior.
- [x] Documentation points provider validation to the committed synthetic realism fixtures.

## Technical Notes

- Keep `local_llm_config.py` and existing environment-variable runtime config as compatibility fallbacks.
- Do not print or commit env-file secret values.
- Historical performance reports can be marked as superseded for realism validation instead of deleting them.
