# Responsive Modal Avatar Picker Layout

## Goal
Make the import-chat dialog and other desktop modals fit within the app window at different window sizes, and make avatar choices fill their option boxes without visible padding.

## Requirements
- Widen the import dialog so the avatar picker no longer makes the lower half overflow in normal desktop sizes.
- Apply viewport-aware max sizing to all shared desktop modals so content remains reachable when the app window is maximized or minimized.
- Keep specialized analysis and chat-history modals working with their existing internal scroll layouts.
- Make avatar option images fill the selectable option box.
- Keep avatar names hidden in the picker.
- Keep changes scoped to desktop modal/avatar styles and tests.

## Acceptance Criteria
- [x] Import dialog uses a wider modal panel than the default modal.
- [x] Shared modal panels have viewport max-height and scroll behavior.
- [x] Avatar options are square and their images fill the option box.
- [x] Desktop typecheck passes.
- [x] Modal/avatar related tests pass.
- [x] Desktop build passes.
