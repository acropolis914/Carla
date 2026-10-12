# ![Carla Logo](resources/48x48/carla.png) Clara (Carla Improved Fork)

![Screenshot](resources/screenshots/image.png?raw=true&v=2)

**Clara** (working title for *Carla Improved*) is an enhanced, modernized fork of [Carla](https://github.com/falkTX/Carla) by [falkTX](https://github.com/falkTX). It focuses on modern modular patchbay UX/UI improvements, robust session safety, fluid navigation, and deep workflow optimizations for audio producers, sound designers, and live performers.

---

## ✨ Clara Features & Improvements

### 🎛️ Modern Patchbay Canvas & Navigation
* **Dual Modal Tools & Navigation**:
  * Photoshop/Blender-inspired tool hotkeys: `V` (Select/Move), `H` / `Space` (Hand/Pan tool), and `Q` (Quick Marquee).
  * Smooth canvas panning via middle-click or empty space left-click dragging.
  * Zoom-synchronized interactive patchbay minimap with visible viewport frustum indicator.
* **Canvas Node Quick Search (`Ctrl+F`)**:
  * In-canvas floating search bar with fuzzy-matching to quickly filter and pinpoint nodes across massive routing setups.
  * Direct canvas centering and selection upon cycling search results.
* **Selection & Alignment Utilities**:
  * Industry-standard selection shortcuts: `Ctrl+A` (Select All), `Ctrl+D` (Deselect All), and `Ctrl+Shift+I` (Invert Selection).
  * Preservation of multi-selection across right-click context actions.
  * Smart horizontal/vertical alignment actions and non-overlapping node repel tools.
* **Crisp HiDPI & Hardware Accelerated Rendering**:
  * Native 4x MSAA multisampling on OpenGL canvas viewports.
  * Integer-snapped coordinate rasterization preventing subpixel text blur on node titles and port labels.

### 🎨 Vibrant Visuals & Cable Routing
* **Unified Catppuccin Node Theming**:
  * Vivid Catppuccin category colors applied automatically by plugin type (Synth, Delay, EQ, Filter, Distortion, Dynamics, Modulator, Utility).
  * Node header tinting (35%) with adaptive luminance contrast text calculations and accent divider bars.
  * Customizable node colors with direct `QColorDialog` integration, synced bidirectionally between patchbay nodes and rack skins.
* **Dynamic Cable Gradients & Styling**:
  * Source-to-destination linear color gradients that dynamically interpolate between node and port colors along connecting cables.
  * Support for multiple cable routing formulas (Bezier curves, Straight/Linear lines, Orthogonal right-angle paths).

### 🎚️ Side-by-Side Dual-View Workflow
* **Synchronized Mini Rack & Patchbay**:
  * Split side-by-side view combining modular graph routing with instant rack parameter access.
  * Bidirectional scroll and focus synchronization: selecting a node in the patchbay instantly focuses and scrolls to its corresponding rack module, and vice versa.

### 💾 Session Safety & Project Management
* **Persistent Node Layouts & Custom Metadata**:
  * Node split coordinates, custom colors, and canvas arrangements saved directly within `.carxp`, `.carjp`, and `.json` project files.
* **Rotating Autosaves & Dirty State Tracking**:
  * Background autosave engine with automatic rotation (`.autosaves/`) and duplicate recursion prevention.
  * Visual dirty state indicators in the title bar (`*`) and status bar (`[Saved]` / `[Modified]`).
  * Live status countdown timer showing time elapsed since last autosave and countdown until the next save interval.
  * Safe exit verification dialog (`Save`, `Discard`, `Cancel`) when closing with unsaved changes.
* **Recent Projects & Autoloading**:
  * Recent projects submenu in `File` menu with clean filenames, tooltips, and status bar path previews.
  * `--autoload-lastsave` CLI flag to automatically resume the last opened project on startup.

### 🔍 Rich Console Logging & Diagnostics
* **Rich Diagnostic Console**:
  * Python `rich` formatted terminal output with colored loglevels, timestamps, and categorical tags (`APP`, `ENGINE`, `PATCHBAY`, `PLUGIN`, `SESSION`, `CANVAS`, `BACKEND`).
  * Real-time interception and formatting of low-level C++ backend `stderr` log streams.
  * Interactive UI log filter checklist and CLI filter flags (`--log-whitelist`, `--log-blacklist`).

### ⚙️ Live Settings & UI Customization
* **Instant Reactive Adjustments (No Restarts Required)**:
  * Real-time sliders for rack slot vertical margin/spacing (0–16 px) and slot internal padding (2–16 px).
  * Dynamic slot minimum width floor adjustments (180–450 px).
  * Instant toggle for bottom status bar visibility.
* **Modernized Settings Dialog**:
  * Clean, borderless sidebar navigation with refined sans-serif typography and 32px compact tab pills.
  * Removal of legacy low-resolution bitmap icons across all dialog headers and sidebar tabs.
  * Sleek Catppuccin Mochaccino dialog aesthetics with subtle surface cards and rounded interactive controls.

---

## 🗺️ Roadmap & In Progress

Track full development details and priorities in [TODO.md](TODO.md):
- [ ] Visual audio/MIDI signal activity animations along cables and active nodes.
- [ ] Mini DSP load history graph with side labels and hover tooltips.
- [ ] In-project session notes with rich Qt Markdown (`QTextDocument`) preview.
- [ ] Infinite canvas with migration recentering for legacy projects.
- [x] Settings dialog redesign featuring live reactive tweakables and cohesive typography.
- [ ] Standardized `argparse` CLI integration with `rich` help output.

---

## 📦 Installation & Packaging

* **Arch Linux / AUR / Pacman**:
  * Bundled [`PKGBUILD`](PKGBUILD) package (`carla-improved`) targeting Qt6 for clean package management.
  * Helper `build.sh` script for rapid local builds and testing.
  * See [`installation.md`](installation.md) for full Arch Linux / makepkg and build-from-source guides.

---

## 🤖 AI Clause

Portions of the modifications, features, refactoring, and documentation in this repository were developed and assisted by AI coding agents (including Google Antigravity / Gemini) working in collaboration with the repository maintainer. All contributions are reviewed, tested, and integrated for quality and compatibility.

---

## 🏛️ Upstream Features

* LADSPA, DSSI, LV2, VST2, VST3, CLAP, and AU plugin format support
* SF2/3 and SFZ sound bank engines
* Internal audio and MIDI file player
* MIDI CC parameter automation and [OSC](https://opensoundcontrol.stanford.edu/) control
* Rack, Patchbay, and JACK Single/Multi-Client processing modes
* Native ALSA, DirectSound, CoreAudio, PulseAudio, and JACK/PipeWire drivers

Refer to the [upstream documentation](https://kx.studio/Applications:Carla) for base Carla documentation.
