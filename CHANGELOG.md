# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Overview

**Clara** (*Carla Improved*) key highlights:
- **Modal Navigation**: Photoshop/Blender hotkeys (`V`, `H`, `Space`, `Q`), infinite canvas, directional marquee box selection, and minimap tracking.
- **Dynamic Cable Gradients & Routing**: Source-to-destination color gradients with Bezier, straight, and stepped routing formulas.
- **Catppuccin Theming**: Automatic category colors, role badges (`SOURCE`, `SINK`, `HW`), and quick popup color swatches.
- **Unified Toolbars**: Floating palettes with standardized Nerd Font glyphs, batch mute/bypass, and alignment/repel tools.
- **Rack & Patchbay Sync**: Side-by-side view with bidirectional scroll, focus, and color synchronization.
- **Session Safety**: Rotating autosaves (`.autosaves/`), countdown timers, dirty edit tracking, and save-on-exit prompts.
- **Rich Diagnostics**: Terminal logs with Python `rich` formatting, color tags, and C++ backend `stderr` capture.

---


## [Unreleased]

### 2026-10-16 04:35:00
- **ci(aur)**: release pipeline now ships a real pacman package
  - `package.yml` archlinux job packages with `makepkg` as a non-root builder using the shared `.github/aur/PKGBUILD.in` template, producing `clara-bin-<ver>-1-x86_64.pkg.tar.zst` with proper `.PKGINFO`/`.MTREE` metadata as the release asset (previously a plain `clara-archlinux-*.tar.zst` DESTDIR tarball). `build-test.yml` now uses the same template instead of an inline heredoc.
  - `aur/clara-bin/PKGBUILD` now consumes the package asset via `bsdtar` extraction (excluding `.PKGINFO`/`.MTREE`) instead of copying a `usr/` tree from the plain tarball.
  - The archlinux release container installs the full runtime dependency list so the PKGBUILD dependency set is validated on every release build.

### 2026-10-16 04:20:00
- **ci(aur)**: build a real pacman package with makepkg in the test workflow
  - New `aur` choice for the `only` dispatch input plus a `build-aur` job: builds the source in an `archlinux:latest` container, then packages it with `makepkg` as a non-root user, producing `clara-bin-<ver>-1-x86_64.pkg.tar.zst` with proper `.PKGINFO` and `.MTREE` metadata (instead of the plain DESTDIR tarball the `distros` job uploads). The job asserts both metadata entries exist and uploads the result as `aur-package`.
  - The build container installs the full AUR runtime dependency list, so the dependency set declared in the PKGBUILD is validated on every run.

### 2026-10-16 04:05:00
- **fix(build)**: stop relying on `which` for tool and interpreter detection
  - `source/Makefile.deps.mk` detected the PyQt6 UI tools with `$(shell which pyuic6)`. Minimal build containers (e.g. `fedora:latest`) do not ship `which`, so `PYUIC6` came out empty, `HAVE_FRONTEND` stayed false and the fedora rpm was built without the entire python frontend (no `clara` launcher, no desktop files, only `carla-single` + libs). Switched `PYRCC5`/`PYUIC5`/`PYUIC6` detection to `command -v`.
  - `data/carla*` launcher wrappers resolved the interpreter with `PYTHON=$(which python3)` and a broken `[ ! -f ${PYTHON} ]` check. On guests without `which` (e.g. minimal arch) `$PYTHON` expanded empty and the shell tried to exec the non-executable `/usr/share/carla/carla`, dying with `line 15: /usr/share/carla/carla: Permission denied`. Switched all nine wrappers to `command -v` + `[ -z "$PYTHON" ]`.

### 2026-10-16 03:40:00
- **fix(rpm)**: stop the fedora rpm from owning shared system directories
  - `.github/workflows/specs/clara.spec` used a catch-all `%files` of `/usr/*`, which made the package claim `/usr/bin`, `/usr/include`, `/usr/lib`, `/usr/lib/lv2`, `/usr/lib/pkgconfig` and `/usr/share` as its own directories. On Fedora these belong to `filesystem`/`lv2`/`pkgconf`, so `dnf install clara-*.rpm` aborted with `file /usr/bin from install of clara-0.0.0-1.fc44.x86_64 conflicts with file from package filesystem-3.18-52.fc44.x86_64`.
  - Replaced the glob with the actual clara payload paths: `/usr/bin/*`, `/usr/include/carla`, `/usr/lib/carla`, `/usr/lib/lv2/carla.lv2`, `/usr/lib/pkgconfig/*`, `/usr/share/carla`.

### 2026-10-16 01:30:00
- **fix(ci)**: make the void-musl build actually link and fail loudly
  - The musl jobs set `LDFLAGS='-lfts $LDFLAGS'` with single quotes, so the literal `$LDFLAGS` was stored; make then expanded it as `$L` + `DFLAGS`, producing `ld: cannot find DFLAGS`. Changed to `LDFLAGS="-lfts $LDFLAGS"` in `build-test.yml`, `package.yml` and `package-aarch64.yml`.
  - The musl build hid failures (`docker ... sh -c` with no `set -e`, and `make | tee` masking make's exit code), so a broken build still uploaded a near-empty tarball as success. Added `set -e` and made `make`'s exit status propagate.
  - Added a `only` dispatch input to `build-test.yml` so a single component (e.g. `void-musl`) can be built and re-tested without running every job.

### 2026-10-16 00:45:00
- **fix(ci)**: build VST frontend stubs on every distro and make the rpm version legal
  - alpine/archlinux/fedora jobs now install the OpenGL + X11 development packages (`mesa-dev libx11-dev libxcursor-dev libxext-dev libxrandr-dev`, `mesa libglvnd libx11 libxcursor libxext libxrandr`, `mesa-libGL-devel libX11-devel libXcursor-devel libXext-devel libXrandr-devel`). `HAVE_DGL` requires `pkg-config --exists gl x11 xcursor xext xrandr`; without it the VST2 plugin stubs (`bin/CarlaRack*`, `bin/CarlaPatchbay*`) are never built and `make install` fails at `install_main`.
  - The test workflow's default version is now rpm-legal (`0.0.0`, no `-`), and the fedora job rewrites `-` to `.` before writing `Version:` in the spec (rpmbuild rejects `Version: 0.0.0-test`).

### 2026-10-16 01:00:00
- **ci(test)**: add `build-test.yml` workflow for downloadable test builds
  - New `workflow_dispatch`-only workflow that builds every platform (alpine, ubuntu, fedora, archlinux, void-glibc, void-musl, nix, appimage, flatpak) and uploads the resulting packages as run artifacts. It never publishes, tags, or attaches anything to a release, so builds can be verified and downloaded locally (`gh run download`) without touching release assets.
  - Adds a per-platform "Detect frontend tooling" step that reports `pyuic6`/`uic6` locations and the `HAVE_FRONTEND`/`HAVE_QT6`/`FRONTEND_TYPE` values from `make -pn` into the run summary, to diagnose the Fedora GUI-less packaging issue.
  - Version string is a dispatch input (`version`, default `0.0.0-test`); `fail-fast` disabled so a single distro failure does not cancel the others.

### 2026-10-16 00:20:00
- **fix(ci)**: correct multi-distro packaging (frontend tooling, versioning, naming)
  - Frontend tooling: install the PyQt6 UI tools the build needs (`pyuic6`, required for `HAVE_FRONTEND`). Ubuntu `.deb` and both AppImage jobs now install `pyqt6-dev-tools`; the void-glibc and void-musl jobs install `python3-pyqt6-devel-tools`; the Fedora spec adds `python3-pyqt6` to `BuildRequires`. Previously these jobs silently produced GUI-less packages (no launcher scripts, desktop files, icons or Python frontend).
  - Packaging: removed the `make install ... || cp -r bin` fallback from every distro and void-musl job, so the stray top-level `bin/` build output is never shipped again.
  - Versioning: `build-void-musl` now sets `VERSION` (it was producing `clara-void-musl-.tar.zst`), and the AppImage is named after the Clara release version (`Clara-<release>-<arch>.AppImage`, honoring a `CLARA_VERSION` override) instead of the engine `VERSION`.
  - `scripts/release_and_push_aur.sh` now normalizes the version argument (strips leading `v`/`V`, dots and whitespace, then validates `X.Y.Z`), preventing malformed tags such as `v.1.0.1`.

### 2026-10-15 23:55:00
- **chore(releases)**: retract all published binary artifacts
  - Removed every uploaded binary asset from the GitHub releases `v0.1.0`–`v1.0.1` (including the malformed `v.1.0.1`), keeping only the auto-generated source archives. All were broken: GUI-less deb/rpm/nix/void packages (missing launcher scripts, desktop files, icons and the Python frontend), a non-starting AppImage (no frontend bundled; hard-coded `/home/runner` build paths), an empty `void-musl` tarball, and `archlinux`/`alpine` tarballs that were plain install trees rather than real `pkg.tar.zst` packages (no `.PKGINFO`/`.MTREE`).
  - Each release body now carries a "RETRACTED — DO NOT USE" notice, and `releases.json` marks every documented release `retracted`. Corrected builds will be published after the packaging fixes land.

### 2026-10-15 23:30:00
- **refactor(frontend)**: replace the Qt-linked native dialogs with pure-PyQt6 implementations
  - `libcarla_frontend` (a Qt C++ shared library) is no longer built or shipped. Its three dialogs — About, Add JACK Application, and the Plugin List browser — are reimplemented in Python under `source/frontend/dialogs/` and `source/frontend/pluginlist/`, using the non-Qt `libcarla_utils` backend for plugin discovery.
  - `CarlaFrontendLib` (`carla_frontend.py`) is now a thin pure-Python shim that keeps the same public API, so `carla_host.py` is unchanged and the app no longer needs a system Qt matching the native build (this fixes the AppImage startup crash caused by the Qt ABI mismatch).
  - Makefile: stop building/installing `libcarla_frontend`, and install the new `dialogs`/`pluginlist` Python packages.

### 2026-10-15 22:40:00
- **perf(packaging)**: shrink the AppImage significantly
  - Switched the bundled `appimagetool` from AppImageKit (gzip squashfs) to the maintained `AppImage/appimagetool`, which defaults to **zstd**, and pinned `--comp zstd --mksquashfs-opt -Xcompression-level 19` (override with `APPIMAGE_ZSTD_LEVEL`).
  - Added a `trim_appdir` pass before packaging: deletes Python test/idlelib/tkinter/`ensurepip`/pip, `__pycache__`/`*.pyc`/`*.pyo`, PyQt6 `*.pyi` stubs, Qt `translations`/`qml`/`lib/cmake`/`lib/pkgconfig`/`lib/metatypes`, `*.a`/`*.la`/`*.prl`, and `include`/`man`/`doc`, then strips every ELF with `strip --strip-unneeded`.

### 2026-10-15 22:15:00
- **ci(packaging)**: Experimental aarch64 packaging workflow
  - New manual-only `.github/workflows/package-aarch64.yml` (`workflow_dispatch`). It builds the same target set as the release workflow (alpine/ubuntu/fedora/archlinux/void archives, AppImage, Flatpak, Nix) on `ubuntu-24.04-arm` runners and attaches the results — suffixed `-aarch64` so they never clobber the x86_64 assets — to the **same** versioned GitHub Release. Targets without an aarch64 image/build fail soft (`continue-on-error`).
  - `scripts/build_appimage.sh` now accepts `--arch=aarch64` (relocatable CPython + linuxdeploy/appimagetool from the aarch64 assets); `scripts/build_flatpak.sh` derives the output arch from `uname -m`.

### 2026-10-15 21:30:00
- **ci(packaging)**: AppImage & Flatpak release jobs + docs
  - `.github/workflows/package.yml` now builds a standalone x86_64 **AppImage** and a **Flatpak** bundle on every `v*` tag and ships them as release assets alongside the deb/rpm/tar.zst/nix packages. Both jobs are non-blocking (`continue-on-error`) so a bundle problem cannot block the rest of the release.
  - README + `installation.md` document the AppImage/Flatpak installs and the `clara` primary / `carla` backwards-compatible symlink naming.
  - Bumped Clara to **1.0.1**.

### 2026-10-15 20:30:00
- **chore(release)**: Clara 1.0.0 + portable packaging
  - Bumped the Clara application version to **1.0.0** (`CLARA_VERSION_STRING`, `aur/clara-bin/PKGBUILD`, `releases.json`).
  - New **Neo Candy** app icon (mixer glyph from the GPL-3.0 `neo-candy-icons` theme) replacing the legacy Carla bitmap/SVG set; rasterized to 16/32/48/128/256px.
  - New portable **AppImage** builder (`scripts/build_appimage.sh`) that bundles a relocatable CPython + PyQt6 (which ships its own Qt6) and the native libs for x86_64.
  - New **Flatpak** assets (`data/flatpak/…`) and builder (`scripts/build_flatpak.sh`).
  - New **git tag hook** (`scripts/git-hooks/pre-push` + `scripts/install-git-hooks.sh`): pushing a `v*` tag builds the AppImage and Flatpak locally into `dist/`.
  - `clara` is the primary binary/desktop name; `carla` remains as a backwards-compatible symlink.

### 2026-10-15 19:30:00
- **ui(settings)**: Sidebar typography, Nerd Font icons & label fixes
  - Sidebar tab buttons now render a **Nerd Font glyph + label** (General, Patchbay, Engine, OSC, File Paths, Plugin Paths, Wine, Experimental) in the detected Nerd Font instead of the cleared legacy bitmap icons; the sidebar font family now follows that font (with a clean sans fallback).
  - Replaced the remaining **legacy bitmap button icons** (project-folder open, and the Add / Change / Remove buttons on File Paths and Plugin Paths) with Nerd Font glyphs.
  - Fixed the **overly long descriptive label overlapping itself**: word-wrapped help/note labels now enable `heightForWidth` and top-left alignment so the layout reserves the full wrapped height.
  - Hid two **legacy options** that are no longer worth exposing: "Full canvas repaints (slower, …)" and "Load Carla backend in global namespace (NOT RECOMMENDED)".

### 2026-10-15 18:45:00
- **ui(patchbay)**: Search interaction restyle + settings widget polish
  - Search **results dropdown** selection/hover is now Catppuccin blue (`#89b4fa`) instead of the harsh orange, with a slim themed scrollbar and **no horizontal scrollbar** (results elide to the right and use uniform item sizes).
  - The on-canvas **search match highlight** was retinted from orange to sapphire (`#74c7ec` for matches, `#89b4fa` for the active row) to match the rest of the theme.
  - Settings dialog: added consistent theming for **combo boxes** (including their dropdown popup view), **spin boxes**, **line edits**, **check boxes** and all **scrollbars**, so the settings widgets no longer fall back to the default (ugly, horizontally-scrolling) platform style.

### 2026-10-15 18:15:00
- **ui(settings)**: Settings dialog cleanup
  - Removed the leftover decorative glyphs in the **upper-right corner of every settings tab** (the old `label_10` / `label_icon_engine_5` / `label_31` / `label_19` header icons were not matched by the previous hide list, so they lingered).
  - Removed the legacy inline **info / warning 16px icons** next to the descriptive text across Engine, OSC, File Paths, Plugin Paths, Wine and Experimental tabs; the text they annotated is kept.
  - Hid the deprecated **"Fancy eye-candy"** option (its toggle handler is disabled upstream).
  - Long help / note lines now **word-wrap** and render in a muted secondary color instead of clipping into a single unreadable line.

### 2026-10-15 17:30:00
- **feat(patchbay)**: Animated signal / event flow + search moved into the top toolbar
  - **Search box relocated**: the patchbay search field is no longer a standalone floater; it now lives inside the top context toolbar as a rounded text box that stays anchored to the bar (and follows it when dragged). The results popup still drops down beneath it.
  - **Signal flow animation**: new `patchcanvas/signalflow.py` animator drives a travelling pulse along every cable and lights up active nodes, using **real engine levels** (input/output peak values polled per plugin). Each pulse has a comet tail for a clear sense of direction; active nodes get both a tinted border and a body glow whose intensity tracks loudness. Levels are smoothed with fast attack / slow decay, and the pulse is now overlaid even on router/orthogonal cables that custom-draw themselves.
  - **External / PipeWire levels**: new `patchcanvas/pwlevels.py` samples the real level of external nodes (virtual **BUS** sinks, monitors, hardware I/O, external clients) using the same hidden peak-detect tap as pavucontrol (`PA_STREAM_PEAK_DETECT` via `libpulse`, pumped on the GUI thread). Activity is keyed by canvas **group id**, and any node with no sample (e.g. a playback stream like Spotify) falls back to a slightly attenuated level borrowed from the groups it is wired to, so a fully external chain still pulses as long as one Carla plugin sits anywhere on it. Cables light up from **either** endpoint.
  - **Clean patchbay**: the observer taps (ours and third-party ones like `pavucontrol` / `pwvucontrol`) are recognised by name and filtered out of the canvas, so they never appear as nodes or in port selectors. Per-node capture can be toggled from the right-click menu of the flow button (setting `Canvas/SignalFlowExternal`, default on).
  - **Quick switch**: a new toggle button (`heartbeat` glyph) in the left canvas palette enables/disables the animation, restored from the new `Canvas/SignalFlow` setting between sessions.
  - **Cleanup**: removed the bottom-right `?` patchbay shortcuts button (its help text lives on the left-palette `btnHelp` tooltip).

### 2026-10-15 15:45:00
- **feat(patchbay)**: Search selection now persists
  - `Ctrl+F` fuzzy search now *selects* the matching nodes in the scene (in addition to the highlight), so the result set stays selected after the search box closes via Enter, click or Esc.
  - The selection persists until the user interacts with the canvas — a canvas click/drag, or the select-all / invert-selection / deselect-all shortcuts, clears it (`_clearHighlights`).
  - Because the persisted selection emits `pluginSelected`, it also drives the mini-rack sync and the floating context toolbar, so you can search and then immediately arrange / act on the result set.

### 2026-10-15 15:00:00
- **feat(canvas)**: Graph introspection model
  - New `patchcanvas/graph_info.py`: a single JSON-serialisable view of the patchbay (`collect_graph`) — nodes (id, name, split, pos/size/rect, ports with mode/type), connections (out/in group+port+node index) and derived topology (edges, incoming, degree, connected components, longest-path layers). Foundation for the layout plugins and the future claractl / scripting layer.

### 2026-10-15 14:00:00
- **feat(canvas)**: Pattern-aware heuristic auto-arrange
  - New `heuristic` arrange algorithm (`patchcanvas/arrange_heuristic.py`), labelled "Heuristic (pattern-aware)", registered after `sugiyama` and selectable from the Arrange Tools menu.
  - It detects connection topology instead of applying a single rule: splits the graph into connected components (islands), then per component recognises exclusive pairs (side by side), fan-out (source beside a vertical stack of destinations), merges (sources aligned before the sink), fully connected cliques (compact grid), stars / hub-and-spoke (sources left, hub centre, sinks right), and plain chains (following signal flow). Anything unrecognised falls back to a layered pass with barycenter crossing reduction.
  - Deterministic (ties broken by node name), reuses `_nodeGraph`/`syncNodePositions`, honours snap/grid, and leaves island separation gaps so unrelated groups do not overlap.

### 2026-10-15 13:00:00
- **perf(canvas)**: Fix multi-second freeze when applying canvas settings (pressing OK) while a pure-Python router (`router`/`orthogonal`) is the active line style.
  - `slot_configureCarla` tears down and rebuilds the whole patchbay, so every cable re-routes once; at ~50-80 ms per long cable that meant several seconds of UI block.
  - `linealgo_ortho.py`: rewrote `_astar` to a flat array-indexed state space (`index = (cell*4)|dir`, list-based `dist`/`prev`, no per-node dict/tuple allocation) and capped grid resolution (`_MAX_CELLS=72`) so cable length no longer dictates A* work. ~50-80 ms/line → ~5-10 ms/line.
  - `linealgo_router.py`: same resolution cap (`_MAX_CELLS=72`) in `plan_waypoints`. ~11-15 ms/line → ~6-8 ms/line.
  - Net effect: a ~50-cable patch drops from ~3-4 s to a few hundred ms on settings apply.

### 2026-10-15 12:00:00
- **feat(canvas)**: Orthogonal router, Sugiyama arrange
  - New `orthogonal` line algorithm (`patchcanvas/linealgo_ortho.py`): self-contained Manhattan router, a direction-aware A* over an occupancy grid with a bend-aware cost (`length + bend_penalty·turns + soft cable-proximity cost`), node boxes as hard obstacles, neighbouring cables as soft obstacles, and rounded corners. Registered after `router`.
  - New `sugiyama` arrange algorithm (`patchcanvas/arrange_sugiyama.py`): classic layered layout — cycle breaking, longest-path layering, barycenter crossing reduction (down/up sweeps), even column placement. It appears in the Arrange Tools "Auto arrange" submenu automatically via the arrange registry.
  - Settings "Line style" combo picks up `orthogonal` with no extra code.

### 2026-10-15 11:15:00
- **refactor(canvas)**: Pluggable arrange algorithms, self-contained router plugin, router fix
  - New `patchcanvas/arrangealgos.py` registry mirroring `linealgos.py`: a `LayoutAlgorithm` interface (`arrange(nodes)`), `register_layout_algorithm`/`get_layout_algorithm`/`layout_algorithms`/`resolve_layout_algorithm`. Two built-ins: `classic` (the original signal-flow `autoArrange()`, still used by the context menus) and `flow` (the newer columnar, selection-aware layout; the default). `patchcanvas.autoArrangeNodes(nodes, algorithm=None)` now dispatches through the registry.
  - Arrange choice is selectable from the **Arrange Tools** popover ("Auto arrange" submenu) and persisted as `Canvas/ArrangeStyle` (`CARLA_KEY_CANVAS_ARRANGE_STYLE`, read in `carla_host`, stored on the Python-side `options_t.arrange_style`).
  - The `router` A* + flocking implementation moved out of the shared `patchcanvas/routing/` package into a single self-contained plugin module `patchcanvas/linealgo_router.py` (grid + A* + string-pulling + flocking + `RouterLineAlgorithm`). It still consumes only the public `LineContext` API; the `routing/` package was removed.
- **fix(canvas)**: Smart router no longer draws straight through node boxes
  - The A* search produced a correct detour, but flocking relaxation then pulled the waypoints back through the obstacle (the unit test was too lenient). Relaxation now (a) only applies the smoothing force when both neighbours can see each other (line-of-sight via the occupancy grid), (b) hard-projects any waypoint out of an inflated node box, and (c) validates the final polyline and falls back to the raw A* path if it ever tunnels. Added a real-`QGraphicsScene` integration test asserting no waypoint or segment enters an inflated node rect.

### 2026-10-15 10:30:00
- **feat(canvas)**: Obstacle-aware routing API (A* + flocking) and smart arrange/wire tools
  - New `patchcanvas/routing/` package: `grid.py` (scene-space occupancy grid), `astar.py` (A* search + string-pulling simplify), `flock.py` (force-based waypoint relaxation for cable spacing), and a single public entry point `plan_waypoints(ctx, ...)`. It consumes only a `LineContext` (endpoints, `nodes()`, `siblings()`), never patchcanvas internals.
  - Registered a new `router` line algorithm (`Smart router (A* + flocking)`): routes cables around node boxes and spaces them from sibling cables, falling back to bézier on failure. Not the default; `bezier` remains default.
  - New public canvas API (exported from `patchcanvas`): `autoArrangeNodes()`, `autoWire()`, `autoArrangeAndWire()`, `autoRepelNodes()`. Arrange uses signal-flow column layering; wire chains nodes in topological order using compatible free ports and requests connections through the normal canvas callback; repel falls back to the whole canvas when nothing is selected.
  - Canvas context toolbar now exposes a grouped **Arrange Tools** popover (auto arrange / auto wire / arrange + wire / auto repel), replacing the separate arrange/repel buttons so the bar stays uncluttered. Wire/both are disabled with no selection.

### 2026-10-15 09:05:00
- **refactor(canvas)**: Retire adaptive, default to bézier
  - `adaptive` hybrid dispatcher removed from the registry; `bezier` is the default again (`CARLA_DEFAULT_CANVAS_LINE_STYLE`, `patchcanvas.options.line_style`). A future A* + flocking router will replace it.

### 2026-10-15 08:40:00
- **fix(canvas)**: Line styles collapsed to straight; tune adaptive hybrid
  - Every non-`bezier` style rendered as a straight line: the settings dialog writes the legacy `Canvas/UseBezierLines` flag as `False` for any non-bezier pick, and `resolve_line_algorithm()` treated that as "force straight". The `line_style` string is now authoritative and the legacy boolean is ignored (`linealgos.py`, `patchcanvas/__init__.py`).

### 2026-10-15 08:20:00
- **feat(canvas)**: New cable shapes + adaptive hybrid routing
  - Added a registered `circuit` line algorithm (H/V trace with rounded corners and sibling-based lane offsets).
  - Renderer flags renamed/clarified: `dynamic` (re-route all cables on node moves; `tracks_others` kept as a read alias) and `selection_sensitive` (re-route on selection change, coalesced per event-loop tick). Dynamic re-routes are coalesced in `CanvasBox.repaintLines` to at most once per event-loop tick.
  - New geometry helper `rounded_polyline` used by the circuit shape.

### 2026-10-15 07:05:00
- **refactor(canvas)**: Pluggable line-algorithm registry for patchbay cables
  - Connection shape logic was spread across `if/elif` chains in `canvasline.py`, the drag previews (`canvaslinemov.py` / `canvasbezierlinemov.py`), and the settings combo. New `patchcanvas/linealgos.py` introduces a `LineAlgorithm` interface (`build_path` / `build_drag_path`, plus `line_type`, `mov_line_type`, `cap_style`) with a registry (`register_line_algorithm`, `get_line_algorithm`, `line_algorithms`).
  - Algorithms receive a `LineContext` (endpoints + `direction` + the ports/connection/`canvas`), not bare points, so complex renderers are possible: `ctx.siblings()` yields every other cable for coupling/bundling, `ctx.nodes()` yields `(group_id, QRectF)` for node-avoidance routing, and `paint(painter, ctx, path)` plus `params()` are optional hooks. Setting `dynamic = True` makes the canvas re-route all cables on node moves so bundles stay in sync.
  - `BezierLineAlgorithm`, `StraightLineAlgorithm`, and `SteppedLineAlgorithm` are registered out of the box; adding a new shape is one class + `@register_line_algorithm` with zero branching changes elsewhere.
  - Drag previews are now a single registry-driven `CanvasLineMov`, so `stepped` gets a live preview too (previously only bezier/straight). Old `CanvasBezierLine` / `CanvasBezierLineMov` names remain as backward-compatible aliases.
  - The settings "Line style" combo is populated from the registry instead of a hardcoded list (`carla_settings.py`).

### 2026-10-15 06:11:30
- **fix(ui)**: Restore `Qt.Key_Backspace` (Qt6 compat)
  - `qt_compat` aliased most `Qt.Key_*` names to their Qt6 `Qt.Key.*` enum for bindings compatibility, but `Key_Backspace` was missing, so deleting a plugin with Backspace crashed with `AttributeError: type object 'Qt' has no attribute 'Key_Backspace'` (`carla_skin.py:1656`). Added the alias.

### 2026-10-15 06:02:45
- **chore(ui)**: Log the active patchbay viewport at startup
  - The canvas startup now logs whether the patchbay is `OpenGL` or `Software raster`, the viewport update mode, and the `Canvas/UseOpenGL` setting, so it is obvious from the terminal whether GPU rendering is actually active.

### 2026-10-15 05:41:20
- **perf(ui)**: Smoother canvas panning and further drag/repaint savings
  - Box drop-shadows are now also skipped while panning the canvas (not just during a node drag), so the strips exposed by scrolling are cheap to redraw.
  - The canvas view no longer adjusts update rects for antialiasing (`DontAdjustForAntialiasing`) and the viewport is marked opaque (`WA_OpaquePaintEvent`), keeping repaints smaller and skipping Qt's background erase.
  - The grid dots are now drawn in a single `drawPoints` call with a round-capped pen instead of thousands of individual `drawRect` calls.
  - The minimap no longer draws the canvas grid while rendering the scene to its cache (invisible at that scale), making minimap refreshes noticeably cheaper.

### 2026-10-15 05:26:10
- **fix(ui)**: Ask about Ctrl+C in the terminal, not with a GUI dialog
  - Pressing Ctrl+C now prints a plain prompt (`[K]ill` / `[T]ray + detach`) in the terminal where the key was pressed, instead of popping a `QMessageBox`.
  - Fixed the previous implementation crashing: `QMessageBox.YesRole`/`NoRole` don't exist on the class in this Qt build, and the failure fallback called `logger.warning()` with a single argument (the logger requires a tag plus message), so the prompt died with an `AttributeError`/`TypeError`.
  - The prompt is shown whenever Carla runs from a TTY; the tray/detach option is only offered when a system tray is available.

### 2026-10-15 05:24:03
- **perf(ui)**: Smoother patchbay node dragging
  - Box drop-shadows no longer recompute their blur on every drag frame: while a box is being dragged the shadow is skipped (the box is painted directly) and restored on release, removing the main source of drag lag.
  - Position changes are no longer written to settings and pushed to the engine on every drag frame; they are flushed once when the drag ends, avoiding a synchronous settings write plus engine callback per frame.
  - The grid background is now cached by the canvas view (`CacheBackground`) and painter state is not saved (`DontSavePainterState`), so the dotted grid is not repainted for every dot on each drag/pan frame.

### 2026-10-15 05:01:41
- **feat(ui)**: Prompt on Ctrl+C (SIGINT) instead of quitting immediately
  - SIGINT is now routed separately from SIGTERM: SIGTERM still closes immediately (needed by session managers/systemd), while SIGINT pops a dialog.
  - Dialog offers "Kill Carla" (default, `Y`/Enter) or "Tray + Detach" (default-less `N`), the latter minimising to the system tray and detaching from the controlling terminal (`setsid`, `SIGHUP` ignored, stdio redirected) so the app survives the terminal closing.
  - Only prompts when launched from a TTY with a system tray available; otherwise it closes as before.

### 2026-10-15 04:52:16
- **feat(ui)**: Edge auto-scroll when dragging the minimap view scope
  - Left-dragging the view scope to (or beyond) a minimap edge now continuously pans the minimap and the main patchbay canvas, ramping speed with how far past the edge the cursor is.
  - Auto-scroll stops automatically when the cursor returns inside the map or the view reaches the edge of the node bounds.

### 2026-10-15 04:46:41
- **fix(ui)**: Minimap phantom node, bottom-scope clamping and collapse button
  - Phantom node: hidden / not-yet-portable group boxes (created at `(0,0)`) were being outlined because `scene.items()` includes invisible items; the minimap and scene-rect expansion now skip invisible items.
  - View scope could not be panned to the bottom until manually scrolling: scene/view rect expansion only ran once at setup (before plugins loaded). It now also runs from `updateMiniCanvasLater()` (client add/remove/rename) and updates both the scene and the view scene rect.
  - Collapse button did nothing: `QToolButton.clicked` passes a bool check-state into `toggleCollapsed(collapsed)`, making every click evaluate as "no change"; the connection is now wrapped so it toggles.

### 2026-10-15 04:31:06
- **feat(ui)**: Blender-style minimap overlay, discoverability and persistence
  - Replaced the top `✕` bar with a compact grip (drag to move) and a corner collapse tab; hide/expand and zoom-reset moved into a right-click context menu.
  - Added a zoom-level badge (`FIT` / percentage) and an on-map control hint so wheel-zoom, middle-drag pan and double-click reset are discoverable.
  - Minimap now expands the patchbay scene rect to the union of node bounds (+margin) so the bottom of the canvas can actually be panned to at startup.
  - Reduced early misplacement: placement now waits for valid geometry and re-clamps via deferred repositioning.
  - Persisted `Minimap/X`, `Minimap/Y`, `Minimap/Zoom`, `Minimap/Collapsed` and `Minimap/Visible` in `QSafeSettings` (app-wide), restored at startup and saved on drag/collapse/zoom/hide and on settings save.

### 2026-10-15 04:14:49
- **fix(ui)**: Render modern minimap from the live scene with contrast-corrected node outlines
  - Replaced the hand-drawn bounding-box fill with a real `QGraphicsScene` render, matching the classic minimap so node bodies, headers, ports and cables keep their true appearance.
  - Outlined every node using its own custom color (theme color when uncolored), passing it through a WCAG luminance/contrast check that lightens or darkens the color against the background so all nodes stay visible.
  - Added minimap-internal zoom (mouse wheel, cursor-anchored), middle-drag panning, and double-click reset so large patches stay readable.

### 2026-10-15 03:09:23
- **feat(ui)**: Float minimap into hideable patchbay viewport overlay
  - Reparented `miniCanvasPreview` out of the side dock into a rounded overlay anchored at the bottom-right of the patchbay viewport.
  - Placement is mode-aware: Modern UI mode uses the floating overlay, while Classic mode restores the original sidebar minimap.
  - Added hide (`✕`) and restore (`Map`) controls so the minimap can be dismissed and brought back on demand.
  - Kept existing canvas navigation and theming behavior intact while repositioning on viewport resize.

### 2026-10-15 00:00:00
- **feat(ui)**: Add "Minimize to system tray" option
  - Added `Main/MinimizeToTray` setting (default off) in Settings with load/save/reset.
  - Main window minimizes to a system tray icon with Show/Quit menu and restores on activation.

## [0.1.5] - 2026-10-13

### 2026-10-13 23:05:00
- **fix(ci)**: Purge ccache from packaging pipeline and fix canvas icon warning
  - Completely removed `ccache` from packaging workflow jobs to prevent caching older Qt6 symbol ABIs (`_ZN8QVariantC1EO7QString`).
  - Switched canvas side-by-side view icon fallback cleanly to `view-refresh` to prevent `Cannot open file ':/16x16/view-split-top-bottom.svgz'` Qt warnings.
  - Bumped version to `0.1.5`.

## [0.1.4] - 2026-10-13

### 2026-10-13 22:10:00
- **fix(packaging)**: Fix Arch Linux Qt6 ABI crash and invalidate stale CI cache
  - Resolved `undefined symbol: _ZN8QVariantC1EO7QString` crash on Arch Linux by scoping CI `ccache` cache key to `ccache-v2-` and ensuring clean build targets.
  - Standardized application window title, logs dialog (`Clara Logs`), and About dialog window title to **Clara**.
  - Fixed missing SVG icon warning for canvas side-by-side view toggle.
  - Bumped `CLARA_VERSION_STRING`, `releases.json`, and AUR `clara-bin` PKGBUILD to `0.1.4`.

### 2026-10-13 21:42:00
- **feat(ui)**: Add timed support banner & purge all emoji from banners and dialogs
  - Added `SupportNotificationBanner` scheduled via a 10-minute timer (`QTimer.singleShot(600000)`) with sponsor links for maintainers (`acropolis914` and `falkTX` from `.github/FUNDING.yml`: GitHub Sponsors, Patreon, Liberapay, PayPal).
  - Added "Support Clara..." menu action in Help menu and hidden CLI flag `--show-support-banner` to display banner immediately for verification.
  - Provided snooze actions: "Hide for 1 Month" (persisted for 30 days via `QSettings`) and "Never Show Again".
  - Cleaned all banner and dialog buttons/headers to be strictly emoji-free.

### 2026-10-13 21:33:00
- **feat(updates)**: Add interactive terminal updater and Open Releases Page action
  - Created embedded `scripts/clara_self_updater.sh` featuring automatic distro family detection (`/etc/os-release`), fallback interactive picker, ANSI styling, and `pkexec`/`sudo` elevation.
  - Replaced banner download button with **⚡ Update Now** (auto-detects and launches terminal emulator) and **🌐 Releases Page**.
  - Configured `Makefile` to install `clara_self_updater.sh` into `$(DATADIR)/carla/scripts/` across all distribution packages.
  - Terminates updates with `Installed. Press enter to exit, please restart Clara`.

### 2026-10-13 21:19:00
- **fix(updates)**: Verify compiled distro binaries exist before prompting update
  - Added GitHub Releases API check in `UpdateCheckThread` to explicitly verify that compiled packages (`.deb`, `.rpm`, `.tar.zst`) have finished uploading, ignoring default auto-generated source zips.
  - In manual checks while packages are building, notifies the user that the release is currently compiling.


### 2026-10-13 21:12:00

- **ci(packaging)**: Standardize release artifact filenames to use release tag version
  - Replaced commit SHA hashes (`${{ github.sha }}`) with release tag versions (`${VERSION}`) across all distro packages (`clara-archlinux-${VERSION}.tar.zst`, `clara-ubuntu-${VERSION}.deb`, etc.).
  - Resolves broken download URLs in AUR `clara-bin` PKGBUILD.

### 2026-10-13 21:07:00

- **docs(sponsors)**: Prioritize acropolis914 GitHub Sponsors in funding & README
  - Added direct GitHub Sponsors badge (`https://github.com/sponsors/acropolis914`) to the `README.md` header.
  - Linked GitHub Sponsors alongside PayPal in the top announcement alert banner.

### 2026-10-13 20:46:00

- **feat(updates)**: Separate Clara and Carla versioning & add manual update checks
  - Introduced `CLARA_VERSION_STRING` ("0.1.2") in `carla_shared.py` to prevent version comparison conflicts with upstream Carla `2.6.0-alpha1`.
  - Added "Check for Updates..." to the Help menu and toolbar menu with immediate feedback dialogs (up-to-date confirmation and error diagnostics).
  - Enhanced update notification banner to slide into the top layout on update detection and display changelog modal dialog on critical or suggested releases.
  - Updated About dialog to distinguish Clara application version from underlying Carla core engine version and added a direct link to GitHub Releases.

### 2026-10-13 20:40:00
- **docs(funding)**: Add upstream creator falkTX funding channels to FUNDING.yml
  - Included falkTX's GitHub Sponsors, Patreon, Liberapay, and PayPal alongside Clara maintainer sponsorship links.

### 2026-10-13 20:16:00

- **feat(ui)**: Add animated loading dialog and modernize About screen
  - Introduced modal `ProjectLoadingDialog` with an indeterminate marquee progress bar and real-time detailed status text pumped via engine event callbacks for project restoration.
  - Revamped About screen: removed legacy bitmap logos and outdated fonts, attributed project maintenance to `acropolis914`, and added direct links to the Clara repository and GitHub Sponsor page.

### 2026-10-13 20:03:00
- **refactor(patchbay)**: Make camera autofocus pan-only and faster
  - Removed zoom scaling in `animateFocusOn` to provide pure, crisp pan travel and shortened duration to 260ms for snappy response.

### 2026-10-13 20:00:00
- **refactor(ui)**: Smooth patchbay camera animation and restyle floating add button
  - Replaced matrix reset scaling with incremental scaling in `animateFocusOn` to eliminate camera anchor jitter during flight.
  - Redesigned floating `+ Add Plugin` button to use cohesive dark glassmorphism palette matching Carla's Catppuccin theme.

### 2026-10-13 19:58:00
- **fix(rack)**: Resolve context menu remove and move action dispatch
  - Fixed erroneous `elif actMoveUp:` check that swallowed subsequent menu actions, restoring the context menu `Remove` confirmation and execution.

### 2026-10-13 19:56:00
- **fix(rack)**: Ensure delete confirmation dialog triggers reliably and add floating add button
  - Added keypress interception for `Delete`/`Backspace` directly on rack slot widgets with parent window anchoring for the confirmation dialog.
  - Added a floating `＋ Add Plugin` action button anchored to the bottom-right corner of the rack list view.

### 2026-10-13 19:51:00
- **feat(patchbay)**: Animate node autofocus with cubic bezier easing and zoom dip
  - Implemented `animateFocusOn()` in `DraggableGraphicsView` featuring `QEasingCurve.InOutCubic` camera travel and a subtle mid-flight zoom-out/zoom-in parabolic arc on rack item selection and patchbay search.

### 2026-10-13 19:44:00
- **feat(patchbay)**: Add configurable minimum node width
  - Introduced `Canvas/NodeMinWidth` setting with slider control in the Canvas settings tab, dynamic options propagation, and CanvasBox width enforcement (default 160px).

### 2026-10-13 19:34:00
- **feat(rack)**: Enforce uniform fixed grid dimensions for parameter dials in minimal skin
  - Configured `setFixedSize(68, 54)` and aligned flow layout spacing on `w_knobs_left` so rack dials arrange into a uniform grid with unclipped labels.

### 2026-10-13 19:27:00
- **fix(rack)**: Ensure header buttons, badge, and title anchor to the far left
  - Cleared fixed template spacers and inserted action buttons (index 0), type badge (index 1), and title (index 2) at the start of `layout_top`.

### 2026-10-13 19:24:00
- **feat(patchbay)**: Trigger zoom to fit after applying deferred hidden ports on load
  - Added `canvas.scene.zoom_fit()` after hiding unconnected ports on session loading to frame all graph nodes neatly.

### 2026-10-13 19:22:00
- **fix(ui)**: Add `Qt.TextElideMode` compatibility aliases in `qt_compat.py`
  - Added `Qt.ElideRight`, `Qt.ElideLeft`, and `Qt.ElideMiddle` aliases for PyQt6, resolving AttributeError during dynamic title elision in `resizeEvent`.

### 2026-10-13 19:20:00
- **fix(rack)**: Prevent access to replaced layout in `PluginSlot_Minimal`
  - Replaced stale reference to `self.ui.horizontalLayout_3` with safe check on `self.w_knobs_left.layout()`, resolving RuntimeError on plugin instantiation.

### 2026-10-13 19:19:00
- **fix(ui)**: Export and import `QSpacerItem` across Qt5/Qt6 compatibility layer
  - Added `QSpacerItem` to `qt_compat.py` QtWidgets exports and imported it into `carla_skin.py`, fixing plugin slot initialization failure.

### 2026-10-13 19:13:00
- **fix(frontend)**: Resolve About Dialog `unwrapinstance` crash under PyQt6
  - Added support for `PyQt6.sip.unwrapinstance` in `carla_frontend.py` to prevent TypeError on `HostWindow`.
- **feat(rack)**: Dynamic title elision on resize and distributed grid width for knobs
  - Switched title truncation to responsive font-metrics elision that only truncates when space is constrained.
  - Standardized dial columns to a distributed 68px grid width to maintain aligned parameter rows without label clipping.

### 2026-10-13 19:11:00
- **docs(readme)**: Add student developer donation note to top banner
  - Added personal student funding note with direct PayPal link to README announcement banner.

### 2026-10-13 18:43:00

- **docs(funding)**: Add GitHub FUNDING.yml configuration
  - Created `.github/FUNDING.yml` to display repository sponsorship button and funding links.

### 2026-10-13 18:42:00

- **docs(readme)**: Clarify AI policy and make alpha announcement imperative
  - Rephrased top callout banner in `README.md` to be directly imperative about bug reporting and contributing.
  - Removed "encouraged" phrasing from AI development policy in `README.md` and `CONTRIBUTING.md`, designating AI tools as strictly permitted under full contributor review.

### 2026-10-13 18:41:00

- **feat(rack)**: Restructure header into flex layout and modernize preset selector
  - Reordered header into `<buttons> <type badge> <title> <auto-expanding spacer> <right modules>` with tightened spacing.
  - Limited title length to 20 characters with ellipsis while preserving the full name in tooltip.
  - Modernized `cb_presets` with a translucent pill surface, subtle border, custom drop indicator, and themed popup menu.

### 2026-10-13 18:35:00
- **fix(ui)**: Resolve missing `QRadialGradient` import in `LEDButton`
  - Cleaned up unused gradient import in `widgets/ledbutton.py` to restore clean frontend launch.

### 2026-10-13 18:34:00
- **feat(ui)**: Reskin 2x2 LED status indicators for modernized header slice
  - Added clean geometric vector rendering with vivid glow and distinct dark states in `LEDButton`, activated exclusively when Modernized Header Slice is enabled.

### 2026-10-13 18:28:00
- **fix(ui)**: Register Qt resource bundle into PyQt6 runtime
  - Fixed missing button pixmaps and icons across classic and modern rack skins by registering `resources_rc` data into `PyQt6.QtCore.qRegisterResourceData`.

### 2026-10-13 18:21:00
- **feat(rack)**: Calibrate smooth scroll easing rate for gentle visual glide
  - Softened easing rate from 28% to 10% per frame and added a 24px/tick velocity limit in `RackListWidget`.

### 2026-10-13 18:06:00
- **feat(rack)**: Smooth scroll rack item into view when clicking corresponding node in patchbay
  - Added `scrollToItemSmooth` to `RackListWidget` with viewport centering and easing interpolation.
  - Linked `slot_canvasPluginSelected` to call `scrollToItemSmooth`, smoothly bringing the plugin slot into focus.

### 2026-10-13 18:03:00
- **fix(patchbay)**: Fix connected port detection when hiding unused ports
  - `CanvasBox.updatePositions` now inspects both global `canvas.connection_list` and node-local `m_connection_lines` to ensure all active wires (including split and re-routed node ports) are recognized as connected.

### 2026-10-13 18:00:00
- **fix(patchbay)**: Resolve cable disconnect misalignment with hidden unconnected ports and reorder Settings menu
  - Connected and re-connected ports now trigger immediate box recalculation (`updatePositions`) on nodes with hidden unconnected ports active, and deferred hiding re-syncs all cable geometries after backend connections finalize.
  - Reorganized Settings menu with panels/toggles grouped first, followed by standalone logs, and `Configure Carla...` placed cleanly at the bottom.

### 2026-10-13 17:41:00
- **feat(rack)**: Implement smooth pixel-based scrolling in Rack list
  - Configured `RackListWidget` with pixel scrolling mode (`ScrollPerPixel`) instead of discrete item stepping.
  - Implemented an animated easing timer (`_on_smooth_scroll_tick`) with fractional interpolation for fluid mouse-wheel navigation through plugin strips.

### 2026-10-13 17:35:00
- **fix(ui)**: Unified flush look for Modern Patchbay+Rack workspace and functional Statusbar toggle
  - Removed container borders, frame shapes, and pane outlines between Rack and Patchbay in Modern side-by-side mode for a continuous flush aesthetic matching the canvas theme.
  - Implemented `Show Statusbar` toggle in Settings and menus, connecting directly to the bottom engine statusbar (`tw_statusbar`) displaying buffer size, sample rate, and DSP load.

### 2026-10-13 17:28:00
- **feat(ui)**: Modern / Classic UI mode switch, unified workspace, and native error loading dialog
  - Refactored `ProjectLoadSummaryDialog` to use system Qt theme styling and native controls without hardcoded color themes.
  - Introduced `Modern UI Mode` toggle in Settings (defaulting to enabled), unbarring Patchbay + Rack into a unified single workspace without tab bar clutter.
  - Decoupled Logs tab into a standalone window via `Show Logs Window` action when in Modern unified view mode, while preserving Classic multi-tab view mode on toggle.

### 2026-10-13 17:11:00
- **feat(ui)**: Default to side-by-side view, no toolbar, and floating menu button when menubar is hidden
  - Added hamburger menu button directly on the floating patchbay toolbar overlay so main menus remain accessible when top menubar and toolbar are both hidden.
  - Set application defaults in `loadSettings`: side-by-side view enabled by default, main toolbar hidden by default, and menubar hidden by default.
  - Safeguarded `gCarla.gui` access in `canvasCallback` during application teardown.

### 2026-10-13 17:10:00
- **tools(aur)**: Add local release and AUR publishing helper script
  - Created `scripts/release_and_push_aur.sh` to update `releases.json`, bump `aur/clara-bin/PKGBUILD`, push the version tag to GitHub, generate `.SRCINFO`, and push directly to `ssh://aur@aur.archlinux.org/clara-bin.git`.

### 2026-10-13 17:05:00

- **packaging(aur)**: Add clara-bin PKGBUILD and automated version bump step
  - Created `aur/clara-bin/PKGBUILD` packaging the pre-compiled GitHub release archive for Arch Linux users without build overhead.
  - Added automated GitHub Actions step in `.github/workflows/package.yml` to bump `pkgver` in `aur/clara-bin/PKGBUILD` and push to main upon tag releases.
  - Updated `installation.md` and `README.md` to document `clara-bin` and `clara-git` options.

### 2026-10-13 16:57:00

- **fix(backend)**: Add system library fallbacks for carla-bridge-native
  - Added fallback search in `/usr/lib/carla` and `/usr/lib64/carla` when `carla-bridge-native` is not present in the local `bin/` folder.
  - Prevents fatal crashes when in-process JUCE plugins (`KV-Element`) require bridge isolation.

### 2026-10-13 16:47:00
- **fix(frontend)**: Resolve missing LEVEL_NAMES, QLabel, and os imports in ProjectLoadSummaryDialog
  - Imported `LEVEL_NAMES` in `carla_host.py` from `carla_logger`.
  - Added missing `QLabel`, `QPushButton`, `QTextEdit`, `QHBoxLayout`, and `os` imports in `carla_widgets.py`.

### 2026-10-13 16:43:00
- **feat(project)**: Add post-load summary dialog with skipped plugins and one-click log copy
  - Wrapped `load_project()` in try-catch and error callback monitoring to prevent aborted sessions when individual plugins fail.
  - Implemented `ProjectLoadSummaryDialog` in `carla_widgets.py` showing failed/skipped items, raw diagnostic logs, and a "Copy Log to Clipboard" button.

### 2026-10-13 16:40:00
- **docs(issues)**: Add GitHub issue template config.yml
  - Configured `.github/ISSUE_TEMPLATE/config.yml` disabling unstructured blank issues.
  - Linked GitHub Discussions and upstream documentation directly in the issue chooser.

### 2026-10-13 16:24:00

- **fix(patchcanvas)**: Implement and export centerGraphInCanvas for project canvas positioning
  - Implemented `centerGraphInCanvas()` in `source/frontend/patchcanvas/patchcanvas.py` filtering out None widgets and centering graph nodes when loading projects.
  - Exported `centerGraphInCanvas` in `source/frontend/patchcanvas/__init__.py`.

### 2026-10-13 08:04:00
- **fix(frontend)**: Fix _on_update_available method placement inside HostWindow class
  - Relocated `_on_update_available` callback inside the `HostWindow` class scope so Qt signal connection resolves correctly.

### 2026-10-13 08:00:00
- **fix(build)**: Prioritize Qt6 over Qt5 when pyuic6 is present
  - Swapped Qt5/Qt6 detection ordering in `source/Makefile.deps.mk` so `pyuic6` is selected when building with `DEFAULT_QT=6`, resolving PyQt5/PyQt6 widget mismatch exceptions.

### 2026-10-13 07:52:00
- **fix(frontend)**: Export QThread, QTextEdit, and QSettings in qt_compat and fix version import
  - Exported `QThread`, `QTextEdit`, and `QSettings` across Qt5 and Qt6 sections of `qt_compat.py`.
  - Updated `update_checker.py` to import `CARLA_VERSION_STRING` from `carla_shared`.
  - Ensured `PKGBUILD` passes `DEFAULT_QT=6` during install stage.

### 2026-10-13 15:39:00
- **ci(workflow)**: Restrict multi-distro packaging workflow strictly to tag pushes
  - Removed standard `main` branch push and weekly cron triggers from `.github/workflows/package.yml`.
  - Configured packaging pipeline to trigger exclusively on version tags (`v*`) and manual `workflow_dispatch`.

### 2026-10-13 15:35:00

- **docs(suggestions)**: Add SUGGESTIONS.md and feature request issue template
  - Added `SUGGESTIONS.md` outlining GitHub Discussions channels and proposal guidelines.
  - Added `.github/ISSUE_TEMPLATE/feature_request.md` for structured feature requests.
  - Linked Ideas & Suggestions into the primary `README.md` navigation bar.

### 2026-10-13 07:34:00

- **feat(desktop)**: Add clara.desktop entry and clara binary symlink
  - Added `data/desktop/clara.desktop` system application launcher.
  - Added `clara` binary symlink in `` pointing to `carla` for direct command-line launch.

### 2026-10-13 15:33:00
- **docs(readme)**: Modernize README, add CONTRIBUTING guide, and GitHub issue template
  - Removed raw emoji clutter from README.md in favor of Catppuccin badges and clean typography.
  - Added early-alpha contributor and bug-reporting callout banner.
  - Added `CONTRIBUTING.md` detailing setup, Conventional Commits, and explicit AI disclosure requirements.
  - Added `.github/ISSUE_TEMPLATE/bug_report.md` for structured bug reporting.

### 2026-10-13 07:30:00

- **feat(updates)**: Add non-blocking background update checker and dismissable top notification banner
  - Added structured `releases.json` with urgency levels (`suggested`, `minor`, `critical`), changelogs, and installation instructions.
  - Implemented `UpdateCheckThread` and `UpdateNotificationBanner` in `update_checker.py` with non-blocking 3s timeout.
  - Added "Hide" and "Skip Version" actions with confirmation dialog and `QSettings` persistence.
  - Updated `AGENTS.md` guidelines to mandate updating `releases.json` alongside `CHANGELOG.md`.
  - Added `clara-bin` AUR packaging task to `TODO.md`.

### 2026-10-13 06:58:00
- **fix(fedora)**: Disable RPM debuginfo package generation
  - Added `%global debug_package %{nil}` to `clara.spec` to prevent rpmbuild from failing on empty debugsource lists.

### 2026-10-13 06:49:00
- **fix(fedora)**: Package all installed files under /usr/* in RPM spec
  - Simplified `%files` in `clara.spec` to include `/usr/*`, resolving missing lib64 path errors and invalid `%optional` spec macro directives.

### 2026-10-13 06:42:00
- **fix(fedora)**: Package pre-compiled binaries directly into RPM without redundant recompilation
  - Updated `clara.spec` and packaging step to use `rpmbuild -bb` on the already-compiled tree, eliminating redundant build failures and slashing package creation time to seconds.

### 2026-10-13 06:18:00
- **fix(nix)**: Fix SDL2 casing in Nix derivation and strictly verify build result
  - Corrected `sdl2` to `SDL2` in `nix/default.nix` to resolve nixpkgs evaluation error.
  - Required valid `./result` derivation path before creating Nix tarball artifact.

### 2026-10-13 06:15:00
- **fix(fedora)**: Correct SMP make flags syntax in RPM spec
  - Fixed duplicate `-j` flag by using standard `%{?_smp_mflags}` macro in `clara.spec` to avoid make argument errors.

### 2026-10-13 06:09:00
- **ci(matrix)**: Enable fail-fast to immediately abort entire build on any distro failure
  - Changed `fail-fast: true` on the packaging matrix.

### 2026-10-13 06:08:00
- **fix(fedora)**: Replace %make_build macro with direct make invocation
  - Switched from Fedora `%make_build` macro to `make -j%{_smp_mflags} DEFAULT_QT=6` in `clara.spec` to prevent strict Red Hat compiler hardening flags from breaking bundled C dependencies (lilv/serd).

### 2026-10-13 06:00:00
- **perf(ci)**: Accelerate CI compilation with parallel make and ccache caching
  - Enabled `make -j$(nproc)` to utilize all 4 runner CPU cores concurrently.
  - Configured `actions/cache@v4` with `ccache` across distros to reuse compiled object files across builds.

### 2026-10-13 05:56:00
- **fix(fedora)**: Add python3-devel to build dependencies
  - Added missing `python3-devel` package to Fedora DNF installation to satisfy RPM build dependencies.

### 2026-10-13 05:49:00
- **fix(rpm)**: Fix RPM spec release tag token syntax and align source archive name
  - Changed `Release` in `clara.spec` to standard `1%{?dist}` to avoid unexpanded GitHub Actions expression syntax errors in rpmbuild.
  - Aligned Fedora source archive filename with `clara-source.tar.gz`.
  - Updated README to point download links directly to release tags.

### 2026-10-13 05:47:00
- **ci(release)**: Add automated GitHub Releases on tag push with changelog extraction
  - Configured `release` job triggered exclusively on `v*` tag pushes to attach all distro package artifacts.
  - Automatically extracts latest changelog notes from `CHANGELOG.md` into the GitHub Release body.
  - Added installation & download table in `README.md` covering all supported distributions.

### 2026-10-13 05:41:00
- **ci(void)**: Isolate void-musl build to host docker container
  - Migrated `void-musl` build to a host runner job using `docker run` to prevent musl dynamic-linking incompatibilities with GitHub Actions Node.js runner.

### 2026-10-13 05:36:00
- **fix(ci)**: Fix POSIX sh pipefail compatibility and container spec path
  - Removed unsupported `set -o pipefail` from Alpine/Void `/bin/sh` build scripts.
  - Corrected Fedora RPM spec lookup to use relative `.github/workflows/specs/clara.spec` inside the container workspace.

### 2026-10-13 05:32:00
- **feat(nix)**: Add Nix derivation, devShell, and Flake configuration
  - Added `nix/default.nix` for packaging Clara using `stdenv.mkDerivation` and Qt6 build hooks.
  - Added `nix/shell.nix` for developer environment and debugging tooling.
  - Added root `flake.nix` with default package, app runner, and devShell outputs.
  - Updated CI Nix workflow to invoke `nix build` with Flakes enabled.

### 2026-10-13 05:25:00
- **ci(packaging)**: Add void-musl build, fix deb/rpm/arch artifact packaging, and isolate Nix to host runner
  - Split Void Linux packaging into `void-glibc` and `void-musl` with musl-fts support.
  - Isolated Nix into a dedicated host runner job using `DeterminateSystems/nix-installer-action` to resolve container Node execution failures.
  - Corrected Debian packaging via `dpkg-deb` and Fedora RPM spec install rules using `make install`.
  - Added Arch Linux zstd tarball packaging target.

### 2026-10-13 05:03:00
- **fix(ui)**: Fix Ctrl+M menubar double-press requirement and infinite canvas panning on right edge
  - Moved `act_settings_show_menubar` and hamburger button setup before `loadSettings(True)` so that restored menubar visibility state immediately syncs with the action state, eliminating the initial double-press bug.
  - Enhanced canvas empty-area hit testing to check `topLevelItem()` to avoid false negatives on child elements.
  - Implemented dynamic scene boundary expansion during panning in `DraggableGraphicsView` so panning smoothly continues across infinite canvas coordinates without hitting scrollbar clamp limits on the right or bottom.
- **feat(settings)**: Refine settings sidebar typography, dimensions, and outline removal
  - Compacted tab row heights to 32px and trimmed sidebar width to 136px.
  - Replaced monospace font with modern system sans-serif font stack (`-apple-system`, `Inter`, `Roboto`, `Segoe UI`).
  - Removed table item outlines and softened border separators with translucent Catppuccin surface styling.
  - Polished button and group box outlines with clean rounded corners and unified accent highlights.

### 2026-10-13 04:10:00
- **fix(settings)**: Import `QSize` and `QIcon` from `qt_compat`
  - Fixed `NameError: name 'QSize' is not defined` when initializing settings sidebar icon size.

### 2026-10-13 04:09:00
- **fix(settings)**: Import `gCarla` and modernize settings tab layout and headers
  - Fixed `NameError: name 'gCarla' is not defined` during live updates (`_on_live_rack_spacing`, `_on_live_rack_padding`, `_on_live_rack_min_width`, `_on_live_statusbar_toggle`).
  - Removed outdated tab icons and replaced with modern typography and clean tab labels in `lw_page`.
  - Hid legacy page header icons (`label_icon_*`) across all settings dialog tabs.
- **fix(settings)**: Correct parent widget for `group_rack_geometry` in `CarlaSettingsW`
  - Fixed `AttributeError: 'Ui_CarlaSettingsW' object has no attribute 'tab_main'` by referencing `page_main` and `verticalLayout_5`.

### 2026-10-13 03:56:00
- **feat(settings)**: Overhaul Settings UI with live tweakables and modern Catppuccin styling
  - Exposed live interactive sliders for rack item vertical spacing (0–16px), slot internal padding (2–16px), and minimum slot width (180–450px) that apply instantly without app restart.
  - Added a statusbar visibility toggle ("Show Statusbar at bottom") that reacts in real-time.
  - Redesigned `CarlaSettingsW` dialog styling with sleek Catppuccin Mochaccino sidebar navigation and modern form card layouts.

### 2026-10-13 03:42:00
- **feat(rack)**: Increase vertical Y-spacing margin between racklist items
  - Configured `RackListWidget.setSpacing(4)` to provide clean 4px vertical margins separating rack slots.

### 2026-10-13 03:39:00
- **feat(rack)**: Increase top and bottom vertical padding of racklist items
  - Increased `PluginSlot_Minimal` vertical contents margins from 3px to 6px (`(14, 6, 6, 6)`).
  - Adjusted slot `getFixedHeight` computation across compacted, knobs, and sliders views to comfortably accommodate the increased vertical spacing without clipping.

### 2026-10-13 03:35:00
- **feat(rack)**: Lower `RackListItem.kMinimumWidth` hard floor from 620px to 200px
  - Reduced `RackListItem.kMinimumWidth` and `RackListWidget.minimumWidth` constraint from 620px to 200px, eliminating the hard floor that prevented rack items and splitters from resizing smaller.
  - Reduced parameter name label minimum width in `SliderParamWidget` from 85px to 40px for compact slider layouts.

### 2026-10-13 03:32:00
- **fix(patchbay)**: Guard `act_canvas_side_by_side` initialization during startup `loadSettings`
  - Fixed `AttributeError: 'HostWindow' object has no attribute 'act_canvas_side_by_side'` during startup settings restoration.
  - Deferred side-by-side state loading until after canvas actions are initialized in `HostWindow.__init__`.

### 2026-10-13 03:30:00
- **feat(rack)**: Lower minimum width of rack items to 200px
  - Reduced `PluginSlot_Minimal` minimum width constraint from 260px down to 200px.
  - Allowed type badge and preset selector combo box to flexibly compress down to 44px and 50px respectively, maximizing rack compaction.

### 2026-10-13 03:26:00
- **feat(rack)**: Place minimize button to the right of the modernized meters
  - Arranged the header layout so the modernized LED and vertical peak meter slice appears before the minimize button, placing the minimize button directly to the right of the meters.

### 2026-10-13 03:25:00
- **feat(rack)**: Swap modernized meters slice and minimize button positions
  - Swapped layout positions so the minimize/collapse button sits next to the sliders/knobs toggle, and the modernized 2x2 LED / vertical peak meter slice is positioned at the far right.
  - Preserved the clean FontAwesome Nerd Font glyph icons (`\uf0c9` / `\uf1de`) for the sliders/knobs view toggle.

### 2026-10-13 03:15:00
- **feat(rack)**: Polish modernized 2x2 LEDs and rounded vertical peak meter slice
  - Fixed `LEDButton` scaling to accurately render SVGs/pixmaps within its bounded widget rectangle without overflowing or resetting custom dimensions.
  - Styled `_modern_slice_container` with a rounded pill background and subtle border, perfectly sizing the 2x2 grid and vertical peak meters without clipping.

### 2026-10-13 03:10:00
- **fix(project)**: Ensure audio engine backend initialization before startup autoload
  - Fixed startup project autoloading for `.carjp` and recent files by initializing backend engine state before dispatching project load requests.
  - Added structured `SESSION` logger diagnostics for project file conversion and backend loading.

### 2026-10-13 02:49:00
- **feat(rack)**: Modernized rack item slice with 2x2 mini LED circle grid and vertical peak meters
  - Implemented compact vertical slice housing audio/MIDI activity LEDs arranged in a 2x2 grid (8px rounded circles).
  - Configured slim vertical slice peak meters fitting within header height margins.
  - Added an Appearance context menu toggle ("Modernized Header Slice") with per-rack-slot state persistence.

### 2026-10-13 02:35:00
- **feat(ui)**: Pre-emptively hide main window on confirmed exit
  - Triggered immediate `hide()` and event flushing on closeEvent after exit confirmation to eliminate destruction lag and UI tearing during teardown.

### 2026-10-13 02:30:00
- **feat(project)**: Full Carla JSON project (`.carjp`) integration across open/save, recents, and drag-and-drop
  - Added support for `.carjp` in Recent Projects menu with automatic path preservation.
  - Enabled double-clicking `.carjp` files in the file browser tree and drag-and-drop loading into rack/canvas.
  - Updated Save/Save As dialog to respect `.carjp` file filter and automatically append the proper extension.
  - Added plugin crash pre-check and bridged execution support for JSON project files during load.
  - Registered `application/x-carla-project-json` MIME type in `data/carla.xml` and `data/desktop/carla.desktop`.

### 2026-10-13 02:18:00
- **feat(ui)**: Hideable menubar with global Ctrl+M, hamburger tool button, and toolbar context menu
  - Bound `Ctrl+M` to `HostWindow` with `Qt.WindowShortcut` context so it works globally even when the menubar is hidden.
  - Managed embedded `QWidgetAction` visibility so the "☰" hamburger menu tool button shows immediately on the toolbar when the menubar is hidden.
  - Added right-click context menu to the toolbar to easily toggle menubar and toolbar visibility.
  - Persisted `ShowMenubar`, `SideBySideEnabled`, and `SideBySideSizes` splitter ratio across application sessions.

### 2026-10-13 01:57:00
- **feat(patchbay)**: Adaptive zoom-dynamic dot grid and canvas cable line scaling
  - Replaced fixed dot spacing with an adaptive multi-tier LOD grid that scales dot frequency and radius based on zoom level.
  - Added subtle major grid reference lines at higher zoom levels for enhanced spatial orientation.
  - Made canvas cable lines scale smoothly across zoom levels with sub-pixel thickness dampening.
  - Added relative luminance contrast check for cable lines against canvas background, dynamically boosting or lowering lightness to guarantee clear contrast (>= 2.5:1).
  - Fixed `NameError: name 'QPen' is not defined` in `scene.py` and reduced dot grid opacity to a subtle background level.

### 2026-10-13 01:49:00
- **fix(patchbay)**: Implement missing single-node power and bypass action slots on context toolbar
  - Resolved `AttributeError: 'CanvasContextToolBarOverlay' object has no attribute '_slot_toggle_power'` by implementing `_slot_toggle_power` and `_slot_toggle_bypass`.
  - Added full rack plugin state sync and canvas scene update on toggle.

### 2026-10-13 01:34:00
- **feat(patchbay)**: Persist and restore hide-unused-ports state on save and serialization
  - Added dedicated `setHideUnconnectedPorts(hide)` method to `CanvasBox` with automatic port layout re-calculation and scene repaint.
  - Added multi-selection batch toggle button for hiding unconnected ports to the top context toolbar.
  - Deferred execution of the hide unconnected ports toggle in `restoreGroupPositions()` so that nodes spawn with standard initial bounds before collapsing unused ports.

### 2026-10-13 01:25:00
- **feat(patchbay)**: Move shortcuts help to toolbar tooltip and collapse overlay by default
  - Collapsed the floating cheat-sheet overlay by default to reduce visual clutter on launch.
  - Added a dedicated Help icon button (`nf-fa-question-circle`) to the left toolbar with a rich HTML tooltip displaying all patchbay and cable shortcuts on hover.


- **feat(patchbay)**: Sensible Nerd Font icon glyphs and quick color preset swatch popup menu
  - Audited and updated all toolbar glyphs across left palette and top context bar to high-readability, standardized Nerd Font icons (`mouse-pointer`, `select-drag`, `hand-paper`, `magnet`, `power-off`, `random`, `sliders`, `desktop`, `paint-brush`, `trash`, etc.).
  - Added quick popup color swatch menu for node tinting with Catppuccin presets (`Default Dark`, `Crimson`, `Synth`, `Audio`, `MIDI`, `FX`, `Dynamics`, `Teal`, `Sky`, `Flamingo`), Reset, and Custom Color Picker dialog.
  - Exported `QIcon` in `qt_compat.py` across PyQt5 and PyQt6 environments.

### 2026-10-13 01:18:00
- **feat(patchbay)**: Align toolbar icons with exact user Nerd Font FontAwesome codepoints
  - Updated all Left Palette and Top Context Toolbar buttons to the user's exact specification (`nf-fa-mouse-pointer`, `nf-fa-object-group`, `nf-fa-th`, `nf-fa-magnet`, `nf-fa-thumb-tack`, `nf-fa-check-square-o`, `nf-fa-toggle-on`, `nf-fa-cubes`, `nf-fa-pencil`, `nf-fa-trash`, `nf-fa-chain-broken`, `nf-fa-arrows-h/v`, etc.).

### 2026-10-13 01:12:00
- **feat(patchbay)**: Transform top context toolbar into compact icon-only palette with expanded actions
  - Replaced bulky text labels with sleek 26x26 square icon buttons and rich contextual tooltips.
  - Added Power (Active/Mute) and Bypass (Dry/Wet) toggles for plugins.
  - Added color picker dialogs (`QColorDialog`) for single and batch node tinting.
  - Added node properties dialog shortcut and toggle for hiding unconnected ports.
  - Added batch power, batch bypass, and alignment/repulsion actions for multi-node selection.

### 2026-10-13 00:54:00
- **fix(patchbay)**: Resolve empty top context toolbar on selection update
  - Fixed Qt layout collapsing to minimal empty margins during dynamic clear/rebuild by explicitly sizing items via font metrics and unparenting discarded widgets.
  - Ensured top context toolbar correctly displays actions for canvas (unselected), single node, and multiple nodes.

### 2026-10-13 00:45:00
- **feat(patchbay)**: Separate grid visibility from coordinate snapping and implement complete context toolbar actions
  - Separated `options.grid_enabled` (dot grid visual background) and `options.snap_enabled` (coordinate snapping) into independent toggle controls.
  - Added dedicated Grid button and Magnet Snap button to the left navigation tool palette.
  - Expanded top context actions toolbar (`CanvasContextToolBarOverlay`):
    - Single node selection: Edit, Custom UI, Jump to Rack, Clone, Rename, Remove, Split/Join box group, Disconnect All, Arrange Connected, Park Aside, Deselect.
    - Multiple node selection: Align Horiz, Align Vert, Distribute H, Distribute V, Auto-Repel Selected, Disconnect Selected cables, Invert Selection, Deselect.

### 2026-10-13 00:38:00
- **feat(patchbay)**: Split canvas toolbars into dedicated left navigation palette and dynamic top context actions bar
  - Resolved Qt6 `QMouseEvent.globalPos()` AttributeError by implementing `_get_event_global_pos()` using `globalPosition().toPoint()`.
  - Fixed button icon centering and zero-padding alignment across floating toolbars.
  - Re-exported graph utility functions (`arrange`, `repelNodes`, `moveAsideNonConnectedNodes`, `alignSelected`, etc.) from `patchcanvas.__init__.py`.
  - Added `CanvasContextToolBarOverlay` at top-center of the canvas dynamically reflecting selection state:
    - *0 nodes*: Global Auto-Arrange, Repel Overlaps, Park Disconnected, and Select All.
    - *1 node*: Node actions (Edit, Custom UI, Jump to Rack, Clone, Remove, Arrange Connected, Park Aside).
    - *2+ nodes*: Multi-node alignment (Align H/V, Distribute H/V, Auto-Repel Selected, Invert Selection, Deselect).

### 2026-10-13 00:23:00
- **feat(patchbay)**: Photoshop-style vertical floating toolbar on left canvas margin
  - Converted `CanvasToolBarOverlay` to a vertical column floating on the left side of the patchbay canvas.
  - Expanded tools with Auto-Arrange, Auto-Repel, Move Aside Non-Connected, Zoom In, Zoom Out, and Zoom to Fit.
  - Maintained smooth drag repositioning and dark translucent Catppuccin theme styling with subtle dividers.

### 2026-10-13 00:19:00
- **fix(patchbay)**: Fix NameError for `options` in `PatchScene.drawBackground`
  - Added missing `options`, `ceil`, `QColor`, and `QBrush` imports to `scene.py` preventing crashes during canvas background repaints.

### 2026-10-13 00:15:00
- **fix(patchbay)**: Immediate cable gradient refresh on node color change
  - Force-repainted connected cable lines and scheduled an instant scene redraw inside `CanvasBox.setCustomColor()`, updating gradient endpoints immediately without requiring node repositioning.

### 2026-10-13 00:14:00
- **feat(patchbay)**: Physics-based iterative auto-repel tools
  - Added `repelNodes()` with AABB overlap resolution and configurable padding/iterations.
  - Added "Auto-Repel (Selected)" and "Auto-Repel (All)" options to the canvas box "Arrange & Align" context menu.

### 2026-10-13 00:11:00
- **feat(patchbay)**: Subtle canvas alignment dot grid and coordinate snapping
  - Added background alignment dot rendering in `PatchScene.drawBackground()` with adaptive contrast according to canvas theme luminance.
  - Implemented node drag snapping to the grid via `CanvasBox.fixPos()`.
  - Added automatic grid snapping to `alignSelected()` operations (`horizontal`, `vertical`, `distribute_h`, `distribute_v`).

### 2026-10-13 00:08:00
- **fix(patchbay)**: Synchronize minimap preview bounds with infinite canvas scene limits
  - Dynamically updated `fRenderSource` and `fInternalRatio` in `CanvasPreviewFrame` to match expanding `sceneRect()` bounds.
  - Calculated `setViewSize` proportions relative to the live scene bounding box rather than static initial canvas dimensions.

### 2026-10-13 00:01:00
- **fix(patchbay)**: Resolve `CanvasBox.calculateBoxSize` AttributeError
  - Aliased `calculateBoxSize` to `updatePositions` on `CanvasBox` and directly invoked `updatePositions` on toolbar toggle and project restore.

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

