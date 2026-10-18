# Clara "Add Plugin" Dialog Modernization Specification

## Overview
This specification details the modernization of Carla's plugin browser (`PluginListDialog` in `source/frontend/pluginlist/pluginlistdialog_py.py`), replacing the legacy `QToolBox` accordion filter interface with a cohesive, vanilla Qt-styled left sidebar featuring grouped checkable multiselect pills.

---

## 1. Feature & UI Parity Matrix

| Feature / Widget | Legacy `PluginListDialog` (`QToolBox`) | Modernized `PluginListDialog` (Left Sidebar Pills) | Parity Status & Functional Rules |
| :--- | :--- | :--- | :--- |
| **Sidebar Layout** | `QToolBox` (collapsible pages; only 1 category open at a time) | Dedicated left sidebar with scrollable `QVBoxLayout` and flow/pill layouts | **Full Parity + QoL**: All filter categories are visible simultaneously without tab accordion switching. |
| **Format Filters** | 10 Checkboxes: Internal, LADSPA, DSSI, LV2, VST2, VST3, CLAP, AU, JSFX, Sound Kits | Grouped checkable `QPushButton` pills: `[All]`, `[CLAP]`, `[VST3]`, `[LV2]`, `[VST2]`, `[JSFX]`, `[Internal]`, `[LADSPA]`, `[DSSI]`, `[Kits]`, `[AU]` | **Full Parity**: Preserves all 10 formats. Selecting `[All]` clears specifics; selecting specifics unchecks `[All]`. Deselecting all specifics re-engages `[All]`. |
| **Type Filters** | 4 Checkboxes: Effects, Instruments, MIDI Plugins, Other/Misc | Grouped checkable `QPushButton` pills: `[All]`, `[Instruments]`, `[Effects]`, `[MIDI]`, `[Other]` | **Full Parity**: Preserves all 4 types with multiselect OR semantics. |
| **Category Filters** | 10 Checkboxes: All, Delay, Distortion, Dynamics, EQ, Filter, Modulator, Synth, Utility, Other | Grouped checkable `QPushButton` pills: `[All]`, `[Synth]`, `[Delay]`, `[Distortion]`, `[Dynamics]`, `[EQ]`, `[Filter]`, `[Modulator]`, `[Utility]`, `[Other]` | **Full Parity**: Category match against plugin metadata string. |
| **Architecture Filters** | 3 Checkboxes: Native, Bridged, Bridged (Wine) | Grouped checkable `QPushButton` pills: `[All]`, `[Native]`, `[Bridged]`, `[Wine Bridged]` | **Full Parity**: Filters against `data["isNative"]`, `data["isBridged"]`, `data["isBridgedWine"]`. |
| **Requirements Filters** | 6 Checkboxes: RT-safe, Stereo, CV Ports, Custom GUI, Inline Display, Favorites | Grouped checkable `QPushButton` pills: `[Any]`, `[RT-Safe]`, `[Stereo]`, `[CV Ports]`, `[Custom GUI]`, `[Inline Display]` + Dedicated `[★ Favorites]` toggle | **Full Parity**: Evaluates capability flags (`PLUGIN_IS_RTSAFE`, `PLUGIN_HAS_CUSTOM_UI`, etc.). |
| **Filter Reset** | `QPushButton` in top search bar | `QPushButton` anchored at bottom of Left Filter Sidebar | **Full Parity**: Resets all pill groups back to `[All]`, unchecks favorites, and clears search input. |
| **Search Bar** | `QLineEdit` with search text debounce timer | `QLineEdit` with search text debounce timer and embedded clear icon | **Full Parity**: Real-time tokenized substring filter against name, label, maker, URI. |
| **Rescan Actions** | `QToolButton` with popup menu (Quick / Full rescan) | `QToolButton` beside search field with identical menu and actions | **Full Parity**: `_startScan(ignoreCache=...)` triggers discovery backend. |
| **Plugin Table** | `QTableWidget` 5 columns (Fav, Name, Label/URI, Maker, Binary) | Identical `QTableWidget` structure, selection mode, sort order, and context menu | **100% Parity**: Zero changes to data model, sorting, or row caching. |
| **Inspector Panel** | `QTabWidget` (`tab_info`) with General, Audio/MIDI, Ports, D-Bus tabs | Identical `tab_info` preserved on the right pane | **100% Parity**: General info and port tables unchanged. |
| **Bottom Bar** | `label` count, `ch_keep_open`, `b_add`, `b_cancel` | Identical layout, shortcut handling, and double-click to add | **100% Parity**: Retains all modal and non-modal behaviors. |
| **Config Persistence** | `QSafeSettings` (`PluginDatabase/*`) | Identical settings keys read/written in `_loadSettings()` and `_saveSettings()` | **100% Backward Compatible**: Existing user presets and window geometry are preserved. |

---

## 2. Interaction Specifications

### 2.1 Multiselect & Toggle Logic
Each filter category (`Format`, `Type`, `Category`, `Architecture`, `Requirements`) operates as an independent toggle group:
1. **The `[All]` / `[Any]` Master Pill**:
   - Active by default.
   - When clicked, all specific pills in that group are unchecked and `[All]` becomes checked.
   - If all specific pills in a group are manually unchecked, `[All]` automatically reactivates.
2. **Specific Pills**:
   - Clicking a specific pill toggles its state (`isChecked()`).
   - If checked, `[All]` is immediately deactivated.
   - Multiple specific pills within a group can be simultaneously checked (Union / OR filtering).
3. **Cross-Group Evaluation**:
   - The plugin match predicate evaluates groups with `AND` logic:
     `match = match_search AND match_format AND match_type AND match_category AND match_arch AND match_reqs AND match_favorites`.

### 2.2 Vanilla Qt Styling & Nerd Font Integration
- Uses native `QPushButton` with `setCheckable(True)`.
- Follows existing desktop palette / Catppuccin themes without hardcoded web colors.
- Uses `getIcon()` and `getBestNerdFont()` glyphs for visual iconography where appropriate.
- Preserves native desktop styling with standard button heights, padding, and subtle checkable bevels.

---

## 3. Implementation Plan

1. **Pill Group Helper (`PillGroupWidget`)**:
   - A lightweight helper class wrapping a label, flow/wrap layout, `[All]` button, and a dictionary of named checkable `QPushButton` pills.
   - Handles the mutual exclusion between `[All]` and specific pills, emitting a single `changed` signal.
2. **Filter Sidebar Construction (`_buildFilters`)**:
   - Replace `QToolBox` in `source/frontend/pluginlist/pluginlistdialog_py.py` with a vertical container in column 0 of `grid`.
   - Add pill groups for Format, Type, Category, Architecture, and Requirements.
   - Anchor `b_clear_filters` at the bottom of the sidebar.
3. **Filter Matching & Settings Synchronization**:
   - Update `_filterSingleRow` and `_checkFilters` to query the pill group active states.
   - Ensure `_loadSettings`, `_saveSettings`, and `_clearFilters` update the pill buttons seamlessly.

---

## 4. Center Presentation Modes

The center plugin browser supports three presentation modes managed by `QStackedWidget` (`self.stackCenter`) and toggled via mode pills in the search bar:

1. **Rack Mode (Default, Index 0)**:
   - Compact horizontal capsule slot (`RackPluginItemWidget`, ~44px height) matching Clara's rack slots.
   - Contains left category accent strip, favorite star icon, format badge pill, bold title, maker/category subtitle, and right-aligned I/O tag capsule.
2. **Cards Mode (Index 1)**:
   - Modular grid card (`CardPluginItemWidget`, ~180x105px) in `QListWidget` IconMode.
   - Features category colored top border, format badge, favorite star, bold title, maker, category, and I/O tags.
3. **Table Mode (Index 2)**:
   - Classic sortable `QTableWidget` (`self.table`) with multi-column headers and sort indicators.

All three presentation modes maintain 1:1 synchronized selection, favorite toggling, and row visibility during filtering.
Active view mode preference is saved in `PluginDatabase/ViewMode`.

### Selected Pill Highlight
- Checked filter pills utilize vibrant, unmistakable accent styling (`#1e66f5`/`#1976d2` solid fill, crisp white bold text `#ffffff`, and 2px border `#7287fd`/`#64b5f6`) across all Catppuccin and Classic Dark theme stylesheets.
