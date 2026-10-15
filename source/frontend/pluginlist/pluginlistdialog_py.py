#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Pure-Python/PyQt6 port of the C++ PluginListDialog ("Carla - Add New" plugin browser).
#
# This replaces the Qt-linked native libcarla_frontend for the Add-Plugin dialog. Plugin discovery still comes
# from the NON-Qt native backend `libcarla_utils`, through pluginlist/discovery_py.py.
# ------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import os
import struct
import sys

# Make sure the frontend folder and this folder are importable regardless of how we were loaded.
_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.dirname(_HERE)
for _d in (_FRONTEND_DIR, _HERE):
    if _d not in sys.path:
        sys.path.insert(0, _d)

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)

from qt_compat import (
    QAbstractItemView,
    QAction,
    QCheckBox,
    QDialog,
    QFileInfo,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QIcon,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSettings,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTimer,
    QVBoxLayout,
    QWidget,
    Qt,
)

try:
    from PyQt6.QtCore import QByteArray
    from PyQt6.QtWidgets import QRadioButton, QToolBox  # noqa: F811
except ImportError:  # pragma: no cover - Qt5 fallback
    from PyQt5.QtCore import QByteArray
    from PyQt5.QtWidgets import QRadioButton, QToolBox  # noqa: F811

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from carla_backend import (
    BINARY_NATIVE,
    BINARY_NONE,
    BINARY_OTHER,
    BINARY_POSIX32,
    BINARY_POSIX64,
    BINARY_WIN32,
    BINARY_WIN64,
    CARLA_OS_64BIT,
    CARLA_OS_MAC,
    CARLA_OS_WIN,
    ENGINE_OPTION_WINE_AUTO_PREFIX,
    ENGINE_OPTION_WINE_EXECUTABLE,
    ENGINE_OPTION_WINE_FALLBACK_PREFIX,
    PLUGIN_AU,
    PLUGIN_CLAP,
    PLUGIN_DSSI,
    PLUGIN_INTERNAL,
    PLUGIN_JSFX,
    PLUGIN_LADSPA,
    PLUGIN_LV2,
    PLUGIN_NONE,
    PLUGIN_SF2,
    PLUGIN_SFZ,
    PLUGIN_VST2,
    PLUGIN_VST3,
    PLUGIN_IS_BRIDGE,
    PLUGIN_IS_RTSAFE,
    PLUGIN_IS_SYNTH,
    PLUGIN_HAS_CUSTOM_UI,
    PLUGIN_HAS_INLINE_DISPLAY,
)
from carla_shared import getIcon
from carla_utils import getPluginCategoryAsString, getPluginTypeAsString

from utils import QSafeSettings

try:
    from .discovery_py import PluginDiscovery, get_library_folder, set_option
except ImportError:  # loaded as a top-level module
    from discovery_py import PluginDiscovery, get_library_folder, set_option  # type: ignore

# ------------------------------------------------------------------------------------------------------------
# Table / role constants (must match the C++ enums)

TW_FAVORITE = 0
TW_NAME     = 1
TW_LABEL    = 2
TW_MAKER    = 3
TW_BINARY   = 4

UR_PLUGIN_INFO = 1
UR_SEARCH_TEXT = 2

_TABLE_COLUMNS = 5

# ------------------------------------------------------------------------------------------------------------
# Enum compatibility helpers (PyQt5 uses short forms, PyQt6 requires scoped enums)

def _qt_checkstate(checked):
    try:
        return Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
    except AttributeError:  # PyQt5
        return Qt.Checked if checked else Qt.Unchecked  # noqa: F821


def _qt_accepted():
    try:
        return QDialog.DialogCode.Accepted
    except AttributeError:  # PyQt5
        return QDialog.Accepted  # noqa: F821


_NO_EDIT_TRIGGERS = getattr(QAbstractItemView, "NoEditTriggers", None)
if _NO_EDIT_TRIGGERS is None:
    _NO_EDIT_TRIGGERS = QAbstractItemView.EditTrigger.NoEditTriggers

_SELECT_ROWS = getattr(QAbstractItemView, "SelectRows", None)
if _SELECT_ROWS is None:
    _SELECT_ROWS = QAbstractItemView.SelectionBehavior.SelectRows

_SINGLE_SELECTION = getattr(QAbstractItemView, "SingleSelection", None)
if _SINGLE_SELECTION is None:
    _SINGLE_SELECTION = QAbstractItemView.SelectionMode.SingleSelection

_ALIGN_RIGHT = getattr(Qt, "AlignRight", None)
if _ALIGN_RIGHT is None:
    _ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight


def _checkstate_checked(item):
    try:
        return item.checkState() == Qt.CheckState.Checked
    except AttributeError:  # PyQt5
        return item.checkState() == Qt.Checked  # noqa: F821

# ------------------------------------------------------------------------------------------------------------
# PluginInfo / PluginFavorite binary serialization (identical to the C++ asByteArray/asPluginInfo)

# PluginInfoHeader: uint16 build, uint16 type, uint32 hints, uint64 uniqueId,
#                   uint16 audioIns, audioOuts, cvIns, cvOuts, midiIns, midiOuts, parameterIns, parameterOuts
_INFO_HEADER = struct.Struct("<HHIQHHHHHHHH")

# PluginFavoriteHeader: uint16 type, (6 bytes padding), uint64 uniqueId
_FAV_HEADER = struct.Struct("<H6xQ")

_INFO_STRINGS = ("category", "filename", "name", "label", "maker")


def _infoToBytes(info):
    out = bytearray()
    out += _INFO_HEADER.pack(
        int(info["build"]) & 0xFFFF,
        int(info["type"]) & 0xFFFF,
        int(info["hints"]) & 0xFFFFFFFF,
        int(info["uniqueId"]) & 0xFFFFFFFFFFFFFFFF,
        int(info["audioIns"]) & 0xFFFF,
        int(info["audioOuts"]) & 0xFFFF,
        int(info["cvIns"]) & 0xFFFF,
        int(info["cvOuts"]) & 0xFFFF,
        int(info["midiIns"]) & 0xFFFF,
        int(info["midiOuts"]) & 0xFFFF,
        int(info["parameterIns"]) & 0xFFFF,
        int(info["parameterOuts"]) & 0xFFFF,
    )
    for key in _INFO_STRINGS:
        out += (info.get(key) or "").encode("utf-8", errors="replace") + b"\0"
    return bytes(out)


def _bytesToInfo(data, offset=0):
    if isinstance(data, QByteArray):
        data = bytes(data)
    if len(data) < offset + _INFO_HEADER.size:
        return None, offset

    (build, ptype, hints, uniqueId,
     aIn, aOut, cvIn, cvOut, mIn, mOut, pIn, pOut) = _INFO_HEADER.unpack_from(data, offset)
    pos = offset + _INFO_HEADER.size

    def readStr():
        nonlocal pos
        end = data.find(b"\0", pos)
        if end < 0:
            end = len(data)
        value = data[pos:end].decode("utf-8", errors="replace")
        pos = end + 1
        return value

    info = {
        "build": build,
        "type": ptype,
        "hints": hints,
        "uniqueId": uniqueId,
        "audioIns": aIn,
        "audioOuts": aOut,
        "cvIns": cvIn,
        "cvOuts": cvOut,
        "midiIns": mIn,
        "midiOuts": mOut,
        "parameterIns": pIn,
        "parameterOuts": pOut,
        "category": readStr(),
        "filename": readStr(),
        "name": readStr(),
        "label": readStr(),
        "maker": readStr(),
    }
    return info, pos


def _infoListToBytes(infos):
    out = bytearray()
    for info in infos:
        out += _infoToBytes(info)
    return bytes(out)


def _bytesToInfoList(data):
    infos = []
    offset = 0
    while offset < len(data):
        info, offset = _bytesToInfo(data, offset)
        if info is None or info["build"] == BINARY_NONE:
            break
        infos.append(info)
    return infos

# ------------------------------------------------------------------------------------------------------------
# Settings helpers

_SETTINGS_ORG = "falkTX"
_SETTINGS_APP = "CarlaDatabase3"


def _newSettings():
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    return settings


def _getBool(settings, key, default):
    try:
        value = settings.value(key, default)
    except Exception:
        return default
    if value is None:
        return default
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


def _getStr(settings, key, default):
    try:
        value = settings.value(key, default)
    except Exception:
        return default
    if value is None:
        return default
    return str(value)


def _getBytes(settings, key):
    try:
        value = settings.value(key, QByteArray())
    except Exception:
        return b""
    if value is None:
        return b""
    if isinstance(value, QByteArray):
        return bytes(value)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return b""

# ------------------------------------------------------------------------------------------------------------
# Default plugin paths (env vars + common locations). Mirrors the C++ PluginPaths helper.

def _defaultPluginPaths():
    home = os.path.expanduser("~")
    paths = {
        PLUGIN_LADSPA: "",
        PLUGIN_DSSI: "",
        PLUGIN_LV2: "",
        PLUGIN_VST2: "",
        PLUGIN_VST3: "",
        PLUGIN_CLAP: "",
        PLUGIN_JSFX: "",
        PLUGIN_SF2: "",
        PLUGIN_SFZ: "",
    }
    if CARLA_OS_MAC:
        paths[PLUGIN_AU] = os.path.join(home, "Library/Audio/Plug-Ins/Components") + \
                          ":/Library/Audio/Plug-Ins/Components:/System/Library/Components"

    if CARLA_OS_WIN:
        appdata = os.environ.get("APPDATA", "")
        localappdata = os.environ.get("LOCALAPPDATA", appdata)
        programfiles = os.environ.get("PROGRAMFILES", "")
        common = os.environ.get("COMMONPROGRAMFILES", "")

        paths[PLUGIN_LADSPA] = os.environ.get("LADSPA_PATH", appdata + "\\LADSPA;" + programfiles + "\\LADSPA")
        paths[PLUGIN_DSSI] = os.environ.get("DSSI_PATH", appdata + "\\DSSI;" + programfiles + "\\DSSI")
        paths[PLUGIN_LV2] = os.environ.get("LV2_PATH", appdata + "\\LV2;" + common + "\\LV2")
        paths[PLUGIN_VST2] = os.environ.get("VST_PATH",
            programfiles + "\\VSTPlugins;" + programfiles + "\\Steinberg\\VSTPlugins;"
            + common + "\\VST2;" + common + "\\Steinberg\\VST2")
        paths[PLUGIN_VST3] = os.environ.get("VST3_PATH", localappdata + "\\Programs\\Common\\VST3;" + common + "\\VST3")
        paths[PLUGIN_CLAP] = os.environ.get("CLAP_PATH", localappdata + "\\Programs\\Common\\CLAP;" + common + "\\CLAP")
        paths[PLUGIN_JSFX] = os.environ.get("JSFX_PATH", appdata + "\\REAPER\\Effects")
        paths[PLUGIN_SF2] = os.environ.get("SF2_PATH", appdata + "\\SF2")
        paths[PLUGIN_SFZ] = os.environ.get("SFZ_PATH", appdata + "\\SFZ")
        return paths

    # Unix-ish
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))

    paths[PLUGIN_LADSPA] = os.environ.get("LADSPA_PATH",
        os.path.join(home, ".ladspa") + ":/usr/local/lib/ladspa:/usr/lib/ladspa")
    paths[PLUGIN_DSSI] = os.environ.get("DSSI_PATH",
        os.path.join(home, ".dssi") + ":/usr/local/lib/dssi:/usr/lib/dssi")
    paths[PLUGIN_LV2] = os.environ.get("LV2_PATH",
        os.path.join(home, ".lv2") + ":/usr/local/lib/lv2:/usr/lib/lv2")
    paths[PLUGIN_VST2] = os.environ.get("VST_PATH",
        os.path.join(home, ".vst") + ":" + os.path.join(home, ".lxvst")
        + ":/usr/local/lib/vst:/usr/local/lib/lxvst:/usr/lib/vst:/usr/lib/lxvst")
    paths[PLUGIN_VST3] = os.environ.get("VST3_PATH",
        os.path.join(home, ".vst3") + ":/usr/local/lib/vst3:/usr/lib/vst3")
    paths[PLUGIN_CLAP] = os.environ.get("CLAP_PATH",
        os.path.join(home, ".clap") + ":/usr/local/lib/clap:/usr/lib/clap")
    paths[PLUGIN_JSFX] = os.environ.get("JSFX_PATH", config_home + "/REAPER/Effects")
    paths[PLUGIN_SF2] = os.environ.get("SF2_PATH",
        os.path.join(home, ".sounds/sf2") + ":" + os.path.join(home, ".sounds/sf3")
        + ":/usr/share/sounds/sf2:/usr/share/sounds/sf3:/usr/share/soundfonts")
    paths[PLUGIN_SFZ] = os.environ.get("SFZ_PATH",
        os.path.join(home, ".sounds/sfz") + ":/usr/share/sounds/sfz")

    # Add wine prefixes (bridged Windows plugins)
    wine_prefix = os.environ.get("WINEPREFIX") or os.path.join(home, ".wine")
    if os.path.isdir(wine_prefix):
        drive_c = os.path.join(wine_prefix, "drive_c")
        for base in ("Program Files", "Program Files (x86)"):
            d = os.path.join(drive_c, base)
            if os.path.isdir(d):
                paths[PLUGIN_VST2] += ":" + os.path.join(d, "VstPlugins")
                paths[PLUGIN_VST2] += ":" + os.path.join(d, "Steinberg/VstPlugins")
                paths[PLUGIN_VST2] += ":" + os.path.join(d, "Common Files/VST2")
                paths[PLUGIN_VST3] += ":" + os.path.join(d, "Common Files/VST3")
                paths[PLUGIN_CLAP] += ":" + os.path.join(d, "Common Files/CLAP")

    return paths

# ------------------------------------------------------------------------------------------------------------
# Plugin Refresh dialog (ported from pluginrefreshdialog.ui)

class _PluginRefreshDialog(QDialog):
    def __init__(self, parent, firstInit=False):
        super().__init__(parent)
        self._firstInit = firstInit

        self.setWindowTitle(self.tr("Carla - Refresh Plugins"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        if CARLA_OS_MAC:
            self.setWindowModality(Qt.WindowModal)

        main = QVBoxLayout(self)

        top = QHBoxLayout()
        self.group = QGroupBox(self.tr("Refresh Options"), self)
        groupLayout = QVBoxLayout(self.group)
        self.ch_all = QRadioButton(self.tr("Scan all plugins"))
        self.ch_updated = QRadioButton(self.tr("Only scan updated/new"))
        self.ch_invalid = QCheckBox(self.tr("Check for invalid plugins"))
        groupLayout.addWidget(self.ch_all)
        groupLayout.addWidget(self.ch_updated)
        groupLayout.addWidget(self.ch_invalid)
        top.addWidget(self.group)
        top.addStretch(1)
        main.addLayout(top)
        main.addStretch(1)

        self.group_formats = QGroupBox(self.tr("Restrict Formats"), self)
        self.group_formats.setCheckable(True)
        formatsLayout = QGridLayout(self.group_formats)
        self.ch_ladspa = QCheckBox("LADSPA")
        self.ch_dssi = QCheckBox("DSSI")
        self.ch_lv2 = QCheckBox("LV2")
        self.ch_vst2 = QCheckBox("VST2")
        self.ch_vst3 = QCheckBox("VST3")
        self.ch_clap = QCheckBox("CLAP")
        self.ch_au = QCheckBox("AU")
        self.ch_jsfx = QCheckBox("JSFX")
        self.ch_sf2 = QCheckBox("SF2")
        self.ch_sfz = QCheckBox("SFZ")
        for i, w in enumerate((self.ch_ladspa, self.ch_dssi, self.ch_lv2, self.ch_vst2, self.ch_vst3,
                               self.ch_clap, self.ch_au, self.ch_jsfx, self.ch_sf2, self.ch_sfz)):
            formatsLayout.addWidget(w, i // 5, i % 5)
        main.addWidget(self.group_formats)

        self.progressBar = QProgressBar(self)
        main.addWidget(self.progressBar)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.b_start = QPushButton(self.tr("Start"))
        self.b_skip = QPushButton(self.tr("Skip Current"))
        buttons.addWidget(self.b_start)
        buttons.addWidget(self.b_skip)
        main.addLayout(buttons)

        self.b_skip.setEnabled(False)
        self.ch_invalid.setEnabled(False)

        if not firstInit:
            self._loadSettings()

        self.finished.connect(self._saveSettings)

    def _loadSettings(self):
        settings = _newSettings()
        if _getBool(settings, "PluginRefreshDialog/RefreshAll", False):
            self.ch_all.setChecked(True)
        else:
            self.ch_updated.setChecked(True)
        self.ch_invalid.setChecked(_getBool(settings, "PluginRefreshDialog/CheckInvalid", False))
        self.group_formats.setChecked(_getBool(settings, "PluginRefreshDialog/RestrictFormats", False))
        self.ch_ladspa.setChecked(_getBool(settings, "PluginRefreshDialog/SearchLADSPA", True))
        self.ch_dssi.setChecked(_getBool(settings, "PluginRefreshDialog/SearchDSSI", True))
        self.ch_lv2.setChecked(_getBool(settings, "PluginRefreshDialog/SearchLV2", True))
        self.ch_vst2.setChecked(_getBool(settings, "PluginRefreshDialog/SearchVST2", True))
        self.ch_vst3.setChecked(_getBool(settings, "PluginRefreshDialog/SearchVST3", True))
        self.ch_clap.setChecked(_getBool(settings, "PluginRefreshDialog/SearchCLAP", True))
        self.ch_au.setChecked(_getBool(settings, "PluginRefreshDialog/SearchAU", True))
        self.ch_jsfx.setChecked(_getBool(settings, "PluginRefreshDialog/SearchJSFX", True))
        self.ch_sf2.setChecked(_getBool(settings, "PluginRefreshDialog/SearchSF2", True))
        self.ch_sfz.setChecked(_getBool(settings, "PluginRefreshDialog/SearchSFZ", True))

    def _saveSettings(self, *_args):
        if self._firstInit:
            return
        settings = _newSettings()
        settings.setValue("PluginRefreshDialog/RefreshAll", self.ch_all.isChecked())
        settings.setValue("PluginRefreshDialog/CheckInvalid", self.ch_invalid.isChecked())
        settings.setValue("PluginRefreshDialog/RestrictFormats", self.group_formats.isChecked())
        settings.setValue("PluginRefreshDialog/SearchLADSPA", self.ch_ladspa.isChecked())
        settings.setValue("PluginRefreshDialog/SearchDSSI", self.ch_dssi.isChecked())
        settings.setValue("PluginRefreshDialog/SearchLV2", self.ch_lv2.isChecked())
        settings.setValue("PluginRefreshDialog/SearchVST2", self.ch_vst2.isChecked())
        settings.setValue("PluginRefreshDialog/SearchVST3", self.ch_vst3.isChecked())
        settings.setValue("PluginRefreshDialog/SearchCLAP", self.ch_clap.isChecked())
        settings.setValue("PluginRefreshDialog/SearchAU", self.ch_au.isChecked())
        settings.setValue("PluginRefreshDialog/SearchJSFX", self.ch_jsfx.isChecked())
        settings.setValue("PluginRefreshDialog/SearchSF2", self.ch_sf2.isChecked())
        settings.setValue("PluginRefreshDialog/SearchSFZ", self.ch_sfz.isChecked())

# ------------------------------------------------------------------------------------------------------------
# The main dialog

class PyPluginListDialog(QDialog):
    def __init__(self, parent, hostSettings):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Carla - Add New"))

        hostSettings = hostSettings or {}

        # -- discovery state -----------------------------------------------------------------------------
        self.paths = _defaultPluginPaths()
        self.cache = {}          # sha1 -> [PluginInfo dict]
        self.favorites = []      # [ {'type', 'uniqueId', 'filename', 'label'} ]
        self._plugins = {
            "internal": [], "ladspa": [], "dssi": [], "lv2": [], "vst2": [],
            "vst3": [], "clap": [], "au": [], "jsfx": [], "kits": [],
        }

        self.retPlugin = {}

        self._lastTableWidgetIndex = 0
        self._refreshDialog = None

        self._discovery = {
            "btype": BINARY_NATIVE,
            "ptype": PLUGIN_NONE,
            "firstInit": True,
            "ignoreCache": False,
            "checkInvalid": False,
            "usePluginBridges": bool(hostSettings.get("showPluginBridges", False)),
            "useWineBridges": bool(hostSettings.get("showWineBridges", False)),
            "handle": None,
            "tool": "",
        }
        self._restartDiscoveryTool()

        # -- global discovery options --------------------------------------------------------------------
        if not CARLA_OS_WIN:
            try:
                set_option(ENGINE_OPTION_WINE_AUTO_PREFIX, 1 if hostSettings.get("wineAutoPrefix") else 0, None)
                set_option(ENGINE_OPTION_WINE_EXECUTABLE, 0, hostSettings.get("wineExecutable") or "")
                set_option(ENGINE_OPTION_WINE_FALLBACK_PREFIX, 0, hostSettings.get("wineFallbackPrefix") or "")
            except Exception as exc:  # pragma: no cover
                print("PyPluginListDialog: set_option failed:", exc)

        # -- build UI ------------------------------------------------------------------------------------
        self._buildUi(hostSettings)

        # -- connections ---------------------------------------------------------------------------------
        self.finished.connect(self._saveSettings)
        self.b_add.clicked.connect(self.accept)
        self.b_cancel.clicked.connect(self.reject)
        self.b_refresh.clicked.connect(self._refreshPlugins)
        self.b_clear_filters.clicked.connect(self._clearFilters)

        self.lineEdit.textChanged.connect(lambda _text: self._checkFilters())
        self.table.currentCellChanged.connect(lambda r, c, pr, pc: self._checkPlugin(r))
        self.table.cellClicked.connect(self._cellClicked)
        self.table.cellDoubleClicked.connect(self._cellDoubleClicked)

        for ch in (self.ch_internal, self.ch_ladspa, self.ch_dssi, self.ch_lv2, self.ch_vst, self.ch_vst3,
                   self.ch_clap, self.ch_au, self.ch_jsfx, self.ch_kits, self.ch_effects,
                   self.ch_instruments, self.ch_midi, self.ch_other, self.ch_native, self.ch_bridged,
                   self.ch_bridged_wine, self.ch_favorites, self.ch_rtsafe, self.ch_cv, self.ch_gui,
                   self.ch_inline_display, self.ch_stereo):
            ch.clicked.connect(lambda _checked=False: self._checkFilters())

        self.ch_cat_all.clicked.connect(self._checkFiltersCategoryAll)
        for ch in (self.ch_cat_delay, self.ch_cat_distortion, self.ch_cat_dynamics, self.ch_cat_eq,
                   self.ch_cat_filter, self.ch_cat_modulator, self.ch_cat_synth, self.ch_cat_utility,
                   self.ch_cat_other):
            ch.clicked.connect(self._checkFiltersCategorySpecific)

        # Ctrl+F focus search
        self.act_focus_search = QAction(self.tr("Focus Text Search"), self)
        self.act_focus_search.setShortcut("Ctrl+F")
        self.act_focus_search.triggered.connect(self.focusSearchFieldAndSelectAll)
        self.addAction(self.act_focus_search)

        # -- only native by default ----------------------------------------------------------------------
        if CARLA_OS_64BIT:
            self.ch_bridged.setText(self.tr("Bridged (32bit)"))
        else:
            self.ch_bridged.setChecked(False)
            self.ch_bridged.setEnabled(False)

        if not (CARLA_OS_WIN or CARLA_OS_MAC):
            # bridged wine only really usable on linux
            pass

        if CARLA_OS_MAC:
            self.setWindowModality(Qt.WindowModal)
        else:
            self.ch_au.setChecked(False)
            self.ch_au.setEnabled(False)
            self.ch_au.setVisible(False)

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # -- load settings + cache -----------------------------------------------------------------------
        self._loadSettings()

        # start with no plugin selected
        self._checkPlugin(-1)

        # -- discovery timer -----------------------------------------------------------------------------
        self._timer = QTimer(self)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._discoveryStep)

    # ----------------------------------------------------------------------------------------------------
    # UI construction

    def _buildUi(self, hostSettings):
        grid = QGridLayout(self)

        # row 0: search + refresh + reset
        searchRow = QHBoxLayout()
        self.lineEdit = QLineEdit(self)
        self.lineEdit.setClearButtonEnabled(True)
        searchRow.addWidget(self.lineEdit)

        self.b_refresh = QPushButton(self.tr("Refresh"), self)
        self.b_refresh.setIcon(getIcon("view-refresh", 16, "svgz"))
        searchRow.addWidget(self.b_refresh)

        self.b_clear_filters = QPushButton(self.tr("Reset filters"), self)
        self.b_clear_filters.setIcon(getIcon("edit-clear", 16, "svgz"))
        searchRow.addWidget(self.b_clear_filters)

        grid.addLayout(searchRow, 0, 0, 1, 3)

        # row 1..3: filters (toolbox) | table | info
        self._buildFilters()

        self.table = QTableWidget(0, _TABLE_COLUMNS, self)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setEditTriggers(_NO_EDIT_TRIGGERS)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(_SINGLE_SELECTION)
        self.table.setSelectionBehavior(_SELECT_ROWS)
        self.table.setWordWrap(False)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels(["", self.tr("Name"), self.tr("Label/Id/URI"),
                                              self.tr("Maker"), self.tr("Binary/Filename")])
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(True)
        hh.setMinimumSectionSize(24)
        self.table.setColumnWidth(TW_FAVORITE, 24)
        self.table.setColumnWidth(TW_NAME, 250)
        self.table.setColumnWidth(TW_LABEL, 200)
        self.table.setColumnWidth(TW_MAKER, 150)
        grid.addWidget(self.table, 1, 1, 3, 1)

        self._buildInfoPanel()
        grid.addWidget(self.tab_info, 1, 2, 3, 1)

        # row 4: status + buttons
        bottomRow = QHBoxLayout()
        self.label = QLabel(self.tr("(Number of Plugins go here)"), self)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bottomRow.addWidget(self.label)
        bottomRow.addStretch(1)

        self.b_add = QPushButton(self.tr("&Add Plugin"), self)
        self.b_add.setIcon(getIcon("list-add", 16, "svgz"))
        self.b_add.setEnabled(False)
        bottomRow.addWidget(self.b_add)

        self.b_cancel = QPushButton(self.tr("Cancel"), self)
        self.b_cancel.setIcon(getIcon("dialog-cancel", 16, "svgz"))
        bottomRow.addWidget(self.b_cancel)

        grid.addLayout(bottomRow, 4, 0, 1, 3)

    def _buildFilters(self):
        self.filterBox = QToolBox(self)

        # Format page
        pageFormat = QWidget(self)
        lf = QVBoxLayout(pageFormat)
        self.ch_internal = QCheckBox(self.tr("Internal"), self)
        self.ch_ladspa = QCheckBox("LADSPA", self)
        self.ch_dssi = QCheckBox("DSSI", self)
        self.ch_lv2 = QCheckBox("LV2", self)
        self.ch_vst = QCheckBox("VST2", self)
        self.ch_vst3 = QCheckBox("VST3", self)
        self.ch_clap = QCheckBox("CLAP", self)
        self.ch_au = QCheckBox("AU", self)
        self.ch_jsfx = QCheckBox("JSFX", self)
        self.ch_kits = QCheckBox(self.tr("Sound Kits"), self)
        for ch in (self.ch_internal, self.ch_ladspa, self.ch_dssi, self.ch_lv2, self.ch_vst, self.ch_vst3,
                   self.ch_clap, self.ch_au, self.ch_jsfx, self.ch_kits):
            lf.addWidget(ch)
        lf.addStretch(1)
        self.filterBox.addItem(pageFormat, self.tr("Format"))

        # Type page
        pageType = QWidget(self)
        lt = QVBoxLayout(pageType)
        self.ch_effects = QCheckBox(self.tr("Effects"), self)
        self.ch_instruments = QCheckBox(self.tr("Instruments"), self)
        self.ch_midi = QCheckBox(self.tr("MIDI Plugins"), self)
        self.ch_other = QCheckBox(self.tr("Other/Misc"), self)
        for ch in (self.ch_effects, self.ch_instruments, self.ch_midi, self.ch_other):
            lt.addWidget(ch)
        lt.addStretch(1)
        self.filterBox.addItem(pageType, self.tr("Type"))

        # Category page
        pageCat = QWidget(self)
        lc = QVBoxLayout(pageCat)
        self.ch_cat_all = QCheckBox(self.tr("All"), self)
        self.ch_cat_delay = QCheckBox(self.tr("Delay"), self)
        self.ch_cat_distortion = QCheckBox(self.tr("Distortion"), self)
        self.ch_cat_dynamics = QCheckBox(self.tr("Dynamics"), self)
        self.ch_cat_eq = QCheckBox(self.tr("EQ"), self)
        self.ch_cat_filter = QCheckBox(self.tr("Filter"), self)
        self.ch_cat_modulator = QCheckBox(self.tr("Modulator"), self)
        self.ch_cat_synth = QCheckBox(self.tr("Synth"), self)
        self.ch_cat_utility = QCheckBox(self.tr("Utility"), self)
        self.ch_cat_other = QCheckBox(self.tr("Other"), self)
        for ch in (self.ch_cat_all, self.ch_cat_delay, self.ch_cat_distortion, self.ch_cat_dynamics,
                   self.ch_cat_eq, self.ch_cat_filter, self.ch_cat_modulator, self.ch_cat_synth,
                   self.ch_cat_utility, self.ch_cat_other):
            lc.addWidget(ch)
        lc.addStretch(1)
        self.filterBox.addItem(pageCat, self.tr("Category"))

        # Architecture page
        pageArch = QWidget(self)
        la = QVBoxLayout(pageArch)
        self.ch_native = QCheckBox(self.tr("Native"), self)
        self.ch_bridged = QCheckBox(self.tr("Bridged"), self)
        self.ch_bridged_wine = QCheckBox(self.tr("Bridged (Wine)"), self)
        for ch in (self.ch_native, self.ch_bridged, self.ch_bridged_wine):
            la.addWidget(ch)
        la.addStretch(1)
        self.filterBox.addItem(pageArch, self.tr("Architecture"))

        # Requirements page (ported from tab_reqs)
        pageReq = QWidget(self)
        lr = QVBoxLayout(pageReq)
        self.ch_favorites = QCheckBox(self.tr("Favorites only"), self)
        self.ch_rtsafe = QCheckBox(self.tr("Real-time safe only"), self)
        self.ch_stereo = QCheckBox(self.tr("Stereo only"), self)
        self.ch_cv = QCheckBox(self.tr("With CV Ports"), self)
        self.ch_gui = QCheckBox(self.tr("With Custom GUI"), self)
        self.ch_inline_display = QCheckBox(self.tr("With Inline Display"), self)
        for ch in (self.ch_favorites, self.ch_rtsafe, self.ch_stereo, self.ch_cv, self.ch_gui,
                   self.ch_inline_display):
            lr.addWidget(ch)
        lr.addStretch(1)
        self.filterBox.addItem(pageReq, self.tr("Requirements"))

        self.filterBox.setCurrentIndex(0)
        self.filterBox.setMinimumWidth(150)
        self._grid_placeholder = self.filterBox
        self.layout().addWidget(self.filterBox, 1, 0, 3, 1)

    def _buildInfoPanel(self):
        self.tab_info = QTabWidget(self)
        self.tab_info.tabBar().hide()
        page = QWidget(self)
        infoLayout = QGridLayout(page)

        header = QLabel(self.tr("Information"), self)
        font = header.font()
        font.setBold(True)
        header.setFont(font)
        infoLayout.addWidget(header, 0, 0, 1, 2)

        self.l_format = QLabel("TextLabel")
        self.l_type = QLabel("TextLabel")
        self.l_arch = QLabel("TextLabel")
        self.l_id = QLabel("TextLabel")
        self.l_ains = QLabel("TextLabel")
        self.l_aouts = QLabel("TextLabel")
        self.l_cvins = QLabel("TextLabel")
        self.l_cvouts = QLabel("TextLabel")
        self.l_mins = QLabel("TextLabel")
        self.l_mouts = QLabel("TextLabel")
        self.l_pins = QLabel("TextLabel")
        self.l_pouts = QLabel("TextLabel")
        self.l_gui = QLabel("TextLabel")
        self.l_idisp = QLabel("TextLabel")
        self.l_bridged = QLabel("TextLabel")
        self.l_synth = QLabel("TextLabel")

        rows = [
            (self.tr("Format:"), self.l_format),
            (self.tr("Type:"), self.l_type),
            (self.tr("Architecture:"), self.l_arch),
            (self.tr("UniqueID:"), self.l_id),
            (self.tr("Audio Ins:"), self.l_ains),
            (self.tr("Audio Outs:"), self.l_aouts),
            (self.tr("CV Ins:"), self.l_cvins),
            (self.tr("CV Outs:"), self.l_cvouts),
            (self.tr("MIDI Ins:"), self.l_mins),
            (self.tr("MIDI Outs:"), self.l_mouts),
            (self.tr("Parameter Ins:"), self.l_pins),
            (self.tr("Parameter Outs:"), self.l_pouts),
            (self.tr("Has Custom GUI:"), self.l_gui),
            (self.tr("Has Inline Display:"), self.l_idisp),
            (self.tr("Is Bridged:"), self.l_bridged),
            (self.tr("Is Synth:"), self.l_synth),
        ]
        for i, (caption, value) in enumerate(rows, start=1):
            label = QLabel(caption)
            label.setAlignment(_ALIGN_RIGHT | getattr(Qt, "AlignVCenter",
                                                       getattr(Qt.AlignmentFlag, "AlignVCenter", 0)))
            infoLayout.addWidget(label, i, 0)
            infoLayout.addWidget(value, i, 1)

        self.tab_info.addTab(page, "")

    # ----------------------------------------------------------------------------------------------------
    # public API

    def getSelectedPluginInfo(self):
        return self.retPlugin

    def setPluginPath(self, ptype, path):
        if ptype in self.paths:
            self.paths[ptype] = path

    def exec(self):
        try:
            res = super().exec()
        except AttributeError:  # pragma: no cover - PyQt5
            res = super().exec_()
        return bool(res)

    # ----------------------------------------------------------------------------------------------------
    # QDialog overrides

    def done(self, r):
        if r == _qt_accepted() and self.table.currentRow() >= 0:
            item = self.table.item(self.table.currentRow(), TW_NAME)
            data = item.data(int(Qt.UserRole) + UR_PLUGIN_INFO) if item is not None else None
            if data is not None:
                info, _ = _bytesToInfo(bytes(data) if isinstance(data, QByteArray) else bytes(data))
                self.retPlugin = info or {}
            else:
                self.retPlugin = {}
        else:
            self.retPlugin = {}
        super().done(r)

    def showEvent(self, event):
        self.focusSearchFieldAndSelectAll()
        super().showEvent(event)

        if self._discovery["firstInit"]:
            self._discovery["firstInit"] = False

            self._refreshDialog = _PluginRefreshDialog(self)
            self._refreshDialog.b_start.setEnabled(False)
            self._refreshDialog.b_skip.setEnabled(True)
            self._refreshDialog.ch_updated.setChecked(True)
            self._refreshDialog.ch_invalid.setChecked(False)
            self._refreshDialog.group.setEnabled(False)
            self._refreshDialog.group_formats.hide()
            self._refreshDialog.progressBar.setFormat(self.tr("Starting initial discovery..."))
            self._refreshDialog.adjustSize()

            self._refreshDialog.b_skip.clicked.connect(self._refreshPluginsSkip)
            self._refreshDialog.finished.connect(lambda _r: self._refreshPluginsStop())

            self._addPluginsToTable()   # show instantly from cache
            self._timer.start()         # start background scan silently

    # ----------------------------------------------------------------------------------------------------
    # settings

    def _loadSettings(self):
        settings = _newSettings()

        geo = _getBytes(settings, "PluginDatabase/Geometry")
        if geo:
            self.restoreGeometry(QByteArray(geo))

        self.ch_effects.setChecked(_getBool(settings, "PluginDatabase/ShowEffects", True))
        self.ch_instruments.setChecked(_getBool(settings, "PluginDatabase/ShowInstruments", True))
        self.ch_midi.setChecked(_getBool(settings, "PluginDatabase/ShowMIDI", True))
        self.ch_other.setChecked(_getBool(settings, "PluginDatabase/ShowOther", True))
        self.ch_internal.setChecked(_getBool(settings, "PluginDatabase/ShowInternal", True))
        self.ch_ladspa.setChecked(_getBool(settings, "PluginDatabase/ShowLADSPA", True))
        self.ch_dssi.setChecked(_getBool(settings, "PluginDatabase/ShowDSSI", True))
        self.ch_lv2.setChecked(_getBool(settings, "PluginDatabase/ShowLV2", True))
        self.ch_vst.setChecked(_getBool(settings, "PluginDatabase/ShowVST2", True))
        self.ch_vst3.setChecked(_getBool(settings, "PluginDatabase/ShowVST3", True))
        self.ch_clap.setChecked(_getBool(settings, "PluginDatabase/ShowCLAP", True))
        if CARLA_OS_MAC:
            self.ch_au.setChecked(_getBool(settings, "PluginDatabase/ShowAU", True))
        self.ch_jsfx.setChecked(_getBool(settings, "PluginDatabase/ShowJSFX", True))
        self.ch_kits.setChecked(_getBool(settings, "PluginDatabase/ShowKits", True))
        self.ch_native.setChecked(_getBool(settings, "PluginDatabase/ShowNative", True))
        self.ch_bridged.setChecked(_getBool(settings, "PluginDatabase/ShowBridged", True))
        self.ch_bridged_wine.setChecked(_getBool(settings, "PluginDatabase/ShowBridgedWine", True))
        self.ch_favorites.setChecked(_getBool(settings, "PluginDatabase/ShowFavorites", False))
        self.ch_rtsafe.setChecked(_getBool(settings, "PluginDatabase/ShowRtSafe", False))
        self.ch_cv.setChecked(_getBool(settings, "PluginDatabase/ShowHasCV", False))
        self.ch_gui.setChecked(_getBool(settings, "PluginDatabase/ShowHasGUI", False))
        self.ch_inline_display.setChecked(_getBool(settings, "PluginDatabase/ShowHasInlineDisplay", False))
        self.ch_stereo.setChecked(_getBool(settings, "PluginDatabase/ShowStereoOnly", False))
        self.lineEdit.setText(_getStr(settings, "PluginDatabase/SearchText", ""))

        categories = _getStr(settings, "PluginDatabase/ShowCategory", "all")
        if categories == "all" or len(categories) < 2:
            self.ch_cat_all.setChecked(True)
            for ch in (self.ch_cat_delay, self.ch_cat_distortion, self.ch_cat_dynamics, self.ch_cat_eq,
                       self.ch_cat_filter, self.ch_cat_modulator, self.ch_cat_synth, self.ch_cat_utility,
                       self.ch_cat_other):
                ch.setChecked(False)
        else:
            self.ch_cat_all.setChecked(False)
            self.ch_cat_delay.setChecked(":delay:" in categories)
            self.ch_cat_distortion.setChecked(":distortion:" in categories)
            self.ch_cat_dynamics.setChecked(":dynamics:" in categories)
            self.ch_cat_eq.setChecked(":eq:" in categories)
            self.ch_cat_filter.setChecked(":filter:" in categories)
            self.ch_cat_modulator.setChecked(":modulator:" in categories)
            self.ch_cat_synth.setChecked(":synth:" in categories)
            self.ch_cat_utility.setChecked(":utility:" in categories)
            self.ch_cat_other.setChecked(":other:" in categories)

        tableGeometry = _getBytes(settings, "PluginDatabase/TableGeometry")
        hh = self.table.horizontalHeader()
        if tableGeometry:
            hh.restoreState(QByteArray(tableGeometry))
        else:
            self.table.setColumnWidth(TW_NAME, 250)
            self.table.setColumnWidth(TW_LABEL, 200)
            self.table.setColumnWidth(TW_MAKER, 150)
            self.table.sortByColumn(TW_NAME, Qt.AscendingOrder)

        hh.setSectionResizeMode(TW_FAVORITE, QHeaderView.Fixed)
        self.table.setColumnWidth(TW_FAVORITE, 24)
        self.table.setSortingEnabled(True)

        # favorites
        self.favorites = self._favoritesFromBytes(_getBytes(settings, "PluginListDialog/Favorites"))

        # load entire plugin cache
        for key in settings.allKeys():
            if not key.startswith("PluginCache/"):
                continue
            sha1 = key[12:]
            data = _getBytes(settings, key)
            if not data:
                self.cache[sha1] = []
                continue
            plist = _bytesToInfoList(data)
            self.cache[sha1] = plist
            for info in plist:
                self._pluginsAdd(info)

    def _saveSettings(self, *args):
        settings = _newSettings()

        settings.setValue("PluginDatabase/Geometry", self.saveGeometry())
        settings.setValue("PluginDatabase/TableGeometry", self.table.horizontalHeader().saveState())
        settings.setValue("PluginDatabase/ShowEffects", self.ch_effects.isChecked())
        settings.setValue("PluginDatabase/ShowInstruments", self.ch_instruments.isChecked())
        settings.setValue("PluginDatabase/ShowMIDI", self.ch_midi.isChecked())
        settings.setValue("PluginDatabase/ShowOther", self.ch_other.isChecked())
        settings.setValue("PluginDatabase/ShowInternal", self.ch_internal.isChecked())
        settings.setValue("PluginDatabase/ShowLADSPA", self.ch_ladspa.isChecked())
        settings.setValue("PluginDatabase/ShowDSSI", self.ch_dssi.isChecked())
        settings.setValue("PluginDatabase/ShowLV2", self.ch_lv2.isChecked())
        settings.setValue("PluginDatabase/ShowVST2", self.ch_vst.isChecked())
        settings.setValue("PluginDatabase/ShowVST3", self.ch_vst3.isChecked())
        settings.setValue("PluginDatabase/ShowCLAP", self.ch_clap.isChecked())
        settings.setValue("PluginDatabase/ShowAU", self.ch_au.isChecked())
        settings.setValue("PluginDatabase/ShowJSFX", self.ch_jsfx.isChecked())
        settings.setValue("PluginDatabase/ShowKits", self.ch_kits.isChecked())
        settings.setValue("PluginDatabase/ShowNative", self.ch_native.isChecked())
        settings.setValue("PluginDatabase/ShowBridged", self.ch_bridged.isChecked())
        settings.setValue("PluginDatabase/ShowBridgedWine", self.ch_bridged_wine.isChecked())
        settings.setValue("PluginDatabase/ShowFavorites", self.ch_favorites.isChecked())
        settings.setValue("PluginDatabase/ShowRtSafe", self.ch_rtsafe.isChecked())
        settings.setValue("PluginDatabase/ShowHasCV", self.ch_cv.isChecked())
        settings.setValue("PluginDatabase/ShowHasGUI", self.ch_gui.isChecked())
        settings.setValue("PluginDatabase/ShowHasInlineDisplay", self.ch_inline_display.isChecked())
        settings.setValue("PluginDatabase/ShowStereoOnly", self.ch_stereo.isChecked())
        settings.setValue("PluginDatabase/SearchText", self.lineEdit.text())

        if self.ch_cat_all.isChecked():
            settings.setValue("PluginDatabase/ShowCategory", "all")
        else:
            categories = ""
            if self.ch_cat_delay.isChecked():
                categories += ":delay"
            if self.ch_cat_distortion.isChecked():
                categories += ":distortion"
            if self.ch_cat_dynamics.isChecked():
                categories += ":dynamics"
            if self.ch_cat_eq.isChecked():
                categories += ":eq"
            if self.ch_cat_filter.isChecked():
                categories += ":filter"
            if self.ch_cat_modulator.isChecked():
                categories += ":modulator"
            if self.ch_cat_synth.isChecked():
                categories += ":synth"
            if self.ch_cat_utility.isChecked():
                categories += ":utility"
            if self.ch_cat_other.isChecked():
                categories += ":other"
            if categories:
                categories += ":"
            settings.setValue("PluginDatabase/ShowCategory", categories)

        settings.setValue("PluginListDialog/Favorites", self._favoritesToBytes(self.favorites))

    # ----------------------------------------------------------------------------------------------------
    # favorites serialization

    def _favoritesToBytes(self, favlist):
        out = bytearray()
        for fav in favlist:
            out += _FAV_HEADER.pack(int(fav["type"]) & 0xFFFF, int(fav["uniqueId"]) & 0xFFFFFFFFFFFFFFFF)
            out += (fav.get("filename") or "").encode("utf-8", errors="replace") + b"\0"
            out += (fav.get("label") or "").encode("utf-8", errors="replace") + b"\0"
        return QByteArray(bytes(out))

    def _favoritesFromBytes(self, data):
        if isinstance(data, QByteArray):
            data = bytes(data)
        favlist = []
        offset = 0
        while offset + _FAV_HEADER.size <= len(data):
            ptype, uniqueId = _FAV_HEADER.unpack_from(data, offset)
            offset += _FAV_HEADER.size

            def readStr():
                nonlocal offset
                end = data.find(b"\0", offset)
                if end < 0:
                    end = len(data)
                value = data[offset:end].decode("utf-8", errors="replace")
                offset = end + 1
                return value

            filename = readStr()
            label = readStr()
            if ptype == PLUGIN_NONE:
                break
            favlist.append({"type": ptype, "uniqueId": uniqueId, "filename": filename, "label": label})
        return favlist

    @staticmethod
    def _favoriteFromInfo(info):
        return {
            "type": int(info["type"]),
            "uniqueId": int(info["uniqueId"]),
            "filename": info["filename"],
            "label": info["label"],
        }

    def _isFavorite(self, info):
        fav = self._favoriteFromInfo(info)
        return fav in self.favorites

    # ----------------------------------------------------------------------------------------------------
    # plugin containers

    def _pluginsAdd(self, info):
        pinfo = info
        ptype = pinfo["type"]

        if ptype == PLUGIN_INTERNAL:
            vec = self._plugins["internal"]
        elif ptype == PLUGIN_LADSPA:
            vec = self._plugins["ladspa"]
        elif ptype == PLUGIN_DSSI:
            vec = self._plugins["dssi"]
        elif ptype == PLUGIN_LV2:
            vec = self._plugins["lv2"]
        elif ptype == PLUGIN_VST2:
            vec = self._plugins["vst2"]
        elif ptype == PLUGIN_VST3:
            vec = self._plugins["vst3"]
        elif ptype == PLUGIN_CLAP:
            vec = self._plugins["clap"]
        elif ptype == PLUGIN_AU:
            vec = self._plugins["au"]
        elif ptype == PLUGIN_JSFX:
            vec = self._plugins["jsfx"]
        elif ptype in (PLUGIN_SF2, PLUGIN_SFZ):
            vec = self._plugins["kits"]
        else:
            return False

        for existing in vec:
            if (existing["filename"] == pinfo["filename"]
                    and existing["uniqueId"] == pinfo["uniqueId"]
                    and existing["name"] == pinfo["name"]):
                return True

        vec.append(pinfo)
        return True

    # ----------------------------------------------------------------------------------------------------
    # discovery

    def _libraryFolder(self):
        folder = get_library_folder()
        if not folder:
            try:
                from carla_shared import gCarla
                folder = os.path.dirname(gCarla.utils.lib._name)
            except Exception:
                folder = ""
        return folder or ""

    def _restartDiscoveryTool(self):
        d = self._discovery
        d["btype"] = BINARY_NATIVE
        d["ptype"] = PLUGIN_NONE
        tool = os.path.join(self._libraryFolder(), "carla-discovery-native")
        if CARLA_OS_WIN:
            tool += ".exe"
        d["tool"] = tool

    def _formatEnabled(self, name):
        r = self._refreshDialog
        if r is None:
            return True
        if not r.group_formats.isVisible():
            return True
        return getattr(r, "ch_" + name).isChecked()

    def _orderedCandidates(self):
        d = self._discovery
        btype = d["btype"]
        paths = self.paths
        isNative = btype == BINARY_NATIVE

        candidates = [
            (PLUGIN_INTERNAL, "", self.tr("internal plugins"), isNative),
            (PLUGIN_LADSPA, paths.get(PLUGIN_LADSPA, ""), self.tr("LADSPA plugins"),
             self._formatEnabled("ladspa")),
            (PLUGIN_DSSI, paths.get(PLUGIN_DSSI, ""), self.tr("DSSI plugins"),
             self._formatEnabled("dssi")),
            (PLUGIN_LV2, paths.get(PLUGIN_LV2, ""), self.tr("LV2 plugins"),
             isNative and bool(paths.get(PLUGIN_LV2, "")) and self._formatEnabled("lv2")),
            (PLUGIN_VST2, paths.get(PLUGIN_VST2, ""), self.tr("VST2 plugins"),
             self._formatEnabled("vst2")),
            (PLUGIN_VST3, paths.get(PLUGIN_VST3, ""), self.tr("VST3 plugins"),
             self._formatEnabled("vst3")),
            (PLUGIN_CLAP, paths.get(PLUGIN_CLAP, ""), self.tr("CLAP plugins"),
             self._formatEnabled("clap")),
        ]
        if CARLA_OS_MAC:
            candidates.append((PLUGIN_AU, paths.get(PLUGIN_AU, ""), self.tr("AU plugins"),
                               self._formatEnabled("au")))
        candidates += [
            (PLUGIN_JSFX, paths.get(PLUGIN_JSFX, ""), self.tr("JSFX plugins"),
             isNative and bool(paths.get(PLUGIN_JSFX, "")) and self._formatEnabled("jsfx")),
            (PLUGIN_SF2, paths.get(PLUGIN_SF2, ""), self.tr("SF2 kits"),
             isNative and bool(paths.get(PLUGIN_SF2, "")) and self._formatEnabled("sf2")),
            (PLUGIN_SFZ, paths.get(PLUGIN_SFZ, ""), self.tr("SFZ kits"),
             isNative and bool(paths.get(PLUGIN_SFZ, "")) and self._formatEnabled("sfz")),
        ]
        return candidates

    def _discoveryPickNext(self):
        d = self._discovery
        candidates = self._orderedCandidates()

        start = 0
        if d["ptype"] != PLUGIN_NONE:
            for i, (ptype, _p, _t, _ok) in enumerate(candidates):
                if ptype == d["ptype"]:
                    start = i + 1
                    break

        for i in range(start, len(candidates)):
            ptype, path, text, ok = candidates[i]
            if ok:
                return ptype, path, text

        # exhausted this tool, try the next bridge tool if allowed
        if self._nextTool():
            return self._discoveryPickNext()

        return None

    def _nextTool(self):
        d = self._discovery

        if d["handle"] is not None:
            d["handle"].stop()
            d["handle"] = None

        if not d["usePluginBridges"]:
            return False

        folder = self._libraryFolder()

        if not CARLA_OS_WIN:
            if not CARLA_OS_MAC and d["btype"] == BINARY_NATIVE:
                d["btype"] = BINARY_POSIX32
                d["ptype"] = PLUGIN_NONE
                d["tool"] = os.path.join(folder, "carla-discovery-posix32")
                if os.path.isfile(d["tool"]):
                    return True

            if not d["useWineBridges"]:
                return False

            if CARLA_OS_64BIT and d["btype"] in (BINARY_NATIVE, BINARY_POSIX32):
                d["btype"] = BINARY_WIN64
                d["ptype"] = PLUGIN_NONE
                d["tool"] = os.path.join(folder, "carla-discovery-win64.exe")
                if os.path.isfile(d["tool"]):
                    return True

            if d["btype"] != BINARY_WIN32:
                d["btype"] = BINARY_WIN32
                d["ptype"] = PLUGIN_NONE
                d["tool"] = os.path.join(folder, "carla-discovery-win32.exe")
                if os.path.isfile(d["tool"]):
                    return True

            return False

        # Windows host build
        if CARLA_OS_64BIT and d["btype"] == BINARY_NATIVE:
            d["btype"] = BINARY_WIN32
            d["ptype"] = PLUGIN_NONE
            d["tool"] = os.path.join(folder, "carla-discovery-win32.exe")
            if os.path.isfile(d["tool"]):
                return True

        return False

    def _discoveryStep(self):
        d = self._discovery

        if d["handle"] is not None:
            if not d["handle"].idle():
                d["handle"].stop()
                d["handle"] = None
            return

        pick = self._discoveryPickNext()
        if pick is None:
            self._refreshPluginsStop()
            return

        ptype, path, text = pick
        d["ptype"] = ptype
        self.label.setText(text)
        if self._refreshDialog is not None:
            self._refreshDialog.progressBar.setFormat(text)

        runner = PluginDiscovery(self._addPluginInfo, self._checkPluginCache)
        d["handle"] = runner
        runner.start(d["tool"], d["btype"], ptype, path)

    # ----------------------------------------------------------------------------------------------------
    # discovery callbacks

    def _addPluginInfo(self, info, sha1sum):
        if info is None:
            if sha1sum is not None:
                settings = _newSettings()
                settings.setValue("PluginCache/%s" % sha1sum, QByteArray())
                self.cache[sha1sum] = []
            return

        pinfo = {
            "build": int(info["btype"]),
            "type": int(info["ptype"]),
            "hints": int(info["metadata"]["hints"]),
            "uniqueId": int(info["uniqueId"]),
            "audioIns": int(info["io"]["audioIns"]),
            "audioOuts": int(info["io"]["audioOuts"]),
            "cvIns": int(info["io"]["cvIns"]),
            "cvOuts": int(info["io"]["cvOuts"]),
            "midiIns": int(info["io"]["midiIns"]),
            "midiOuts": int(info["io"]["midiOuts"]),
            "parameterIns": int(info["io"]["parameterIns"]),
            "parameterOuts": int(info["io"]["parameterOuts"]),
            "category": getPluginCategoryAsString(int(info["metadata"]["category"])),
            "filename": info["filename"] or "",
            "name": info["metadata"]["name"] or "",
            "label": info["label"] or "",
            "maker": info["metadata"]["maker"] or "",
        }

        if sha1sum is not None:
            settings = _newSettings()
            key = "PluginCache/%s" % sha1sum
            if sha1sum in self.cache:
                data = _getBytes(settings, key)
            else:
                data = b""
            data += _infoToBytes(pinfo)
            settings.setValue(key, QByteArray(data))
            self.cache.setdefault(sha1sum, []).append(pinfo)

        self._pluginsAdd(pinfo)

    def _checkPluginCache(self, filename, sha1sum):
        if filename and self._refreshDialog is not None:
            self._refreshDialog.progressBar.setFormat(filename)

        if sha1sum not in self.cache:
            return False

        plist = self.cache[sha1sum]
        if not plist:
            return self._discovery["ignoreCache"] or not self._discovery["checkInvalid"]

        if not filename or plist[0]["filename"] != filename:
            self.cache.pop(sha1sum, None)
            return False

        for info in plist:
            self._pluginsAdd(info)
        return True

    # ----------------------------------------------------------------------------------------------------
    # refresh

    def _refreshPlugins(self):
        self._refreshPluginsStop()

        self._refreshDialog = _PluginRefreshDialog(self)
        self._refreshDialog.b_start.clicked.connect(self._refreshPluginsStart)
        self._refreshDialog.b_skip.clicked.connect(self._refreshPluginsSkip)
        self._refreshDialog.finished.connect(lambda _r: self._refreshPluginsStop())
        self._refreshDialog.exec()

    def _refreshPluginsStart(self):
        self._plugins["internal"] = []
        self._plugins["ladspa"] = []
        self._plugins["dssi"] = []
        self._plugins["lv2"] = []
        self._plugins["vst2"] = []
        self._plugins["vst3"] = []
        self._plugins["clap"] = []
        self._plugins["au"] = []
        self._plugins["jsfx"] = []
        self._plugins["kits"] = []

        r = self._refreshDialog
        if r is not None:
            r.b_start.setEnabled(False)
            r.b_skip.setEnabled(True)
            self._discovery["ignoreCache"] = r.ch_all.isChecked()
            self._discovery["checkInvalid"] = r.ch_invalid.isChecked()
        if self._discovery["ignoreCache"]:
            self.cache.clear()

        self._restartDiscoveryTool()

        if not self._timer.isActive():
            self._timer.start()

    def _refreshPluginsStop(self):
        d = self._discovery

        if d["handle"] is not None:
            d["handle"].stop()
            d["handle"] = None

        r = self._refreshDialog
        self._refreshDialog = None
        if r is not None:
            r.close()

        if self._timer.isActive():
            self._timer.stop()
            self._addPluginsToTable()

    def _refreshPluginsSkip(self):
        d = self._discovery
        if d["handle"] is not None:
            d["handle"].skip()

    # ----------------------------------------------------------------------------------------------------
    # table

    def _addPluginsToTable(self):
        self.table.setSortingEnabled(False)
        self.table.clearContents()

        total = sum(len(v) for v in self._plugins.values())
        self.table.setRowCount(total)

        order = ["internal", "ladspa", "dssi", "lv2", "vst2", "vst3", "clap", "au", "jsfx", "kits"]
        self._lastTableWidgetIndex = 0
        for key in order:
            for info in self._plugins[key]:
                self._addPluginToTable(info)

        # label summary
        self.label.setText(
            self.tr("Have %1 Internal, %2 LADSPA, %3 DSSI, %4 LV2, %5 VST2, %6 VST3, %7 CLAP and %8 JSFX plugins, plus %9 Sound Kits")
            .replace("%1", str(len(self._plugins["internal"])))
            .replace("%2", str(len(self._plugins["ladspa"])))
            .replace("%3", str(len(self._plugins["dssi"])))
            .replace("%4", str(len(self._plugins["lv2"])))
            .replace("%5", str(len(self._plugins["vst2"])))
            .replace("%6", str(len(self._plugins["vst3"])))
            .replace("%7", str(len(self._plugins["clap"])))
            .replace("%8", str(len(self._plugins["jsfx"])))
            .replace("%9", str(len(self._plugins["kits"])))
        )

        self.table.setSortingEnabled(True)

        self._checkFilters()
        self._checkPlugin(self.table.currentRow())

    def _addPluginToTable(self, info):
        index = self._lastTableWidgetIndex
        self._lastTableWidgetIndex += 1

        isFav = self._isFavorite(info)

        itemFav = QTableWidgetItem()
        itemFav.setCheckState(_qt_checkstate(isFav))
        itemFav.setText(" ")
        self.table.setItem(index, TW_FAVORITE, itemFav)

        self.table.setItem(index, TW_NAME, QTableWidgetItem(info["name"]))
        self.table.setItem(index, TW_LABEL, QTableWidgetItem(info["label"]))
        self.table.setItem(index, TW_MAKER, QTableWidgetItem(info["maker"]))
        self.table.setItem(index, TW_BINARY, QTableWidgetItem(os.path.basename(info["filename"])))

        pluginText = (info["name"] + info["label"] + info["maker"] + info["filename"]).lower()

        itemName = self.table.item(index, TW_NAME)
        itemName.setData(int(Qt.UserRole) + UR_PLUGIN_INFO, QByteArray(_infoToBytes(info)))
        itemName.setData(int(Qt.UserRole) + UR_SEARCH_TEXT, pluginText)

    # ----------------------------------------------------------------------------------------------------
    # slots

    def _cellClicked(self, row, column):
        if column != TW_FAVORITE:
            return

        item = self.table.item(row, TW_NAME)
        if item is None:
            return
        data = item.data(int(Qt.UserRole) + UR_PLUGIN_INFO)
        info, _ = _bytesToInfo(bytes(data)) if data is not None else (None, 0)
        if info is None:
            return

        fav = self._favoriteFromInfo(info)
        isFavorite = fav in self.favorites
        checked = _checkstate_checked(self.table.item(row, TW_FAVORITE))

        if checked:
            if not isFavorite:
                self.favorites.append(fav)
        elif isFavorite:
            self.favorites = [f for f in self.favorites if f != fav]

        settings = _newSettings()
        settings.setValue("PluginListDialog/Favorites", self._favoritesToBytes(self.favorites))

    def _cellDoubleClicked(self, _row, column):
        if column != TW_FAVORITE:
            self.done(_qt_accepted())

    def focusSearchFieldAndSelectAll(self):
        self.lineEdit.setFocus()
        self.lineEdit.selectAll()

    def _checkFilters(self):
        text = self.lineEdit.text().lower()

        hideEffects = not self.ch_effects.isChecked()
        hideInstruments = not self.ch_instruments.isChecked()
        hideMidi = not self.ch_midi.isChecked()
        hideOther = not self.ch_other.isChecked()

        hideInternal = not self.ch_internal.isChecked()
        hideLadspa = not self.ch_ladspa.isChecked()
        hideDSSI = not self.ch_dssi.isChecked()
        hideLV2 = not self.ch_lv2.isChecked()
        hideVST2 = not self.ch_vst.isChecked()
        hideVST3 = not self.ch_vst3.isChecked()
        hideCLAP = not self.ch_clap.isChecked()
        hideAU = not self.ch_au.isChecked()
        hideJSFX = not self.ch_jsfx.isChecked()
        hideKits = not self.ch_kits.isChecked()

        hideNative = not self.ch_native.isChecked()
        hideBridged = not self.ch_bridged.isChecked()
        hideBridgedWine = not self.ch_bridged_wine.isChecked()

        hideNonFavs = self.ch_favorites.isChecked()
        hideNonRtSafe = self.ch_rtsafe.isChecked()
        hideNonCV = self.ch_cv.isChecked()
        hideNonGui = self.ch_gui.isChecked()
        hideNonIDisp = self.ch_inline_display.isChecked()
        hideNonStereo = self.ch_stereo.isChecked()

        if CARLA_OS_WIN:
            nativeBins = (BINARY_WIN32, BINARY_WIN64) if CARLA_OS_64BIT else (BINARY_WIN32, BINARY_NONE)
            wineBins = (BINARY_NONE, BINARY_NONE)
        elif CARLA_OS_MAC:
            nativeBins = (BINARY_POSIX64, BINARY_NONE)
            wineBins = (BINARY_WIN32, BINARY_WIN64)
        else:
            nativeBins = (BINARY_POSIX32, BINARY_POSIX64)
            wineBins = (BINARY_WIN32, BINARY_WIN64)

        for i in range(self.table.rowCount()):
            item = self.table.item(i, TW_NAME)
            if item is None:
                continue
            data = item.data(int(Qt.UserRole) + UR_PLUGIN_INFO)
            info, _ = _bytesToInfo(bytes(data)) if data is not None else (None, 0)
            if info is None:
                self.table.hideRow(i)
                continue

            ptext = item.data(int(Qt.UserRole) + UR_SEARCH_TEXT)
            ptext = str(ptext) if ptext is not None else ""

            aIns = info["audioIns"]
            aOuts = info["audioOuts"]
            cvIns = info["cvIns"]
            cvOuts = info["cvOuts"]
            mIns = info["midiIns"]
            mOuts = info["midiOuts"]
            phints = info["hints"]
            ptype = info["type"]
            categ = info["category"]

            isSynth = bool(phints & PLUGIN_IS_SYNTH)
            isEffect = aIns > 0 and aOuts > 0 and not isSynth
            isMidi = aIns == 0 and aOuts == 0 and mIns > 0 and mOuts > 0
            isKit = ptype in (PLUGIN_SF2, PLUGIN_SFZ)
            isOther = not (isEffect or isSynth or isMidi or isKit)
            isNative = info["build"] == BINARY_NATIVE
            isRtSafe = bool(phints & PLUGIN_IS_RTSAFE)
            isStereo = (aIns == 2 and aOuts == 2) or (isSynth and aOuts == 2)
            hasCV = cvIns + cvOuts > 0
            hasGui = bool(phints & PLUGIN_HAS_CUSTOM_UI)
            hasIDisp = bool(phints & PLUGIN_HAS_INLINE_DISPLAY)
            isBridged = (not isNative) and (info["build"] in nativeBins)
            isBridgedWine = (not isNative) and (info["build"] in wineBins)

            def hasText():
                for token in text.strip().split(" "):
                    if token in ptext:
                        return True
                return False

            if hideEffects and isEffect:
                self.table.hideRow(i)
            elif hideInstruments and isSynth:
                self.table.hideRow(i)
            elif hideMidi and isMidi:
                self.table.hideRow(i)
            elif hideOther and isOther:
                self.table.hideRow(i)
            elif hideKits and isKit:
                self.table.hideRow(i)
            elif hideInternal and ptype == PLUGIN_INTERNAL:
                self.table.hideRow(i)
            elif hideLadspa and ptype == PLUGIN_LADSPA:
                self.table.hideRow(i)
            elif hideDSSI and ptype == PLUGIN_DSSI:
                self.table.hideRow(i)
            elif hideLV2 and ptype == PLUGIN_LV2:
                self.table.hideRow(i)
            elif hideVST2 and ptype == PLUGIN_VST2:
                self.table.hideRow(i)
            elif hideVST3 and ptype == PLUGIN_VST3:
                self.table.hideRow(i)
            elif hideCLAP and ptype == PLUGIN_CLAP:
                self.table.hideRow(i)
            elif hideAU and ptype == PLUGIN_AU:
                self.table.hideRow(i)
            elif hideJSFX and ptype == PLUGIN_JSFX:
                self.table.hideRow(i)
            elif hideNative and isNative:
                self.table.hideRow(i)
            elif hideBridged and isBridged:
                self.table.hideRow(i)
            elif hideBridgedWine and isBridgedWine:
                self.table.hideRow(i)
            elif hideNonRtSafe and not isRtSafe:
                self.table.hideRow(i)
            elif hideNonCV and not hasCV:
                self.table.hideRow(i)
            elif hideNonGui and not hasGui:
                self.table.hideRow(i)
            elif hideNonIDisp and not hasIDisp:
                self.table.hideRow(i)
            elif hideNonStereo and not isStereo:
                self.table.hideRow(i)
            elif text and not hasText():
                self.table.hideRow(i)
            elif hideNonFavs and not self._isFavorite(info):
                self.table.hideRow(i)
            elif (self.ch_cat_all.isChecked()
                  or (self.ch_cat_delay.isChecked() and categ == "delay")
                  or (self.ch_cat_distortion.isChecked() and categ == "distortion")
                  or (self.ch_cat_dynamics.isChecked() and categ == "dynamics")
                  or (self.ch_cat_eq.isChecked() and categ == "eq")
                  or (self.ch_cat_filter.isChecked() and categ == "filter")
                  or (self.ch_cat_modulator.isChecked() and categ == "modulator")
                  or (self.ch_cat_synth.isChecked() and categ == "synth")
                  or (self.ch_cat_utility.isChecked() and categ == "utility")
                  or (self.ch_cat_other.isChecked() and categ == "other")):
                self.table.showRow(i)
            else:
                self.table.hideRow(i)

    def _checkFiltersCategoryAll(self, clicked=False):
        notClicked = not clicked
        for ch in (self.ch_cat_delay, self.ch_cat_distortion, self.ch_cat_dynamics, self.ch_cat_eq,
                   self.ch_cat_filter, self.ch_cat_modulator, self.ch_cat_synth, self.ch_cat_utility,
                   self.ch_cat_other):
            ch.setChecked(notClicked)
        self._checkFilters()

    def _checkFiltersCategorySpecific(self, clicked=False):
        if clicked:
            self.ch_cat_all.setChecked(False)
        elif not (self.ch_cat_delay.isChecked() or self.ch_cat_distortion.isChecked()
                  or self.ch_cat_dynamics.isChecked() or self.ch_cat_eq.isChecked()
                  or self.ch_cat_filter.isChecked() or self.ch_cat_modulator.isChecked()
                  or self.ch_cat_synth.isChecked() or self.ch_cat_utility.isChecked()
                  or self.ch_cat_other.isChecked()):
            self.ch_cat_all.setChecked(True)
        self._checkFilters()

    def _clearFilters(self):
        def setCheckedNoSignal(w, checked):
            w.blockSignals(True)
            w.setChecked(checked)
            w.blockSignals(False)

        for ch in (self.ch_internal, self.ch_ladspa, self.ch_dssi, self.ch_lv2, self.ch_vst,
                   self.ch_vst3, self.ch_clap, self.ch_jsfx, self.ch_kits,
                   self.ch_instruments, self.ch_effects, self.ch_midi, self.ch_other,
                   self.ch_native):
            setCheckedNoSignal(ch, True)

        setCheckedNoSignal(self.ch_bridged, False)
        setCheckedNoSignal(self.ch_bridged_wine, False)
        setCheckedNoSignal(self.ch_favorites, False)
        setCheckedNoSignal(self.ch_rtsafe, False)
        setCheckedNoSignal(self.ch_stereo, False)
        setCheckedNoSignal(self.ch_cv, False)
        setCheckedNoSignal(self.ch_gui, False)
        setCheckedNoSignal(self.ch_inline_display, False)

        if self.ch_au.isEnabled():
            setCheckedNoSignal(self.ch_au, True)

        setCheckedNoSignal(self.ch_cat_all, True)
        for ch in (self.ch_cat_delay, self.ch_cat_distortion, self.ch_cat_dynamics, self.ch_cat_eq,
                   self.ch_cat_filter, self.ch_cat_modulator, self.ch_cat_synth, self.ch_cat_utility,
                   self.ch_cat_other):
            setCheckedNoSignal(ch, False)

        self.lineEdit.blockSignals(True)
        self.lineEdit.clear()
        self.lineEdit.blockSignals(False)

        self._checkFilters()

    def _checkPlugin(self, row):
        if row >= 0:
            self.b_add.setEnabled(True)

            item = self.table.item(row, TW_NAME)
            data = item.data(int(Qt.UserRole) + UR_PLUGIN_INFO) if item is not None else None
            info, _ = _bytesToInfo(bytes(data)) if data is not None else (None, 0)
            if info is None:
                info = {"hints": 0, "audioIns": 0, "audioOuts": 0, "midiIns": 0, "midiOuts": 0,
                        "build": BINARY_NONE, "type": PLUGIN_NONE, "uniqueId": 0, "cvIns": 0, "cvOuts": 0,
                        "parameterIns": 0, "parameterOuts": 0}

            isSynth = bool(info["hints"] & PLUGIN_IS_SYNTH)
            isEffect = info["audioIns"] > 0 and info["audioOuts"] > 0 and not isSynth
            isMidi = info["audioIns"] == 0 and info["audioOuts"] == 0 and info["midiIns"] > 0 and info["midiOuts"] > 0

            if isSynth:
                ptypeStr = self.tr("Instrument")
            elif isEffect:
                ptypeStr = self.tr("Effect")
            elif isMidi:
                ptypeStr = self.tr("MIDI Plugin")
            else:
                ptypeStr = self.tr("Other")

            if info["build"] == BINARY_NATIVE:
                parch = self.tr("Native")
            elif info["build"] == BINARY_POSIX32:
                parch = "posix32"
            elif info["build"] == BINARY_POSIX64:
                parch = "posix64"
            elif info["build"] == BINARY_WIN32:
                parch = "win32"
            elif info["build"] == BINARY_WIN64:
                parch = "win64"
            elif info["build"] == BINARY_OTHER:
                parch = self.tr("Other")
            else:
                parch = self.tr("Unknown")

            self.l_format.setText(getPluginTypeAsString(info["type"]))
            self.l_type.setText(ptypeStr)
            self.l_arch.setText(parch)
            self.l_id.setText(str(info["uniqueId"]))
            self.l_ains.setText(str(info["audioIns"]))
            self.l_aouts.setText(str(info["audioOuts"]))
            self.l_cvins.setText(str(info["cvIns"]))
            self.l_cvouts.setText(str(info["cvOuts"]))
            self.l_mins.setText(str(info["midiIns"]))
            self.l_mouts.setText(str(info["midiOuts"]))
            self.l_pins.setText(str(info["parameterIns"]))
            self.l_pouts.setText(str(info["parameterOuts"]))
            self.l_gui.setText(self.tr("Yes") if info["hints"] & PLUGIN_HAS_CUSTOM_UI else self.tr("No"))
            self.l_idisp.setText(self.tr("Yes") if info["hints"] & PLUGIN_HAS_INLINE_DISPLAY else self.tr("No"))
            self.l_bridged.setText(self.tr("Yes") if info["hints"] & PLUGIN_IS_BRIDGE else self.tr("No"))
            self.l_synth.setText(self.tr("Yes") if isSynth else self.tr("No"))
        else:
            self.b_add.setEnabled(False)
            for label in (self.l_format, self.l_type, self.l_arch, self.l_id, self.l_ains, self.l_aouts,
                          self.l_cvins, self.l_cvouts, self.l_mins, self.l_mouts, self.l_pins, self.l_pouts,
                          self.l_gui, self.l_idisp, self.l_bridged, self.l_synth):
                label.setText("---")

    # ----------------------------------------------------------------------------------------------------
    # CSV export

    def appendToCSV(self):
        out = []

        def appendVec(vec):
            for info in vec:
                out.append("%d|%d|%d|%s|%s|%s|%s|%s|%d\n" % (
                    int(info["build"]), int(info["type"]), int(info["hints"]),
                    info["category"], info["filename"], info["name"], info["label"],
                    info["maker"], int(info["uniqueId"])))

        order = ["internal", "ladspa", "dssi", "lv2", "vst2", "vst3", "clap", "au", "jsfx", "kits"]
        for key in order:
            appendVec(self._plugins[key])

        return "".join(out)

# ------------------------------------------------------------------------------------------------------------
# Module-level API (drop-in replacement for the native carla_frontend wrappers)

def createPluginListDialog(parent, hostSettings):
    return PyPluginListDialog(parent, hostSettings)


def destroyPluginListDialog(dialog):
    if dialog is None:
        return
    dialog.close()
    dialog.setParent(None)
    dialog.deleteLater()


def setPluginListDialogPath(dialog, ptype, path):
    if dialog is None:
        return
    dialog.setPluginPath(ptype, path)


def execPluginListDialog(dialog):
    if dialog is None:
        return None
    if dialog.exec():
        return dialog.getSelectedPluginInfo()
    return None


def getCachedPluginsCsv(dialog):
    if dialog is None:
        return ""
    return dialog.appendToCSV()

# ------------------------------------------------------------------------------------------------------------
