# Desktop IPC Only Refactor

## Goal
Refactor the desktop application to a desktop-only architecture where the renderer no longer talks to the local Python API over loopback HTTP. All renderer data access must go through preload and Electron main-process IPC.

## Requirements
- Remove direct renderer-side HTTP access for settings, conversations, jobs, simulations, and imports.
- Add a main-process backend facade that proxies desktop data operations.
- Keep the Python backend as an internal desktop dependency for this phase.
- Restrict backend access so the renderer does not hold direct API credentials or base URLs.
- Move import execution to the main process so the renderer does not read and upload the full chat text itself.
- Preserve current desktop functionality and existing user flows.

## Acceptance Criteria
- [ ] `desktop/src/lib/services/*` no longer depends on the renderer HTTP client.
- [ ] Preload exposes typed IPC methods for the desktop data operations used by the renderer.
- [ ] Main-process IPC handlers proxy desktop data requests successfully.
- [ ] The Python API requires an internal desktop auth token when started by Electron.
- [ ] Import flow works without renderer-side file-content upload.
- [ ] Desktop typecheck and tests pass.
- [ ] Python tests pass through the supported test entry.

## Technical Notes
- This refactor is desktop-only. Future web reuse is explicitly out of scope.
- The Python API remains as an internal service in this phase; removing FastAPI entirely is a later optional step.
- Keep the UI-facing service interfaces as stable as possible to limit App-level churn.
