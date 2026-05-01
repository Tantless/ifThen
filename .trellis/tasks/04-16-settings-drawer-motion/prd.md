# Settings Drawer Motion

## Goal
Add smooth open and close motion to the desktop settings drawer so it feels like a sliding drawer instead of an abrupt popup.

## Requirements
- Animate the backdrop opacity on open and close.
- Animate the drawer panel with a right-to-left slide and slight opacity change.
- Keep the existing save behavior and outside-click dismiss behavior.
- Delay unmount on close long enough for the exit animation to complete.

## Acceptance Criteria
- [ ] Opening settings visibly fades in the backdrop and slides in the drawer.
- [ ] Closing settings visibly fades out the backdrop and slides out the drawer.
- [ ] Save-to-close and outside-click-to-close still work.
- [ ] Typecheck and desktop tests pass.
