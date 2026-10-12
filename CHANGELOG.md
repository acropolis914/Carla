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

### 2026-10-12 23:55:00
- **feat(patchbay)**: Infinite canvas, legacy project migration, and side-by-side layout persistence
  - Implemented dynamic scene and bounds expansion (`canvas.size_rect`, `sceneRect()`) in `canvasbox.py` and `scene.py` removing fixed boundary clamping for an infinite canvas experience.
  - Automatically recenters legacy save files lacking `infinite_canvas = true` upon load while preserving exact coordinates for modern infinite canvas projects.
  - Added canvasbox sub-bar button (`\uf066` / `\uf065`) to dynamically collapse and hide unconnected ports.
  - Tightly grouped unconnected nodes within cluster bounds when triggering "Move Aside Non-Connected Nodes".
  - Persisted `infinite_canvas`, `hide_unconnected_ports`, and side-by-side split view layout state (`split_view_enabled`, `split_view_sizes`) across XML and JSON formats.

### 2026-10-12 23:28:00
- **feat(ui)**: Enlarged FontAwesome Nerd Font icons and TODO tracker update
  - Increased font-size for action buttons (`b_power`, `b_bypass`, `b_gui`, `b_edit`, `b_slider_mode`, `b_minimize`) from 11px to 13px (12px on minimize) for enhanced legibility.
  - Increased canvas box toolbar button icon font size to 9pt on 18×18 square targets.
  - Checked off canvas box sub-bar action buttons in `TODO.md`.

### 2026-10-12 23:26:00
- **feat(ui)**: Pure FontAwesome Nerd Font buttons and transparent button styling
  - Converted Power (`\uf011`), Bypass (`\uf05e`), Custom UI (`\uf2d0`), and Parameters/Edit (`\uf013`) into pure `QPushButton` controls using FontAwesome Nerd Font glyphs.
  - Eliminated static background fills across all header buttons (Bypass, Expand/Minimize, Power, GUI, Edit, Slider mode) for a clean, borderless transparent look.
  - Added subtle hover (`0.08`) and pressed (`0.16`) translucent feedback without distracting borders or hard backgrounds.

### 2026-10-12 23:22:00
- **feat(ui)**: Clean borderless buttons, consistent type badge width, and FontAwesome / Nerd Font glyphs
  - Removed all button border outlines in both Rack headers and Canvas boxes for a clean, minimal look.
  - Standardized the Type Badge width to 56px with centered alignment so plugin titles align uniformly.
  - Converted minimize/expand (`\uf077` / `\uf078`) and slider view toggles (`\uf0c9` / `\uf1de`) to FontAwesome / Nerd Font icons with 22×22 square sizing.
  - Kept Custom UI button (`b_gui`) always visible, transitioning into a disabled state when unavailable.

### 2026-10-12 23:15:00
- **feat(ui)**: Standardized square action buttons, Nerd Font icons, and responsive header layout
  - Fixed action buttons (`b_enable`, `b_bypass`, `b_gui`, `b_edit`) to consistent square dimensions (22×22 px in rack slots, 18×18 px in canvas boxes) with 3 explicit states: Active (accent glow/border), Inactive (neutral subtle border), and Disabled/Unavailable (greyed out `opacity: 0.35`).
  - Unified iconography with FontAwesome / Nerd Font glyphs across Canvas and Rack headers (`\uf011` Power, `\uf05e` Bypass, `\uf08e` Jump to Rack).
  - Repositioned the category/type badge pill before the plugin name in the rack header for uniform left title alignment.
  - Reduced minimum width constraints (down to 260px) and set preset selector sizing for responsive layout fitting on smaller screens.
  - Added comprehensive tooltips to all header buttons, type badge, and preset controls.

### 2026-10-12 23:00:00
- **feat(rack)**: CarlaSkin 2-line headers and canvas-style buttons
  - Restructured plugin slot headers into a 2-line layout: Line 1 aligns the plugin title, type badge, peak meters, and minimize toggle; Line 2 provides a dedicated action toolbar for power, bypass, GUI, edit, presets, and slider mode.
  - Increased left margin padding to give the category colorbar generous separation from the controls.
  - Upgraded rack buttons to mirror canvas box aesthetics with neutral translucent backgrounds (`rgba(255, 255, 255, 0.05)`), subtle borders (`0.12`), hover highlights, and crisp pressed feedback.
  - Resolved plugin active state synchronization between patchbay canvas toolbar and host engine/rack widget (`pwidget.setActive(..., sendHost=True)`).
  - Toggling power now updates the DSP engine, rack UI enable toggle, and canvas node simultaneously.
- **feat(patchbay)**: Toolbar button visuals and tactile feedback
  - Removed darker shading and dividing line behind canvas box toolbar buttons for a seamless transparent look.
  - Added interactive visual feedback for buttons including hover glow, distinct pressed background highlight, and tactile 1px offset shift.

### 2026-10-12 22:22:00
- **feat(patchbay)**: Neutral square toolbar styling
  - Adjusted sub-bar height to 22px and rendered 14×14 square buttons with 4px top/bottom padding.
  - Replaced colored fills with unified neutral translucent backgrounds, subtle borders, and muted icon tints.

### 2026-10-12 21:50:00
- **feat(patchbay)**: Semantic Bypass button and "Jump to Rack" context menu
  - Preserved the native top-left icon (`CanvasIcon`) completely undisturbed; plugin titles display with clean padding.
  - Added "Jump to Rack" to the node right-click context menu for all rack plugins, focusing and scrolling the paired rack item smoothly without header clutter.
  - Placed the compact, semantic power toggle (`⏻`) neatly on the right next to the category badge pill, rendering only for plugins that expose bypass capabilities.
  - Ensured clicking bypass toggles the active state in-place without triggering selection sync or shifting views.


- **refactor(cli)**: Modernize command-line argument parsing with `argparse.ArgumentParser`
  - Replaced legacy manual `sys.argv` string inspection loop in `handleInitialCommandLineArguments()` with standard `argparse.ArgumentParser` and `parse_known_args()`.
  - Unified host options and `CarlaLogger` configuration (`--log-level`, `--log-whitelist`, `--log-blacklist`, `--console-log`, `--no-console-log`) into a single declarative parser.
  - Safely handles positional project files, OSC URLs, and unknown backend pass-through flags without errors.
  - Automatically loads plugins in bridge mode and selects newer autosaves without prompt dialogs when `--autoload-lastsave` is active.

- **docs(cli)**: Rich colored help banner with app info, versions, and full tag options
  - Added Carla version header, Python, Qt, PyQt version specs, and binary/resource paths directly inside `--help`.
  - Added ANSI color highlighting for options, arguments, and tags.
  - Listed all available logging filter tags (`APP`, `ENGINE`, `PATCHBAY`, `PLUGIN`, `SESSION`, `CANVAS`, `BACKEND`) in `--log-whitelist` and `--log-blacklist`.
  - Added binary stream decoding and control-character sanitization to stderr capture in `CarlaLogger`.
  - Wired explicit debug level forwarding from `log_carla()` through `DEBUG_LEVEL_MAP` to prevent suppression leaks.

- **refactor(logging)**: Deduplicate repeated messages and filter non-fatal backend assertion noise
  - Added consecutive log deduplication in `CarlaLogger` with repeat counting to prevent runaway spam in console output.
  - Filtered benign C++ backend assertions (`canRead`, `groupName != nullptr`, `TemporaryFile`, buffer sizes, `plugin.get() != nullptr`) to debug level.
  - Suppressed yabridge/Wine boilerplate, duplicate LV2 plugin notices, `carla_v3_component_handler` queries, and `PatchCanvas::removeGroup` warnings on shutdown.
  - Demoted high-frequency port discovery, client addition, and connection callback messages (`addPort`, `connectPorts`, `slot_handlePatchbayClientAddedCallback`, `addGroup`, `unhiding box`) to debug level, keeping default info level clean.

- **feat(patchbay)**: Add type-based node selection to patchbay context menus
  - Implemented `getNodeBadgeType()` on `CanvasBox`, mapping each node to its exact functional type (`SYNTH`, `EQ`, `DELAY`, `FILTER`, `DIST`, `DYN`, `MOD`, `UTIL`, `FX`, `PLUGIN`, `SINK`, `SOURCE`, `IN`, `OUT`, `HW`, `APP`, `NODE`).
  - Added "Select All of Same Type ({type})" to individual node context menus.
  - Added "Select -> By Type" dynamic submenu to both canvas background and node item context menus.
  - Added `selectNodesByType(target_type)` and `getAvailableNodeTypes()` in `patchcanvas.py`.

- **feat(patchbay)**: 100% badge coverage across all plugins, external clients, and I/O nodes
  - Added fallback badges `PLUGIN` (Blue) and `SYNTH` (Red) for plugins without explicit category tags.
  - Added `APP` (Mauve) for bidirectional client apps and `NODE` (Slate) fallback, guaranteeing every node displays a badge.

- **feat(patchbay)**: Add header badge pills for sinks, sources, hardware, and inputs/outputs
  - Implemented dynamic role detection in `canvasbox.py` for non-plugin nodes.
  - Added color-coded badges: `SINK` (Green), `SOURCE` (Peach), `IN` (Sky), `OUT` (Yellow), and `HW` (Lavender) alongside existing category badges.

- **feat(patchbay)**: Neutral default nodes with clean category badges in header
  - Removed forced default category coloring so unstyled nodes and rack items remain clean and neutral by default.
  - Implemented crisp, color-coded category pill badges (e.g. `SYNTH`, `FX`, `EQ`, `DYN`, `UTIL`) inside patchbay node headers for instant visual classification without cluttering or tinting the whole node.

- **fix(color)**: Properly reset patchbay node color to default category tone when rack item color is reset
  - Updated `changePluginColor()` in `carla_host.py` to restore the node's Catppuccin category color when resetting a rack item rather than leaving it in an unsynced state.
  - Updated `getColorAndSkinStyle()` and `createPluginSlot()` in `carla_skin.py` to cleanly revert to the category palette whenever `CarlaColor` is reset to `"255;255;255"`.

- **feat(patchbay)**: Support individual color customization and persistence for non-rack patchbay items
  - Enabled color selection and persistence for all patchbay items (e.g. ALSA, JACK, PipeWire hardware, external clients) via canvas positions metadata in `patchcanvas.py` and `project_storage.py`.
  - Serialized custom node colors into project files (`.carxp`, `.carjp`, `.json`) under canvas group position tags.
  - Prioritized mapped rack item colors on load so synced rack items always govern their canvas counterparts while standalone nodes retain their independently assigned colors.

- **feat(patchbay)**: Improve node header readability with soft color tinting and adaptive contrast text
  - Blended 35% custom color tint with base header background in `canvasbox.py` for distinct, non-garish node headers.
  - Added custom color accent divider line under node headers.
  - Implemented dynamic luminance calculation for node header text to guarantee high contrast and readability against tinted headers.

- **fix(color)**: Bidirectional saved color synchronization on project load & vibrant category palettes
  - Updated `getColorFromCategory()` in `carla_skin.py` to use vivid Catppuccin category tones instead of dark gray shades, giving unstyled nodes and rack items distinct colors immediately.
  - Aligned rack context menu structure by elevating Color submenu to the top level, matching canvas node context menus with direct `QColorDialog` triggers.
  - Synchronized colors directly from rack widgets (`fSkinColor`) to patchbay canvas nodes on both `PluginListItem.recreateWidget()` and `slot_handlePatchbayClientAddedCallback()`.

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

### 2026-10-12 18:30:00
- **fix(rack)**: Fix persistence and startup synchronization of saved plugin colors on canvas nodes
  - Added project dirty tracking and `markProjectModified()` on `changePluginColor()` to ensure custom colors persist on save.
  - Linked `setGroupAsPlugin()` in `patchcanvas.py` to fetch saved `CarlaColor` custom data from the engine and immediately tint the patchbay node and its cable connections upon project loading.

### 2026-10-12 18:58:00
- **feat(patchbay)**: Assign distinctive Catppuccin category colors to nodes by default and sync saved colors
  - Added default Catppuccin category color palette mapping (Synth: Red, Delay: Sky, EQ: Green, Filter: Teal, Distortion: Peach, Dynamics: Yellow, Modulator: Mauve, Utility: Lavender, Other: Blue) for patchbay nodes without explicit custom overrides.
  - Linked `CarlaColor` retrieval in `setGroupAsPlugin()` to restore project-saved custom node tints reliably upon initial load.

### 2026-10-12 18:24:00 (`e577fae12`) (`e577fae12`)
- **fix(canvas)**: Ensure cable gradients render regardless of line formula (bezier/straight/stepped) and stroke pattern
  - Recomputed `updateLineGradient()` on every `updateLinePos()` to ensure gradients always match latest node positions.
  - Fixed painter rendering in `CanvasLine.paint()` to draw directly with `_cached_pen` preserving `QBrush` gradient fill across all line shapes and stroke patterns (`solid`, `dotted`, `dashed`).

### 2026-10-12 18:20:00 (`ceaa6b6e1`)
- **fix(canvas)**: Fix cable linear gradients not rendering across canvas nodes
  - Resolved gradient vector calculation in `CanvasLine.updateLineGradient()` by mapping scene port bounding rect endpoints into the item's local coordinate system (`mapFromScene()`).
- **feat(rack)**: Add unified Catppuccin color palette and custom color picker to rack item menu
  - Replicated horizontal Catppuccin preset palette into rack `Appearance -> Color` context menu.
  - Added "Custom Color..." `QColorDialog` picker and "Reset Color" to both patchbay node and rack context menus.
  - Synchronized color changes bidirectionally between rack items and `group.widgets` on the patchbay canvas.
  - Applied subtle 15% custom tint formula to patchbay node body backgrounds to match rack styling.

### 2026-10-12 17:57:00 (`2f3ba4308`)
- **fix(rack)**: Fix bidirectional color synchronization between patchbay nodes and rack items
  - Connected `ACTION_PLUGIN_COLOR` to `changePluginColor()` to update rack skins with the selected Catppuccin color and persist to `CarlaColor`.
  - Added reverse synchronization from `changePluginColor()` to `CanvasBox.setCustomColor()` on patchbay nodes.

### 2026-10-12 17:53:00 (`4dab86fee`)
- **feat(rack)**: Synchronize node colors between patchbay and rack items
  - Added `ACTION_PLUGIN_COLOR` to patchcanvas callback architecture and notified when `setCustomColor()` is changed on a plugin node.
  - Linked `canvasCallback` to propagate the custom tint color to the corresponding `PluginListItem` in the rack.

### 2026-10-12 17:47:00 (`f5ca2fe6a`)
  - Added "Color" submenu to node context menu with horizontal one-click Catppuccin color buttons (Red, Peach, Yellow, Green, Teal, Sky, Blue, Lavender, Mauve, Pink) and reset button.
  - Linked custom node colors into `CanvasLine.updateLineGradient()`, dynamically tinting connection cable gradients to match source and target node colors.

### 2026-10-12 17:42:00 (`ef964798a`)
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

---

## [Unreleased] - 2026-10-06

### 2026-10-06
- **perf(patchbay)**: Debounce heavy canvas refresh during rack reordering (`3bdb33f11`)
  - Throttled canvas redraw triggers while drag-reordering rack items to eliminate UI stuttering.
- **refactor(rack)**: Native `moveRow` reordering without manual widget shuffling (`1b32d180a`)
  - Switched rack reordering to use native `QModelIndex::moveRow`, preventing Qt garbage collection segfaults.
- **fix(rack)**: Prevent list widget crashes and destruction during fast reordering (`a897cf0c5`, `fb6dd9261`, `c44f4161b`, `f57456a4e`)
  - Parked widgets in temporary holding container during moves rather than unparenting to `None`.
  - Preserved active rack selection state seamlessly during item drag-reordering.
- **feat(ui)**: Modern native rack buttons and Unicode symbol icons (`815691ce8`, `67e54e3b9`, `b7c76a47d`, `fb8318e89`)
  - Replaced overlapping power icons with native dark-themed `QPushButton` for bypass and minimize controls.
  - Updated UI iconography to clean Unicode symbols across compact and standard rack modes.

---

## [Unreleased] - 2026-10-05

### 2026-10-05
- **feat(packaging)**: Arch Linux / Pacman integration and PKGBUILD (`f8a2a6c79`, `9105b012b`, `8d4984256`)
  - Added native `PKGBUILD` for `carla-improved` package targeting Qt6.
  - Added helper `build.sh` script and `installation.md` guide for rapid building and pacman installation.
- **feat(session)**: Recent projects list and autoload on startup (`4da5fdaa8`)
  - Added `Recent Projects` submenu under `File` with file path previews.
  - Added startup prompt to resume last opened project and `--autoload-lastsave` CLI flag.
- **feat(patchbay)**: Canvas node quick search with fuzzy matching (`0f50c125f`)
  - Implemented `Ctrl+F` in-canvas search bar with fuzzy filtering and direct viewport centering.
- **feat(patchbay)**: Persistent canvas node coordinates in project files (`c79581357`)
  - Automatically saved and restored canvas node positions inside `.carxp` project files.
- **feat(ui)**: Blender-inspired socket aesthetics, rounded nodes, and system typography (`e4eeb3315`, `311e6d60c`)
  - Introduced circular socket styling, rounded canvas node containers, and refined port colors.
  - Unified system fonts across the interface and added initial CLI debug/logging flags.
- **feat(ui)**: Pianoroll enhancements and theme system (`a6acc8bd0`, `7ba0b3c45`)
  - Styled pianoroll view, upgraded keyboard bitmaps, and installed data-driven `themes.json`.
- **fix(patchbay)**: Patchbay rack node sync and PyQt6 inline display support (`65eaa7e6a`)
  - Fixed sync between rack items and canvas nodes, port drag connections, and PyQt6 inline display rendering.

---

## [Unreleased] - 2026-10-04

### 2026-10-04
- **fix(canvas)**: Initial patchbay canvas stability improvements (`831bf93b3`)
  - Fixed initial canvas rendering glitches, drag-connection line offsets, and view initialization.

