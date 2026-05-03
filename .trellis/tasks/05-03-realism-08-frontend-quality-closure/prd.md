# realism-08 frontend quality closure

## Goal

Close the frontend automated validation gaps left in `realism-08` for realtime branch chat without changing product behavior.

## Scope

- Add focused desktop tests for realtime branch reply job concurrency, superseded input merging, failed reply job display, and retry.
- Update rollout and roadmap documentation to distinguish completed frontend automated coverage from remaining manual/provider validation.
- Keep production code unchanged unless the tests reveal an actual regression.

## Acceptance Criteria

- Frontend tests cover that queued/running branch reply jobs do not trigger a parallel new job when the user sends another self message.
- Frontend tests cover failed branch reply jobs showing an error state and allowing retry.
- Existing frontend coverage for debounce, delayed split bubbles, typing/wait states, and original simulation result compatibility is reflected in `plan/realism-08-quality-and-rollout.md`.
- `npm test -- --runInBand` or the closest project-supported desktop test command passes for the touched tests.

## Out of Scope

- Real provider batch evaluation.
- New backend behavior.
- New Electron UI behavior.
- Full Playwright/E2E infrastructure.
