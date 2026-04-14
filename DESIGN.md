# WeChat Desktop-Inspired DESIGN.md

## Design Intent

Design for an Electron-based chat application with a visual tone inspired by Windows WeChat desktop.

This is not:
- a WeChat Mini Program native UI spec
- a marketing H5 spec
- a SaaS dashboard style guide

This design system focuses on:
- buttons
- dialogs / modals
- lightweight overlays

The goal is to make the UI feel like a real desktop chat client instead of a generic web page inside Electron.

---

## Overall Vibe

The interface should feel:
- restrained
- practical
- calm
- familiar
- desktop-first

Prioritize:
- low visual interruption
- quiet hierarchy
- compact controls
- subtle layering
- conversation-first composition

Avoid:
- loud SaaS styling
- high-saturation action colors
- oversized rounded mobile controls
- heavy floating-card aesthetics
- decorative or promotional UI

---

## Color Palette

### Base
- App background: warm gray
- Window surface: soft off-white
- Secondary surface: pale beige-gray
- Elevated surface: white
- Divider: light warm neutral

Suggested tokens:
- `--bg-app: #D9D6D2`
- `--bg-window: #F3F1EE`
- `--bg-panel: #F7F4EF`
- `--bg-secondary: #E7E2DC`
- `--bg-elevated: #FFFFFF`
- `--divider: rgba(94, 84, 72, 0.12)`

### Text
- Primary text: dark charcoal
- Secondary text: warm gray
- Meta text: muted neutral

Suggested tokens:
- `--text-primary: #1C1A18`
- `--text-secondary: #6F675F`
- `--text-tertiary: #958D84`

### Accent
Use green sparingly for important confirmation and selected states.

Suggested tokens:
- `--accent: #07C160`
- `--accent-hover: #06AE56`
- `--accent-soft: #E8F7EF`

### Danger
Use restrained red for destructive intent.

Suggested tokens:
- `--danger: #D04B57`
- `--danger-soft: #FCEBEC`

---

## Typography

Preferred fonts:
- `"Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif`

Recommended sizing:
- Dialog title: `16px - 18px`
- Section title: `14px - 15px`
- Body: `13px - 14px`
- Meta: `12px`
- Button text: `13px - 14px`

Rules:
- keep type compact and readable
- avoid oversized headlines
- avoid decorative weight contrast
- use uppercase eyebrow text sparingly

---

## Shape & Depth

Use restrained radii and soft separation.

Recommended radii:
- small controls: `6px - 8px`
- buttons / inputs: `8px - 10px`
- dialogs / popovers: `10px - 12px`

Depth rules:
- borders matter more than shadows
- use soft shadows only on floating layers
- keep surfaces mostly flat and calm

Suggested shadows:
- dialog: `0 18px 40px rgba(0, 0, 0, 0.12)`
- popover: `0 10px 28px rgba(0, 0, 0, 0.14)`

---

## Buttons

### Hierarchy

#### Primary
Use for the single main confirm action in a local context.

Style:
- green background
- white text
- compact desktop sizing

Use for:
- save
- confirm
- import
- submit

Rules:
- only one primary action per dialog or action cluster
- never place two primary buttons side by side

#### Secondary
Default action style.

Style:
- neutral light background
- subtle border
- dark text

Use for:
- cancel
- choose file
- edit
- open settings
- view details

#### Ghost
For low-emphasis toolbar or inline actions.

Style:
- transparent or near-transparent background
- visible hover fill
- no strong border by default

Use for:
- close
- more
- utility actions
- lightweight header controls

#### Danger
For destructive actions only.

Style:
- neutral or soft red-tinted base
- restrained red text or outline
- never more visually dominant than the main primary action

### Sizing
Recommended heights:
- small: `28px - 30px`
- default: `32px - 36px`

Padding:
- horizontal `12px - 16px`

Rules:
- keep buttons compact
- icon-only buttons need clear hover feedback
- avoid large mobile CTA proportions

### States
All buttons must support:
- default
- hover
- active
- disabled
- focus-visible

Behavior:
- hover: slightly darker fill or clearer border
- active: subtle pressed response
- disabled: lower contrast, still readable
- focus-visible: thin accessible ring

Avoid:
- large scale animation
- bounce or spring motion
- glowing hover effects

---

## Dialogs / Modals

### Intent
Dialogs should feel light, clear, and desktop-appropriate.

Use dialogs for:
- confirmation
- import / setup tasks
- multi-field forms
- important warnings

Do not use dialogs for:
- tiny action lists
- simple contextual tools
- low-risk local actions

### Overlay
- dark neutral translucent scrim
- mild blur allowed
- never overly heavy

Suggested overlay:
- `rgba(33, 33, 33, 0.28)`

### Panel
- off-white or white surface
- thin border
- restrained radius
- compact shadow
- efficient internal spacing

Recommended widths:
- standard: `420px - 520px`
- large: `560px - 760px`

### Structure
Recommended order:
1. header
2. body
3. optional form/content area
4. footer actions

Header:
- title left
- optional close action right

Footer:
- actions aligned right
- cancel before confirm
- primary action last

### Copy
Use short task-oriented copy.

Good examples:
- `导入聊天记录`
- `保存设置`
- `确认删除`
- `选择头像`

Avoid:
- long explanatory headlines
- emotional or promotional wording
- vague action labels

---

## Lightweight Overlays

Includes:
- popovers
- menus
- quick panels
- anchored date/filter/action surfaces

Traits:
- compact
- close to trigger
- subtle border
- soft shadow
- fast open/close
- lighter than dialogs

Use for:
- quick filters
- action menus
- contextual settings
- anchored picker surfaces

Avoid turning these into full-screen or high-interruption layers.

---

## Inputs In Modal Contexts

Inputs should feel calm and desktop-native.

Style:
- near-white fill
- thin neutral border
- restrained radius
- dark readable text

Rules:
- labels above fields
- helper text below if needed
- validation close to the field
- no oversized input heights
- use border emphasis before glow on focus

---

## Spacing

Use moderate desktop density.

Recommended rhythm:
- tight: `6px - 8px`
- standard: `10px - 12px`
- section: `16px - 20px`
- dialog padding: `20px - 24px`

Rules:
- keep hierarchy driven by spacing and contrast
- avoid random jumps in padding scale
- avoid landing-page whitespace

---

## Motion

Motion should be subtle and nearly invisible.

Recommended timing:
- `120ms - 180ms`

Use:
- opacity shifts
- border-color changes
- slight surface changes

Avoid:
- bounce
- elastic movement
- dramatic scaling
- theatrical entrances

---

## Do

- keep conversation content visually primary
- use green only for important confirm actions
- default to neutral secondary buttons
- use subtle borders to define layers
- keep controls compact and desktop-like
- prefer contextual overlays over unnecessary modal interruption
- make hover feedback clear but quiet

---

## Don’t

- don’t make every action green
- don’t use oversized rounded mobile buttons
- don’t use bright SaaS blue primary actions
- don’t rely on heavy black modal backdrops
- don’t create oversized floating white cards
- don’t overuse gradients, glows, or decorative shadows
- don’t let controls overpower the chat content

---

## Agent Prompt Guide

When generating UI for this project:
- treat it as a desktop chat application inside Electron
- use Windows WeChat desktop as the tone reference
- keep buttons, dialogs, and overlays restrained and practical
- favor warm neutrals, subtle borders, and compact spacing
- reserve green for the single most important confirm action
- avoid SaaS dashboard styling and marketing-page composition
- keep the message area as the visual center

When unsure:
- choose the quieter option
- choose the flatter option
- choose the more contextual option
- choose the one that feels more like a desktop utility than a web landing page
