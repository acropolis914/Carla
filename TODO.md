# Carla Development Tasks

## Bugs
- [ ] Fix: Rack item remove button still does not delete or show confirmation dialog (reopened: calf skin vs other skins / context menu / delete key)
- [ ] Fix: Left-click drag on empty canvas does not pan the UI
- [x] Fix: Node right-click preserves multi-selection so Align Horizontally / Vertically works



## Features
- [x] feat: Improved logging with Python Rich console, loglevels, log tags, and CLI flags (`--log-whitelist`, `--log-blacklist`)
- [ ] feat: Minimize to system tray
- [x] feat: Side-by-side view for mini rack and patchbay with bidirectional focus/scroll synchronization
- [ ] feat: Synchronized colors, bypass state, and switch button between rack node and patchbay node
- [ ] feat: Floating sidebar quick settings overlay for patchbay with integrated search bar
- [ ] feat: Search selection persists selected items until user interaction
- [ ] feat: Minified rack mode exposing only essential controls
- [x] feat: Offer to save dirty edits on exit (Yes, No, Cancel) with visual save status indicator (dirty/saved)
- [x] feat: Status indicator for last autosave timestamp and countdown timer to next autosave
- [ ] feat: Subtle canvas alignment dots/grid with snapping; align functions respect grid snap
- [ ] feat: Infinite canvas with `infinite-canvas = true` project metadata and migration for legacy files (recenter by subtracting half total bounding box on both X and Y axes)
- [ ] feat: Auto repel arrangement tools (auto repel selected vs auto repel all), defaulting auto arrange and auto repel to selected items only
- [ ] feat: Patchbay selection keyboard shortcuts (Ctrl+A to select all, Photoshop-style selection shortcuts: Ctrl+D to deselect, Ctrl+Shift+I to invert selection)
- [ ] feat: Reposition/resize bottom bar audio info (sample rate, buffer size, DSP load, etc.) — make more compact or relocate to settings
- [ ] feat: Settings dialog sidebar enhancement — use a more readable, cohesive font
- [ ] feat: Settings dialog polish & cleanup — reorganize sections, improve layout, use system icons instead of custom/outdated ones, and remove obsolete options deprecated by recent updates
- [ ] feat: Smoother patchbay rendering and interaction performance (higher refresh/frame rate, reduced dragging jitter and cable render overhead)
- [ ] feat: Mini DSP load graph over time with side label and hover tooltip
