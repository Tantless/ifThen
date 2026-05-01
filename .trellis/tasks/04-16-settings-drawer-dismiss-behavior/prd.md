# Settings Drawer Dismiss Behavior

## Goal
Refine the desktop settings panel interaction so it behaves like a dismissible drawer.

## Requirements
- Keep the settings surface as a drawer anchored to the right edge.
- Opening settings should render the drawer and an outside-click dismiss area.
- Clicking save should persist the settings and then close the drawer.
- Clicking outside the drawer should close it without saving.
- Clicking inside the drawer should not dismiss it.

## Acceptance Criteria
- [ ] Settings panel opens as a right-side drawer.
- [ ] Saving settings still persists data and closes the drawer.
- [ ] Clicking the backdrop or any non-drawer area closes the drawer without calling save.
- [ ] Existing settings drawer tests pass and include the dismiss-without-save path.

## Technical Notes
- Keep the existing settings form structure and save logic.
- Do not add unrelated visual or data-layer refactors in this task.
