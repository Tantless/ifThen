# Enrich Default Avatar Library

## Goal
Replace the current small default avatar preset set with about 30 generated image avatars that feel varied and less templated.

## Requirements
- Generate approximately 30 avatar images using the project image API configuration from `model_env.env`.
- Include varied avatar categories, including landscapes, model/photo-style portraits, anime-style avatars, abstract icons, objects, and other common online avatar styles.
- Include at least three paired couple-avatar sets.
- Refine the current set by keeping only `樱影`, `茶昼`, `暮城`, and `珊海`, then regenerating all other avatar assets.
- Make every couple-avatar pair clearly one male avatar and one female avatar.
- Bias the regenerated set toward more anime and cute anime styles.
- Do not display avatar names in the avatar picker UI.
- Store final project-bound assets inside the desktop frontend workspace.
- Update the default avatar preset source so the avatar picker and default self/other avatars use the richer library.
- Keep changes scoped to the avatar library and related generated assets.

## Acceptance Criteria
- [x] `AVATAR_PRESETS` exposes about 30 usable avatar image URLs.
- [x] At least three explicit male/female couple-avatar pairs are present in the preset list.
- [x] `樱影`, `茶昼`, `暮城`, and `珊海` are preserved from the current set.
- [x] The avatar picker no longer displays avatar names under each option.
- [x] Existing default avatar exports remain available.
- [x] Desktop typecheck passes.
- [x] Relevant avatar/default UI tests pass.

## Technical Notes
- The provider at `API_URL=https://new.myouo.online/v1` blocks the default OpenAI SDK user agent. Use raw HTTP or set `User-Agent: curl/8.0`.
- Use `IMAGE_MODEL_NAME` from `model_env.env`, currently `gpt-image-2`.
