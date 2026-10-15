#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Pure-PyQt/Python bindings for the Carla plugin discovery C API.
#
# This talks to the NON-Qt native backend library `libcarla_utils` (via gCarla.utils.lib), exposing:
#   carla_plugin_discovery_start / idle / skip / stop / set_option
# plus the matching ctypes structures from source/backend/CarlaUtils.h.
#
# It intentionally does NOT reimplement plugin discovery: all real work happens inside the native helper
# executable (`carla-discovery-native`, etc.) which is spawned by libcarla_utils.
# ------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------
# Imports (ctypes)

from ctypes import (
    CFUNCTYPE,
    POINTER,
    Structure,
    c_bool,
    c_char_p,
    c_int,
    c_uint,
    c_uint32,
    c_uint64,
    c_void_p,
    py_object,
)

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from carla_backend import charPtrToString, c_enum

# ------------------------------------------------------------------------------------------------------------
# ctypes structures (must match source/backend/CarlaUtils.h field order exactly)

# CarlaPluginDiscoveryMetadata
class CarlaPluginDiscoveryMetadata(Structure):
    _fields_ = [
        ("name", c_char_p),
        ("maker", c_char_p),
        ("category", c_enum),   # PluginCategory
        ("hints", c_uint),
    ]

# CarlaPluginDiscoveryIO
class CarlaPluginDiscoveryIO(Structure):
    _fields_ = [
        ("audioIns", c_uint32),
        ("audioOuts", c_uint32),
        ("cvIns", c_uint32),
        ("cvOuts", c_uint32),
        ("midiIns", c_uint32),
        ("midiOuts", c_uint32),
        ("parameterIns", c_uint32),
        ("parameterOuts", c_uint32),
    ]

# CarlaPluginDiscoveryInfo
class CarlaPluginDiscoveryInfo(Structure):
    _fields_ = [
        ("btype", c_enum),      # BinaryType
        ("ptype", c_enum),      # PluginType
        ("filename", c_char_p),
        ("label", c_char_p),
        ("uniqueId", c_uint64),
        ("metadata", CarlaPluginDiscoveryMetadata),
        ("io", CarlaPluginDiscoveryIO),
    ]

# CarlaCachedPluginInfo (kept here so this module is self-contained)
class CarlaCachedPluginInfo(Structure):
    _fields_ = [
        ("valid", c_bool),
        ("category", c_enum),
        ("hints", c_uint),
        ("audioIns", c_uint32),
        ("audioOuts", c_uint32),
        ("cvIns", c_uint32),
        ("cvOuts", c_uint32),
        ("midiIns", c_uint32),
        ("midiOuts", c_uint32),
        ("parameterIns", c_uint32),
        ("parameterOuts", c_uint32),
        ("name", c_char_p),
        ("label", c_char_p),
        ("maker", c_char_p),
        ("copyright", c_char_p),
    ]

# ------------------------------------------------------------------------------------------------------------
# Callback types
#
# The first argument ("void* callbackPtr") is passed through as a Python object, matching what we hand to
# carla_plugin_discovery_start().

DiscoveryCallback = CFUNCTYPE(None, py_object, POINTER(CarlaPluginDiscoveryInfo), c_char_p)
CheckCacheCallback = CFUNCTYPE(c_bool, py_object, c_char_p, c_char_p)

# ------------------------------------------------------------------------------------------------------------
# Library access / prototype setup

_lib = None
_setup_done = False


def get_library():
    """Return the loaded libcarla_utils cdll (gCarla.utils.lib), importing lazily to avoid import cycles."""
    global _lib
    if _lib is None:
        from carla_shared import gCarla
        if gCarla.utils is None:
            raise RuntimeError("discovery_py: gCarla.utils is not available (libcarla_utils not loaded)")
        _lib = gCarla.utils.lib
    return _lib


def _setup(lib):
    global _setup_done
    if _setup_done:
        return

    lib.carla_plugin_discovery_start.argtypes = (
        c_char_p,          # discoveryTool
        c_enum,            # bttype (BinaryType)
        c_enum,            # ptype (PluginType)
        c_char_p,          # pluginPath
        DiscoveryCallback, # discoveryCb
        CheckCacheCallback,# checkCacheCb (may be null)
        py_object,         # callbackPtr
    )
    lib.carla_plugin_discovery_start.restype = c_void_p

    lib.carla_plugin_discovery_idle.argtypes = (c_void_p,)
    lib.carla_plugin_discovery_idle.restype = c_bool

    lib.carla_plugin_discovery_skip.argtypes = (c_void_p,)
    lib.carla_plugin_discovery_skip.restype = None

    lib.carla_plugin_discovery_stop.argtypes = (c_void_p,)
    lib.carla_plugin_discovery_stop.restype = None

    lib.carla_plugin_discovery_set_option.argtypes = (c_enum, c_int, c_char_p)
    lib.carla_plugin_discovery_set_option.restype = None

    if hasattr(lib, "carla_get_library_folder"):
        lib.carla_get_library_folder.argtypes = ()
        lib.carla_get_library_folder.restype = c_char_p

    if hasattr(lib, "carla_get_cached_plugin_count"):
        lib.carla_get_cached_plugin_count.argtypes = (c_enum, c_char_p)
        lib.carla_get_cached_plugin_count.restype = c_uint

    if hasattr(lib, "carla_get_cached_plugin_info"):
        lib.carla_get_cached_plugin_info.argtypes = (c_enum, c_uint)
        lib.carla_get_cached_plugin_info.restype = POINTER(CarlaCachedPluginInfo)

    _setup_done = True


# ------------------------------------------------------------------------------------------------------------
# Conversions

def discoveryInfoToDict(info):
    """Convert a CarlaPluginDiscoveryInfo structure into a plain python dict (raw enum ints preserved)."""
    return {
        "btype": int(info.btype),
        "ptype": int(info.ptype),
        "filename": charPtrToString(info.filename),
        "label": charPtrToString(info.label),
        "uniqueId": int(info.uniqueId),
        "metadata": {
            "name": charPtrToString(info.metadata.name),
            "maker": charPtrToString(info.metadata.maker),
            "category": int(info.metadata.category),
            "hints": int(info.metadata.hints),
        },
        "io": {
            "audioIns": int(info.io.audioIns),
            "audioOuts": int(info.io.audioOuts),
            "cvIns": int(info.io.cvIns),
            "cvOuts": int(info.io.cvOuts),
            "midiIns": int(info.io.midiIns),
            "midiOuts": int(info.io.midiOuts),
            "parameterIns": int(info.io.parameterIns),
            "parameterOuts": int(info.io.parameterOuts),
        },
    }

# ------------------------------------------------------------------------------------------------------------
# Global discovery options

def set_option(option, value, valueStr=None):
    """Set a global plugin discovery option. `option` is an ENGINE_OPTION_* constant."""
    lib = get_library()
    _setup(lib)
    if valueStr is not None:
        valueStr = valueStr.encode("utf-8")
    lib.carla_plugin_discovery_set_option(int(option), int(value), valueStr)


def get_library_folder():
    """Return the folder where libcarla_utils (and the discovery helpers) reside."""
    lib = get_library()
    _setup(lib)
    if not hasattr(lib, "carla_get_library_folder"):
        return None
    return charPtrToString(lib.carla_get_library_folder())

# ------------------------------------------------------------------------------------------------------------
# Incremental discovery runner (used by the dialog with a QTimer)

class PluginDiscovery:
    """
    Manages a single carla_plugin_discovery_* session.

    infoCallback(info, sha1) is invoked for each plugin (info is a dict) and for each binary that turned
    out to have no plugins (info is None, sha1 is set).
    checkCacheCallback(filename, sha1) -> bool is optional; when it returns True the native side skips
    scanning that binary.
    """

    def __init__(self, infoCallback, checkCacheCallback=None):
        self._infoCallback = infoCallback
        self._checkCacheCallback = checkCacheCallback

        # Keep strong references to the C callbacks for the lifetime of this object.
        self._infoCb = DiscoveryCallback(self._onInfo)
        self._checkCacheCb = CheckCacheCallback(self._onCheckCache) if checkCacheCallback else CheckCacheCallback()

        self.handle = None

    # -- C callbacks --------------------------------------------------------------------------------------

    def _onInfo(self, _ptr, infoPtr, sha1Ptr):
        sha1 = charPtrToString(sha1Ptr)

        if not infoPtr:
            info = None
        else:
            info = discoveryInfoToDict(infoPtr.contents)

        self._infoCallback(info, sha1)

    def _onCheckCache(self, _ptr, filenamePtr, sha1Ptr):
        sha1 = charPtrToString(sha1Ptr)
        if sha1 is None:
            return False
        filename = charPtrToString(filenamePtr)
        return bool(self._checkCacheCallback(filename, sha1))

    # -- lifecycle ----------------------------------------------------------------------------------------

    def start(self, tool, btype, ptype, path):
        lib = get_library()
        _setup(lib)

        self.stop()

        toolB = tool.encode("utf-8") if tool is not None else None
        pathB = path.encode("utf-8") if path is not None else None

        self.handle = lib.carla_plugin_discovery_start(
            toolB, int(btype), int(ptype), pathB,
            self._infoCb, self._checkCacheCb, self,
        )
        return bool(self.handle)

    def idle(self):
        if self.handle is None:
            return False
        lib = get_library()
        _setup(lib)
        return bool(lib.carla_plugin_discovery_idle(self.handle))

    def skip(self):
        if self.handle is None:
            return
        lib = get_library()
        _setup(lib)
        lib.carla_plugin_discovery_skip(self.handle)

    def stop(self):
        if self.handle is None:
            return
        lib = get_library()
        _setup(lib)
        lib.carla_plugin_discovery_stop(self.handle)
        self.handle = None

# ------------------------------------------------------------------------------------------------------------
# Blocking convenience helper

def run_discovery(tool, btype, ptype, path, infoCallback, checkCacheCallback=None):
    """
    Run discovery for one format to completion, blocking until done.
    Returns True if a session was started (there was something to scan), else False.
    """
    runner = PluginDiscovery(infoCallback, checkCacheCallback)
    if not runner.start(tool, btype, ptype, path):
        return False

    while runner.idle():
        pass

    runner.stop()
    return True

# ------------------------------------------------------------------------------------------------------------
