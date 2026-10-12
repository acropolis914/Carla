# Carla Development Tasks

> **Difficulty Scale**: `[Diff: 1]` Easy / Quick win · `[Diff: 2]` Moderate · `[Diff: 3]` Complex / Architectural

---

## 🐛 Bugs
- [x] `[Diff: 1]` Fix: Rack item remove button still does not delete or show confirmation dialog (reopened: calf skin vs other skins / context menu / delete key)
- [x] `[Diff: 1]` Fix: Left-click drag on empty canvas does not pan the UI
- [x] `[Diff: 1]` Fix: Patchbay canvas node power button (`⏻`) does not toggle plugin processing state reliably
- [ ] `[Diff: 1]` Fix: Patchbay minimap looks cut off on unloaded canvas areas (works now, but visually cut off/janky boundary clipping)




---

## 🎛️ Patchbay Canvas & Navigation
- [x] `[Diff: 1]` feat: Patchbay selection keyboard shortcuts (Ctrl+A to select all, Photoshop-style selection shortcuts: Ctrl+D to deselect, Ctrl+Shift+I to invert selection)
- [x] `[Diff: 2]` feat: Smoother patchbay rendering and interaction performance (higher refresh/frame rate, reduced dragging jitter and cable render overhead)
- [ ] `[Diff: 1]` feat: Search selection persists selected items until user interaction
- [x] `[Diff: 2]` feat: Subtle canvas alignment dots/grid with snapping; align functions respect grid snap
- [x] `[Diff: 2]` feat: Auto repel arrangement tools (auto repel selected vs auto repel all), defaulting auto arrange and auto repel to selected items only
- [x] `[Diff: 3]` feat: Infinite canvas with `infinite-canvas = true` project metadata and migration for legacy files (recenter by subtracting half total bounding box on both X and Y axes)
- [x] `[Diff: 1]` feat: Canvasbox sub-bar action buttons (quick controls/actions bar with Nerd Font icons)
- [x] `[Diff: 2]` feat: Option/checkbox on canvasbox to collapse or hide ports without active connections


---

## 🔗 Cables & Patchbay Visuals
- [x] `[Diff: 2]` feat: Cable routing styles (Bezier, Straight/Linear, Orthogonal/Right-angle)
- [x] `[Diff: 2]` feat: Dynamic cable coloring based on source and destination node colors with linear gradients
- [x] `[Diff: 1]` Fix/feat: Patchbay canvasbox color changes dynamically update connected canvas line gradients immediately without requiring redraw or node moves
- [ ] `[Diff: 3]` feat: Visual signal/event flow animations — pulsing/glow animations on active nodes and animated traveling pulses or particles along cables when audio/MIDI events are transmitted


---

## 🎚️ Rack & Dual-View Integration
- [x] `[Diff: 2]` feat: Side-by-side view for mini rack and patchbay with bidirectional focus/scroll synchronization
- [x] `[Diff: 2]` feat: Synchronized colors, bypass state, and switch button between rack node and patchbay node
- [ ] `[Diff: 2]` feat: Minified rack mode exposing only essential controls

---

## ⚙️ Settings & System UI
- [ ] `[Diff: 1]` feat: Settings dialog sidebar enhancement — use a more readable, cohesive font
- [ ] `[Diff: 2]` feat: Settings dialog polish & cleanup — reorganize sections, improve layout, use system icons instead of custom/outdated ones, and remove obsolete options deprecated by recent updates
- [ ] `[Diff: 1]` feat: Minimize to system tray

---

## 📊 Status Bar & Diagnostics
- [ ] `[Diff: 2]` feat: Reposition/resize bottom bar audio info (sample rate, buffer size, DSP load, etc.) — make more compact or relocate to settings
- [ ] `[Diff: 2]` feat: Mini DSP load graph over time with side label and hover tooltip
- [ ] `[Diff: 2]` feat: Floating sidebar quick settings overlay for patchbay with integrated search bar

---

## 💾 Project Session & System Utilities
- [x] `[Diff: 1]` feat: Offer to save dirty edits on exit (Yes, No, Cancel) with visual save status indicator (dirty/saved)
- [x] `[Diff: 1]` feat: Status indicator for last autosave timestamp and countdown timer to next autosave
- [x] `[Diff: 2]` feat: Improved logging with Python Rich console, loglevels, log tags, and CLI flags (`--log-whitelist`, `--log-blacklist`)
- [ ] `[Diff: 2]` feat: Project notes for current session/save file with rich Markdown rendering support in Qt (QTextDocument markdown / preview)
- [ ] `[Diff: 1]` feat: Standardized `argparse` integration to expose all CLI flags and `--help` with Python `rich` formatting
- [x] `[Diff: 1]` Fix/feat: Full `.carjp` project file integration across autosave manager, recent files list, dirty tracking, and startup autoload

