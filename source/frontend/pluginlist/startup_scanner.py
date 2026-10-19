#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2026 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.dirname(_HERE)
for _d in (_FRONTEND_DIR, _HERE):
    if _d not in sys.path:
        sys.path.insert(0, _d)

from qt_compat import (
    QObject,
    QThread,
    pyqtSignal,
)

try:
    from PyQt6.QtCore import QByteArray
except ImportError:
    from PyQt5.QtCore import QByteArray

from carla_backend import (
    BINARY_NATIVE,
    BINARY_NONE,
    CARLA_OS_MAC,
    CARLA_OS_WIN,
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
)
from carla_utils import getPluginCategoryAsString
from carla_shared import log_carla
from pluginlist.discovery_py import PluginDiscovery, get_library_folder
from pluginlist.pluginlistdialog_py import (
    _bytesToInfoList,
    _defaultPluginPaths,
    _getBytes,
    _infoToBytes,
    _newSettings,
)


class PluginScannerThread(QThread):
    """
    Non-blocking, low-priority background thread for plugin scanning & delta discovery.
    Runs discovery out-of-process via carla-discovery-native without blocking the UI or audio thread.
    """
    pluginDiscovered = pyqtSignal(dict, str)   # pinfo, sha1
    statusChanged = pyqtSignal(str)            # human status e.g. "Scanning VST3 plugins..."
    fileChanged = pyqtSignal(str)              # current filename being analyzed
    scanFinished = pyqtSignal(int)             # newly discovered plugin count

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paths = _defaultPluginPaths()
        self.ignoreCache = False
        self.checkInvalid = False
        self._stopRequested = False
        self._currentRunner = None
        self._discoveredCount = 0

    def configure(self, paths=None, ignoreCache=False, checkInvalid=False):
        if paths:
            self.paths.update(paths)
        self.ignoreCache = ignoreCache
        self.checkInvalid = checkInvalid

    def requestStop(self):
        self._stopRequested = True
        runner = self._currentRunner
        if runner is not None:
            try:
                runner.stop()
            except Exception:
                pass

    def _libraryFolder(self):
        folder = get_library_folder()
        if not folder:
            try:
                from carla_shared import gCarla
                folder = os.path.dirname(gCarla.utils.lib._name)
            except Exception:
                folder = ""
        return folder or ""

    def _discoveryTool(self):
        tool = os.path.join(self._libraryFolder(), "carla-discovery-native")
        if CARLA_OS_WIN:
            tool += ".exe"
        return tool

    def _orderedCandidates(self):
        paths = self.paths
        candidates = [
            (PLUGIN_INTERNAL, "", "internal plugins", True),
            (PLUGIN_LADSPA, paths.get(PLUGIN_LADSPA, ""), "LADSPA plugins", bool(paths.get(PLUGIN_LADSPA, ""))),
            (PLUGIN_DSSI, paths.get(PLUGIN_DSSI, ""), "DSSI plugins", bool(paths.get(PLUGIN_DSSI, ""))),
            (PLUGIN_LV2, paths.get(PLUGIN_LV2, ""), "LV2 plugins", bool(paths.get(PLUGIN_LV2, ""))),
            (PLUGIN_VST2, paths.get(PLUGIN_VST2, ""), "VST2 plugins", bool(paths.get(PLUGIN_VST2, ""))),
            (PLUGIN_VST3, paths.get(PLUGIN_VST3, ""), "VST3 plugins", bool(paths.get(PLUGIN_VST3, ""))),
            (PLUGIN_CLAP, paths.get(PLUGIN_CLAP, ""), "CLAP plugins", bool(paths.get(PLUGIN_CLAP, ""))),
        ]
        if CARLA_OS_MAC:
            candidates.append((PLUGIN_AU, paths.get(PLUGIN_AU, ""), "AU plugins", bool(paths.get(PLUGIN_AU, ""))))
        candidates += [
            (PLUGIN_JSFX, paths.get(PLUGIN_JSFX, ""), "JSFX plugins", bool(paths.get(PLUGIN_JSFX, ""))),
            (PLUGIN_SF2, paths.get(PLUGIN_SF2, ""), "SF2 kits", bool(paths.get(PLUGIN_SF2, ""))),
            (PLUGIN_SFZ, paths.get(PLUGIN_SFZ, ""), "SFZ kits", bool(paths.get(PLUGIN_SFZ, ""))),
        ]
        return candidates

    def run(self):
        self._stopRequested = False
        self._discoveredCount = 0
        tool = self._discoveryTool()

        if not os.path.isfile(tool):
            self.statusChanged.emit("Discovery tool not found")
            self.scanFinished.emit(0)
            return

        settings = _newSettings()
        cached_keys = set(k[12:] for k in settings.allKeys() if k.startswith("PluginCache/"))

        def checkCacheCallback(filename, sha1):
            if filename:
                self.fileChanged.emit(os.path.basename(filename))
            if self.ignoreCache:
                return False
            if sha1 in cached_keys:
                return not self.checkInvalid
            return False

        def infoCallback(info, sha1sum):
            if self._stopRequested:
                return
            if info is None:
                if sha1sum is not None:
                    s = _newSettings()
                    s.setValue("PluginCache/%s" % sha1sum, QByteArray())
                    cached_keys.add(sha1sum)
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
                s = _newSettings()
                key = "PluginCache/%s" % sha1sum
                data = _getBytes(s, key) if sha1sum in cached_keys else b""
                data += _infoToBytes(pinfo)
                s.setValue(key, QByteArray(data))
                cached_keys.add(sha1sum)

            self._discoveredCount += 1
            self.pluginDiscovered.emit(pinfo, sha1sum or "")

        candidates = self._orderedCandidates()
        for ptype, path, label, enabled in candidates:
            if self._stopRequested:
                break
            if not enabled and ptype != PLUGIN_INTERNAL:
                continue

            self.statusChanged.emit(f"Scanning {label}...")
            log_carla(f"[SCANNER] Starting discovery for {label} (path='{path}')", level="info")

            runner = PluginDiscovery(infoCallback, checkCacheCallback)
            self._currentRunner = runner

            if runner.start(tool, BINARY_NATIVE, ptype, path):
                while runner.idle():
                    if self._stopRequested:
                        runner.stop()
                        break
                    # Gentle yield so Qt main event loop and audio engine experience zero jitter
                    time.sleep(0.003)
            log_carla(f"[SCANNER] Finished discovery for {label}", level="info")

            self._currentRunner = None

        self.statusChanged.emit("Scan complete" if not self._stopRequested else "Scan stopped")
        self.scanFinished.emit(self._discoveredCount)


_GLOBAL_SCANNER = None


def getGlobalScanner():
    global _GLOBAL_SCANNER
    if _GLOBAL_SCANNER is None:
        _GLOBAL_SCANNER = PluginScannerThread()
    return _GLOBAL_SCANNER
