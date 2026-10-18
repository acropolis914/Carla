# Dynamic Adaptive Rack Slot Specification & Parity Checklist

This document serves as the single source of truth for the dynamic adaptive rack UI in Clara.
Instead of a rigid toggle between "normal" and "mini" rack modes, the rack slot dynamically reflows its layout based on actual container width.

---

## 1. Core Architectural Principles

1. **Fluid Responsiveness Over Rigid Modes**:
   - A single, unified rack slot implementation dynamically reflows between **Ultra-Thin**, **Medium**, and **Wide** configurations based on width thresholds evaluated during `resizeEvent`.
   - No separate "Mini Rack Mode" global setting or per-plugin layer toggle.

2. **Universal Interaction & Muscle Memory**:
   - **Double-Click Title**: Double-clicking anywhere on the plugin title row toggles drawer expansion/collapse across all viewport widths.
   - **Dedicated Bypass**: An unambiguous Bypass (`⊘`) toggle sits immediately beside Power (`⏻`), providing instant Dry/Wet 0% / processing bypass with warm amber illumination.
   - **Frameless Flat Glyphs**: Action buttons (`⏻`, `⊘`, `🗔`, `⚙`) use flat, borderless glyphs with direct state color transitions (emerald, amber, lavender, mauve).

3. **Strict Visual Geometry**:
   - **Square 2×2 I/O Matrix**: The 4 status LEDs (Control, MIDI, Audio In, Audio Out) are permanently locked to an exact `18×18px` square container (`aspect-square`) with square pixel tiles that never distort.
   - **Stereo Peak Meters**: Sits flush beside the 2×2 LED matrix as vertical dual bars with smooth gradient coloration.

---

## 2. Dynamic Width Breakpoints

### Tier 1: Ultra-Thin Sidebar (`Width < 230px`)
- **Action Spine (Row 1)**:
  - Left: Frameless `[⏻]` `[⊘]` `[🗔]` `[⚙]`
  - Right: Square 2×2 I/O Matrix + Dual Peak Meters
  - **No Chevron**: The separate expand chevron is completely removed to prevent clutter and maximize space. Drawer is toggled via title double-click.
- **Identity (Row 2)**:
  - 100% full-width plugin title (bold, unclipped).
  - Sub-badge with plugin type and category (`LV2 • DYNAMICS`).
- **Quick Controls (Row 3)**:
  - Full-width Preset selector capsule and inline Mix pill (`MIX: 85%`).
- **Parameter Drawer**:
  - **Stacked Mode**: Label and value sit on line 1; slider track spans **100% full width** on line 2 for precision scrubbing travel.

### Tier 2: Medium / Sidebar (`230px ≤ Width < 440px`)
- **Main Bar (Row 1)**:
  - Left: `[⏻]` `[⊘]` `[🗔]` `[⚙]`
  - Middle: **Title & Type Stack** (`min-width: 90px`, `flex-1`) guaranteed **150px+ dedicated breathing room**.
  - Right: Square 2×2 I/O Matrix + Dual Peak Meters + `[▾]` Chevron.
- **Secondary Bar (Row 2)**:
  - Preset capsule (`[★ Preset Name ▾]`) on left + Dry/Wet Mix pill on right. Presets remain on row 2 so they never compress the title.
- **Parameter Drawer**:
  - Reflows from 1-column stacked (`< 320px`) to **2-column inline grid** (`≥ 320px`).

### Tier 3: Wide Streamline (`Width ≥ 440px`)
- **Single Streamlined Strip**:
  - `[⏻ ⊘ 🗔 ⚙]` + `[Title & Type]` + `[Preset ▾]` + `[MIX: 85%]` + `[Square 2×2 I/O + Meters]` + `[▾]` all flow seamlessly onto a single ultra-compact bar (`34px` - `38px` base height).
- **Parameter Drawer**:
  - 2-column inline grid with 75px fixed label alignment and 46px spinboxes.

---

## 3. Parity Checklist for Future Modifications

Before landing any UI modification to rack slots, verify the following checklist:

- [ ] **Ultra-Thin Parity (< 230px)**:
  - [ ] No chevron button visible in action spine.
  - [ ] Action buttons `[⏻ ⊘ 🗔 ⚙]` are frameless and do not wrap or overflow.
  - [ ] Plugin title is 100% readable without truncation.
  - [ ] Parameter sliders stack label/value on row 1 and slider track on row 2 (100% width).
- [ ] **Medium Parity (230px – 440px)**:
  - [ ] Plugin title has at least 100px visible width and does not collapse to 0px.
  - [ ] Presets and Mix stay on row 2 below title and never crush the title horizontally.
- [ ] **Wide Parity (≥ 440px)**:
  - [ ] Presets and Mix flow into row 1.
  - [ ] Drawer parameter sliders use 2-column grid.
- [ ] **Interaction Parity**:
  - [ ] Double-clicking title row toggles expand/minimize across all widths.
  - [ ] Bypass (`⊘`) toggles DSP dry/wet to 0% with amber glow.
  - [ ] 2×2 I/O LEDs maintain identical 1:1 aspect ratio (`18×18px`) without stretching.
