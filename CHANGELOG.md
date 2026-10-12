# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Overview

Recent developments enhance the Carla modular audio host across three primary pillars:
1. **Patchbay Navigation & Modal Workflow**: Introduced Photoshop/Blender-style modal tools (`V`, `H`, `Space`, `Q`), directional marquee box selection, non-overlapping repelling node arrangements, and minimap zoom synchronization.
2. **Session Lifecycle & Autosave Safety**: Implemented rotating autosaves, recursive `.autosaves/` directory prevention, automatic project dirty tracking on node moves/connections, and save-on-exit prompts (`Save`, `Discard`, `Cancel`) with live countdown timers.
3. **Structured Rich Logging & Tag Filtering**: Added Python `rich` console formatting with categorical tag coloring (`APP`, `ENGINE`, `PATCHBAY`, `PLUGIN`, `SESSION`, `CANVAS`, `BACKEND`), low-level C++ backend `stderr` interception, CLI flags, and in-UI tag checklist filters.

---

## [Unreleased] - 2026-10-12

### 2026-10-12 16:47:00 (`79af505ae`)
- **fix(canvas)**: Preserve active selection on canvas right-click and add Select menu to node context menu
  - Prevented right-click mouse press and release on canvas background from deselecting highlighted items in `scene.py`.
  - Added "Select" submenu (`Select All`, `Deselect`, `Invert Selection`) to both canvas background and node item context menus in `canvasbox.py`.

### 2026-10-12 16:40:00 (`86543b139`)
- **feat(canvas)**: Add patchbay selection shortcuts and context menu actions
  - Implemented `Ctrl+A` (Select All), `Ctrl+D` (Deselect All), and `Ctrl+Shift+I` (Invert Selection) in `DraggableGraphicsView`.
  - Added dedicated "Select" submenu in the patchbay background context menu exposing all selection actions.
  - Implemented `selectAllNodes()`, `deselectAllNodes()`, and `invertNodeSelection()` helpers in `patchcanvas.py`.

### 2026-10-12 16:30:00 (`ff593af74`)
- **fix(canvas)**: Prevent blurry text rendering on patchbay ports and box titles
  - Rounded text coordinates to integer pixel positions in `canvasport.py` and `canvasbox.py` to eliminate subpixel coordinate blur under OpenGL viewports.
  - Temporarily disabled geometric polygon antialiasing right before invoking `painter.drawText()`, allowing font rasterization to utilize sharp native hinting instead of multisample edge blurring.

### 2026-10-12 16:23:15 (`2357653cc`)
- **fix(canvas)**: Enable 4x MSAA hardware multisampling for OpenGL canvas viewport
  - Configured `QSurfaceFormat` with 4 samples on `QOpenGLWidget` when canvas antialiasing is enabled, resolving jagged lines and missing antialiasing when using OpenGL hardware acceleration.
  - Exported `QSurfaceFormat` in `qt_compat.py`.

### 2026-10-12 17:42:00
- **feat(patchbay)**: Implement dynamic source-to-destination gradient coloring along cables
  - Updated `CanvasLine.updateLineGradient()` to construct `QLinearGradient` directly oriented between output and input port endpoints (`scenePos()`).
  - Smoothly interpolates the cable color between the source port color at 0.0 and destination port color at 1.0.

### 2026-10-12 17:36:00 (`dd3cab7d0`)
  - Fixed `NameError: name 'QComboBox' is not defined` when opening Carla Settings dialog by importing `QComboBox`, `QSlider`, and `QSpinBox` via `qt_compat.py`.
  - Added `QSpinBox` to Qt5 and Qt6 exports in `qt_compat.py`.

### 2026-10-12 17:34:00 (`38b2215df`)
- **feat(canvas)**: Expose line style, pattern, and opacity in Canvas Settings
  - Added configurable options `Canvas/LineStyle` (`"bezier"`, `"straight"`, `"stepped"`), `Canvas/LineStroke` (`"solid"`, `"dotted"`, `"dashed"`), and `Canvas/LineOpacity` (20% – 100%) in `carla_shared.py`, `patchcanvas/__init__.py`, and `carla_host.py`.
  - Added line style and pattern comboboxes and an interactive opacity slider in `carla_settings.py`.
  - Updated `CanvasLine` to dynamically scale line alpha by user opacity settings.
- **refactor(qt)**: Complete migration of all custom UI widgets in `widgets/` to `qt_compat.py`
  - Exported missing UI items (`QKeySequence`, `QShortcut`, `QListWidget`, `QSvgWidget`, `QToolButton`, `QDial`, `QConicalGradient`, `QProgressBar`, `QGraphicsSimpleTextItem`, `QActionGroup`) in [`qt_compat.py`](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/qt_compat.py).
  - Cleaned up `if qt_config == 5:` boilerplate across all 13 widget modules in `widgets/` (`draggablegraphicsview.py`, `canvaspreviewframe.py`, `pixmapdial.py`, `scalabledial.py`, `commondial.py`, `digitalpeakmeter.py`, `paramspinbox.py`, `pianoroll.py`, `racklistwidget.py`, `scalablebutton.py`, `ledbutton.py`, `collapsablewidget.py`, `pixmapkeyboard.py`).

### 2026-10-12 17:11:00
- **fix(qt)**: Resolve `qt_config` NameError in `theme.py` and clean up `canvasbox.py`
  - Replaced manual `qt_config == 6` branches in `theme.py` (`parse_pen`, font weight) with standard `Qt` pen style and `QFont.Bold` / `QFont.Normal` aliases.
  - Added `QImage.Format_ARGB32` and `QImage.Format_RGB32` aliases to `qt_compat.py`.
  - Removed obsolete runtime `qt_config` imports in `canvasbox.py` inline display and `itemChange`.

### 2026-10-12 17:09:00
- **refactor(qt)**: Centralize Qt5/Qt6 imports through `qt_compat.py` across `patchcanvas`
  - Exported missing Qt items (`QGraphicsPathItem`, `QGraphicsLineItem`, `QGraphicsObject`, `QGraphicsDropShadowEffect`, `QFontMetrics`, `QPolygonF`, `pyqtSignal`, `pyqtSlot`, `qFatal`, `qWarning`, `QAbstractAnimation`, `QGraphicsSvgItem`, `QSvgRenderer`, `QFormLayout`, `QGroupBox`, `QTabWidget`, `QTableWidget`, `QTableWidgetItem`) in [`qt_compat.py`](file:///home/acroarch/Documents/Projects/git-clones/Carla/source/frontend/qt_compat.py).
  - Replaced repetitive `if qt_config == 5: from PyQt5... elif qt_config == 6: from PyQt6...` import boilerplate across all `patchcanvas` modules with direct `from qt_compat import ...`.

### 2026-10-12 17:03:00
- **refactor(canvas)**: Unify line drawing and Bézier formulas into single configurable `CanvasLine`
  - Re-implemented `CanvasLine` as a flexible `QGraphicsPathItem` supporting orthogonal geometry `shape` (`"bezier"`, `"straight"`, `"stepped"`) and stroke pattern (`"solid"`, `"dotted"`, `"dashed"`).
  - Maintained backward-compatible `CanvasBezierLine` subclass alias and stub module.
  - Eliminated duplicate boilerplate across line implementations while enabling future custom path and stroke styling.

### 2026-10-12 16:53:00
- **perf(canvas)**: Cache gradient `QPen` in `CanvasBezierLine`/`CanvasLine` — built once in `updateLineGradient()`, reused in `paint()`. Eliminates hundreds of `QPen`/`QLinearGradient`/`QColor` heap allocs per mousemove tick with many connections.
- **perf(canvas)**: Early-return in `updateLineSelected()` when selection state is unchanged — skips full gradient recompute on every drag event when nothing visually changed.
- **perf(canvas)**: Guard cosmetic double-draw (glow overlay) in line `paint()` behind `options.eyecandy` — saves one full path/line draw per connection per frame when eye candy is off.
- **perf(canvas)**: Cache theme attribute lookups in `CanvasPort` — resolved once at port creation and on `updateTheme()` instead of dict-instantiation + `getattr` f-string lookups on every `paint()` frame for every visible port.
- **perf(canvas)**: Throttle minimap update timeout from 0ms to 150ms — stops full scene re-renders for the thumbnail on every event.
- **perf(canvas)**: Reduce `CanvasBoxShadow` blur radius from 20 → 8 — cuts per-box offscreen composite buffer cost.

### 2026-10-12 15:59:00 (`3f3c6711c`)
- **perf(canvas)**: Remove `repaintLines()` cascade from `CanvasBoxShadow.draw()` — eliminates per-frame `updateLinePos()` call on every box shadow repaint, which was cascading into O(connections) work every render tick when dragging nodes with many connections loaded.

### 2026-10-12 15:37:00 (`e213d7f02`)
- **fix(canvas)**: Fix HighQualityAntialiasing crash and expose Use OpenGL in Canvas settings
  - Fixed `AttributeError: type object 'QPainter' has no attribute 'HighQualityAntialiasing'` on Qt6 by safely probing `QPainter.RenderHint`.
  - Exposed "Use OpenGL for rendering (needs restart)" directly in **Settings → Canvas → Rendering** with bidirectional state synchronization to the Experimental tab.

### 2026-10-12 15:26:30 (`e225021e5`)
- **perf(canvas)**: Optimize patchbay rendering with SmartViewportUpdate and eliminate event hot path logging
  - Upgraded graphicsView viewport update mode to `SmartViewportUpdate` for intelligent partial blits when dragging nodes and cables.
  - Removed per-click and per-miss verbose `log_carla` calls in `CanvasViewportFilter` to prevent hot-path I/O stalls during interaction.
  - Streamlined cable render pipeline in `CanvasBezierLine.paint` by removing redundant double path stroking.

### 2026-10-12 15:20:45 (`6c4960fc0`)
- **fix(ui)**: Fix rack plugin removal across all skins and enable empty canvas left-click drag panning
  - Connected `b_remove` in `PluginSlot_Calf` and fixed `Delete` key handling in `RackListWidget` to invoke `self.host.remove_plugin()` with a confirmation prompt.
  - Implemented left-click drag panning on empty canvas area in `DraggableGraphicsView` for fluid navigation without needing to switch modal tools.

### 2026-10-12 15:09:12 (`b2ab7196b`)
- **fix(compat)**: Restore QSizePolicy in PyQt6 imports in qt_compat
  - Re-added `QSizePolicy` to the `PyQt6.QtWidgets` import list so `QSizePolicy.Policy` alias definitions resolve correctly on startup.

### 2026-10-12 15:07:45 (`839cdd56a`)
- **feat(ui)**: Add side-by-side split view and bidirectional rack-patchbay synchronization
  - Added toggleable Side-by-Side View mode (`Ctrl+Shift+R`) placing Patchbay (left) and Rack (right) in an adjustable `QSplitter` layout.
  - Implemented bidirectional selection sync: selecting a node in the Patchbay centers and scrolls to its slot in the Rack; selecting a slot in the Rack highlights and centers the node on the canvas.
  - Exported `QSplitter` and `QWidget` in `qt_compat.py` for cross-version Qt compatibility.

### 2026-10-12 14:34:44 (`5cac2b881`)
- **fix(session)**: Propagate dirty modifications on node moves, connects, and deletes
  - Wired `markProjectModified()` into `ACTION_GROUP_POSITION` moves so node relocations flag unsaved edits.
  - Linked cable connection / disconnection actions and backend plugin add / remove / rename callbacks to mark project state as modified.
  - Fixed exit prompt bypassing by ensuring dirty state triggers the Save/Discard/Cancel dialog.

### 2026-10-12 14:27:40 (`9e46f070a`)
- **feat(session)**: Add save on exit prompt, dirty state indicator, and autosave countdown timer
  - Implemented save-on-exit dialog with `Save`, `Discard`, and `Cancel` options when unsaved edits exist.
  - Added visual dirty indicator (`*` prefix in title bar and `● Unsaved` / `✓ Saved` status bar badge).
  - Added live statusbar timer displaying last autosave time and countdown to next autosave.

### 2026-10-12 14:19:02 (`d58a34d15`)
- **fix(logging)**: Capture C++ backend stderr into CarlaLogger
  - Intercepted file descriptor 2 (POSIX `stderr`) using `os.dup2` to capture C++ backend assertion failures and plugin bridge messages directly into `CarlaLogger`.
  - Started stderr capture at launcher startup in `source/frontend/carla`.

### 2026-10-12 09:58:45 (`ac84a74e5`)
- **fix(logging)**: Remove right padding on log levels, add per-tag colors, and handle backend assertion logs
  - Removed fixed right-padding on log level badges (e.g. `[INFO]`).
  - Added distinct color themes for all categories (`APP`, `ENGINE`, `PATCHBAY`, `PLUGIN`, `SESSION`, `CANVAS`, `BACKEND`).
  - Classified incoming `[carla]` assertion failures into `[BACKEND]` error logs.

### 2026-10-12 09:51:38 (`539c08c44`)
- **fix(logging)**: Import QFrame, QCheckBox, QLabel, QVBoxLayout in carla_host
  - Exported `QCheckBox` across PyQt5 and PyQt6 in `qt_compat.py`.
  - Resolved `NameError: name 'QFrame' is not defined` during host window initialization.

### 2026-10-12 09:45:02 (`621a4e998`)
- **feat(logging)**: Rich terminal output, tag filtering checklist, and mirror settings
  - Created centralized `CarlaLogger` supporting Python `rich` formatting, log levels, and categories.
  - Added CLI flags (`--log-level`, `--log-whitelist`, `--log-blacklist`, `--console-log`, `--no-console-log`).
  - Added in-UI Log tab tag checklist filter to dynamically toggle visible categories without losing log history.
  - Added setting checkbox to mirror application logs to terminal.

### 2026-10-12 04:01:07 (`5e318622a`)
- **fix(autosave)**: Prevent recursive nested autosave directories on recovery
  - Added `get_canonical_project_filepath` to normalize paths and strip `.autosaves/` segments when recovering.
  - Separated canonical project file path from recovery source override in `loadProjectNow`.
  - Pruned corrupted nested autosave directories and duplicate plugin folders.

### 2026-10-12 03:53:18 (`2de8b65f0`)
- **feat(patchbay)**: Add modal tools, floating toolbar, fix zoom minimap, and update interactions
  - Implemented Photoshop/Blender-style modal tools (`V` for marquee, `H` / `Space` for hand/pan, `Q` / `Escape` for pointer).
  - Added floating modal tool pill widget (`CanvasToolBarOverlay`) with cached Nerd Font glyphs.
  - Fixed minimap viewport coordinate mapping and zoom scale synchronization.
  - Made patchbay keyboard shortcut help overlay draggable across viewport.

### 2026-10-12 03:11:08 (`8bec393b0`)
- **fix(patchcanvas)**: Correct connection endpoint attribute names in moveAsideNonConnectedNodes
  - Fixed `AttributeError: 'connection_dict_t' object has no attribute 'group_id_1'`.

### 2026-10-12 03:06:24 (`e4c2b5be0`)
- **feat(patchcanvas)**: Add 'Move Aside Non-Connected Nodes' arrange action
  - Added background context menu option to shift unconnected nodes away from active graphs.

### 2026-10-12 03:00:16 (`f8bc296df`)
- **fix(patchcanvas)**: Fix mouse dragging for canvas panning, node movement, and right-drag marquee disambiguation
  - Restored canvas panning and item dragging without event swallowed in `DraggableGraphicsView`.
  - Added background click to deselect items.

### 2026-10-12 02:53:19 (`fae78c8d2`)
- **feat(patchcanvas)**: Fix right-drag marquee gesture, background deselect, and zoom-invariant line/selection widths
  - Device-pixel-invariant stroke widths for connection lines and node borders when zooming.

### 2026-10-12 02:40:54 (`60c3ac6a9`)
- **feat(patchcanvas)**: Add directional right-drag marquee selection and non-overlapping node alignment
  - Left-to-right drag selects all touched/intersected items; right-to-left drag selects enclosed items only.
  - Added repel spacing in horizontal and vertical alignment to avoid node overlap.
