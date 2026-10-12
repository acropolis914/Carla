# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] - 2026-10-12

### Added
- **Photoshop/Blender-Style Modal Tools**:
  - `V`: Marquee selection mode (crosshair cursor; drag to box-select).
  - `H` / `Space`: Hand / pan mode (hand cursor; drag to pan canvas).
  - `Q` / `Escape`: Default pointer mode (drag nodes, patch cables, open menus).
  - Floating modal tool pill widget (`CanvasToolBarOverlay`) with cached Nerd Font glyphs (with fallback to Unicode) and viewport repositioning.
- **Canvas Context Menu Arrange Submenu**:
  - Added "Arrange & Align" submenu to empty canvas background context menu (Auto-arrange All, Align/Distribute Horizontally & Vertically, Move Aside Non-Connected Nodes).
- **Node-Wide Multi-Selection**:
  - `Ctrl + Click` anywhere on a node body or port toggles selection without moving nodes or triggering cable patches.
- **Rich Logging & Tag Checklist Filtering**:
  - Structured `CarlaLogger` supporting Python Rich terminal formatting, log levels, timestamps, and categories (`APP`, `ENGINE`, `PATCHBAY`, `PLUGIN`, `SESSION`, `CANVAS`, `BACKEND`).
  - Added CLI flags `--log-level`, `--log-whitelist`, `--log-blacklist`, and `--console-log` / `--no-console-log`.
  - Added in-UI Log tab tag checklist filter to dynamically toggle visible categories without losing history, and a settings option to mirror logs to terminal.
- **Session Safety & Autosave Status Indicators**:
  - Save on exit prompt with `Save`, `Discard`, and `Cancel` options whenever a session has unsaved modifications.
  - Visual dirty/saved indicator (`*` prefix in title bar, plus `● Unsaved` / `✓ Saved` badge in the status bar).
  - Statusbar display showing last autosave timestamp and live countdown timer to the next autosave.


### Fixed
- **Autosave Path Normalization & Recursion Prevention**:
  - Normalized project filenames to prevent `.autosaves/` recursion when recovering and re-saving sessions.
  - Separated logical project filepath from autosave recovery source during load.
- **Patchbay Interactions & Drag Propagation**:
  - Fixed `DraggableGraphicsView` mouse event interception that swallowed scene port patches and node clicks.
  - Implemented instant $\ge 4\text{px}$ right-drag directional marquee selection (left-to-right touches, right-to-left encloses) disambiguated from a stationary 150ms hold context menu.
- **Minimap Zoom & Position Sync**:
  - Corrected zoom-level coordinate mapping and clamping in `CanvasPreviewFrame` to prevent minimap cursor drift and offset distortion.
  - Routed wheel-event zooming through `PatchScene.zoom_wheel` so minimap scale updates synchronously.
- **Draggable Canvas Controls**:
  - `PatchbayHelpOverlay` cheat-sheet is now open by default and freely draggable across the viewport.
- **Qt 6 Compatibility**:
  - Fixed `QFontDatabase` instantiation error on Qt 6 by invoking static method `QFontDatabase.families()`.
