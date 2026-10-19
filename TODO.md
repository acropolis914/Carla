# Carla Development Tasks

> **Difficulty Scale**: `[Diff: 1]` Easy / Quick win · `[Diff: 2]` Moderate · `[Diff: 3]` Complex / Architectural

---

## 🐛 Bugs
- [x] `[Diff: 1]` Fix: Rack item remove button still does not delete or show confirmation dialog (reopened: calf skin vs other skins / context menu / delete key)
- [x] `[Diff: 1]` Fix: Left-click drag on empty canvas does not pan the UI
- [x] `[Diff: 1]` Fix: Patchbay canvas node power button (`⏻`) does not toggle plugin processing state reliably
- [x] `[Diff: 1]` Fix: Patchbay canvasbox selected text color is inverted or unreadable against header background
---

## 🎛️ Patchbay Canvas & Navigation
- [x] `[Diff: 1]` feat: Patchbay selection keyboard shortcuts (Ctrl+A to select all, Photoshop-style selection shortcuts: Ctrl+D to deselect, Ctrl+Shift+I to invert selection)
- [x] `[Diff: 2]` feat: Smoother patchbay rendering and interaction performance (higher refresh/frame rate, reduced dragging jitter and cable render overhead)
- [x] `[Diff: 1]` feat: Search selection persists selected items until user interaction
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
- [x] `[Diff: 3]` feat: Visual signal/event flow animations - pulsing/glow animations on active nodes and animated traveling pulses or particles along cables when audio/MIDI events are transmitted
- [x] `[Diff: 2]` Fix: OpenGL-first canvas rendering - default to hardware acceleration, eliminate artificial software-render throttling, fix PulseAudio peak-detect read callback in `pwlevels.py`, and reapply clean UI fixes
- [x] `[Diff: 2]` Fix: Signal-flow pulses sometimes disappear on quiet/transient audio - need peak-hold envelope smoothing so brief silences do not drop a node below the pulse threshold (flicker/stutter)
- [x] `[Diff: 2]` feat: Tint signal-flow glows/pulses with the correct colors along the chain - blend from the source node color through the cable to the destination node color (per-endpoint gradient) instead of the single fixed cyan/white


---

## 🎚️ Rack & Dual-View Integration
- [x] `[Diff: 2]` feat: Side-by-side view for mini rack and patchbay with bidirectional focus/scroll synchronization
- [x] `[Diff: 2]` feat: Synchronized colors, bypass state, and switch button between rack node and patchbay node
- [x] `[Diff: 2]` feat: Minified rack mode exposing only essential controls (Photoshop layer view with mini collapsible slider tray)

---

## ⚙️ Settings & System UI
- [x] `[Diff: 1]` feat: Settings dialog sidebar enhancement - use a more readable, cohesive font
- [x] `[Diff: 2]` feat: Settings dialog polish & cleanup - reorganize sections, improve layout, use modern compact pills instead of outdated bitmap icons, and add live reactive tweakables
- [x] `[Diff: 1]` feat: Minimize to system tray

---

## 📊 Status Bar & Diagnostics
- [x] `[Diff: 2]` feat: Reposition/resize bottom bar audio info (sample rate, buffer size, DSP load, etc.) - make flexible and compact for tiling
- [ ] `[Diff: 2]` feat: Mini DSP load graph over time with side label and hover tooltip
- [ ] `[Diff: 2]` feat: Floating sidebar quick settings overlay for patchbay with integrated search bar

---

## 💾 Project Session & System Utilities
- [x] `[Diff: 1]` feat: Offer to save dirty edits on exit (Yes, No, Cancel) with visual save status indicator (dirty/saved)
- [x] `[Diff: 1]` feat: Status indicator for last autosave timestamp and countdown timer to next autosave
- [x] `[Diff: 2]` feat: Improved logging with Python Rich console, loglevels, log tags, and CLI flags (`--log-whitelist`, `--log-blacklist`)
- [ ] `[Diff: 2]` feat: Project notes for current session/save file with rich Markdown rendering support in Qt (QTextDocument markdown / preview)
- [x] `[Diff: 1]` feat: Standardized `argparse` integration to expose all CLI flags and `--help` with Python `rich` formatting
- [x] `[Diff: 1]` feat: Rich CLI startup banner (`Clara vX.Y.Z` / `based on Carla version A.B.C`) and a formatted SIGINT prompt with a safe Enter-to-exit default
- [x] `[Diff: 1]` Fix/feat: Full `.carjp` project file integration across autosave manager, recent files list, dirty tracking, and startup autoload
---

## 🧠 Graph Introspection & Layout
- [x] `[Diff: 2]` feat: Graph introspection model (`collect_graph`) returning JSON-able nodes + ports + connections + derived topology, shared by arrange/control layers

---

## 🕹️ Control Interface (claractl / scripting)
- [ ] `[Diff: 3]` IPC core: `QLocalServer` (UNIX socket) started by the GUI (`--control-socket`), newline-delimited JSON request/response protocol
- [ ] `[Diff: 2]` Single command/ops layer shared by CLI + server + scripting (`getallnodes`, `getnode`, `getallconnections`, `movenode`, `connect src aport dst bport`, `disconnect`, `arrange`, `setlinestyle`, `getgraph`, `nodesinfo`)
- [ ] `[Diff: 2]` `claractl` CLI + `carla --getnodeinfo` alias - connect to a running instance, print JSON or tables
- [ ] `[Diff: 3]` In-UI scripting tab - `exec` user code with a `Clara` facade injected into globals (no imports), e.g. `Clara.getAllNodes() -> dict`
- [ ] `[Diff: 2]` MCP/lib wrapper exposing the same ops layer for external agents

---

## 🧩 UI Decoupling & Multi-Framework Architecture (Parked)
- [ ] `[Diff: 3]` Extract Headless Session & Engine Controller: Decouple backend state and event dispatching from `carla_host.py:HostWindow` into a framework-agnostic `SessionController`.
- [ ] `[Diff: 2]` Standardize UI Manifest & Operations API: Implement pure command bus (`core/ops.py`) for pluggable frontends (Transport, Rack, Patchbay, Plugin Browser, Session).
- [ ] `[Diff: 2]` Framework-agnostic Rack and Canvas data models: Decouple `carla_skin.py` and `patchcanvas/` logic from `QWidget` / `QGraphicsItem` hierarchies.
- [ ] `[Diff: 3]` WebSocket / IPC Gateway: Allow alternative modern frontends (Tauri, Slint, Web) to connect and bidirectionally sync with running Clara instances.

---

## 📦 Packaging & Distribution
- [x] `[Diff: 1]` Create and maintain `clara-bin` package on AUR for rapid binary installations alongside `clara-git`
- [x] `[Diff: 3]` feat: AppImage build with standalone builder bundling CPython + PyQt6/Qt6
- [x] `[Diff: 2]` feat: Flatpak manifest (`org.kde.Platform` 6.8 runtime) + automated CI workflow
- [x] `[Diff: 1]` Decide Qt bundling policy: bundle libQt6 + PyQt6 inside AppImage/Flatpak for modern system portability
