#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

import sys
import os
import re
from datetime import datetime
from qt_config import qt as qt_config
if qt_config == 5:
    from PyQt5.QtCore import QObject, pyqtSignal
else:
    from PyQt6.QtCore import QObject, pyqtSignal

# Import rich if available, with graceful fallback
try:
    from rich.console import Console
    from rich.theme import Theme
    from rich.text import Text

    _custom_theme = Theme({
        "debug": "dim cyan",
        "info": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "critical": "bold white on red",
        "timestamp": "dim white",
        "tag_app": "bold magenta",
        "tag_engine": "bold cyan",
        "tag_patchbay": "bold blue",
        "tag_plugin": "bold green",
        "tag_session": "bold yellow",
        "tag_canvas": "bold bright_magenta",
        "tag_backend": "bold red",
    })
    _rich_console = Console(theme=_custom_theme)
    HAVE_RICH = True
except ImportError:
    _rich_console = None
    HAVE_RICH = False

LOG_LEVEL_DEBUG = 10
LOG_LEVEL_INFO = 20
LOG_LEVEL_WARNING = 30
LOG_LEVEL_ERROR = 40
LOG_LEVEL_CRITICAL = 50

LEVEL_NAMES = {
    LOG_LEVEL_DEBUG: "DEBUG",
    LOG_LEVEL_INFO: "INFO",
    LOG_LEVEL_WARNING: "WARNING",
    LOG_LEVEL_ERROR: "ERROR",
    LOG_LEVEL_CRITICAL: "CRITICAL",
}

NAME_TO_LEVEL = {
    "DEBUG": LOG_LEVEL_DEBUG,
    "INFO": LOG_LEVEL_INFO,
    "WARNING": LOG_LEVEL_WARNING,
    "WARN": LOG_LEVEL_WARNING,
    "ERROR": LOG_LEVEL_ERROR,
    "CRITICAL": LOG_LEVEL_CRITICAL,
}

# Standard tags known throughout the app
KNOWN_TAGS = [
    "APP",
    "ENGINE",
    "PATCHBAY",
    "PLUGIN",
    "SESSION",
    "CANVAS",
    "BACKEND",
]

class LogEntry:
    __slots__ = ("timestamp", "level", "tag", "message", "raw_text")

    def __init__(self, level, tag, message, raw_text=""):
        self.timestamp = datetime.now()
        self.level = level
        self.tag = tag.upper().strip("[] ") if tag else "APP"
        self.message = message
        self.raw_text = raw_text or f"[{self.tag}] {message}"

    def formatted_ui(self):
        time_str = self.timestamp.strftime("%H:%M:%S")
        lvl_str = LEVEL_NAMES.get(self.level, "INFO")
        return f"[{time_str}] [{lvl_str}] [{self.tag}] {self.message}"

class CarlaLogger(QObject):
    logAdded = pyqtSignal(object)  # Emits LogEntry

    def __init__(self):
        super().__init__()
        self.console_enabled = True
        self.min_level = LOG_LEVEL_INFO
        self.whitelist = set()  # if non-empty, only these tags shown
        self.blacklist = set()  # these tags hidden
        self.history = []       # all LogEntry objects stored
        self.max_history = 5000

    def parse_cli_args(self, args=None):
        if args is None:
            args = sys.argv[1:]

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--log-level" and i + 1 < len(args):
                lvl_str = args[i + 1].upper()
                if lvl_str in NAME_TO_LEVEL:
                    self.min_level = NAME_TO_LEVEL[lvl_str]
                i += 1
            elif arg == "--log-whitelist" and i + 1 < len(args):
                tags = [t.strip().upper() for t in args[i + 1].split(",") if t.strip()]
                self.whitelist.update(tags)
                i += 1
            elif arg == "--log-blacklist" and i + 1 < len(args):
                tags = [t.strip().upper() for t in args[i + 1].split(",") if t.strip()]
                self.blacklist.update(tags)
                i += 1
            elif arg == "--no-console-log":
                self.console_enabled = False
            elif arg == "--console-log":
                self.console_enabled = True
            i += 1

    def is_tag_active(self, tag):
        tag = tag.upper()
        if self.whitelist and tag not in self.whitelist:
            return False
        if tag in self.blacklist:
            return False
        return True

    def should_display(self, entry):
        if entry.level < self.min_level:
            return False
        return self.is_tag_active(entry.tag)

    def log(self, level, tag, message):
        entry = LogEntry(level, tag, message)
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Output to terminal if enabled
        if self.console_enabled and self.should_display(entry):
            self._print_terminal(entry)

        # Emit to UI
        self.logAdded.emit(entry)

    def _print_terminal(self, entry):
        lvl_name = LEVEL_NAMES.get(entry.level, "INFO")
        time_str = entry.timestamp.strftime("%H:%M:%S")

        if HAVE_RICH and _rich_console is not None:
            style_name = lvl_name.lower()
            tag_style = f"tag_{entry.tag.lower()}"
            if tag_style not in _custom_theme.styles:
                tag_style = "tag_app"
            text = Text()
            text.append(f"[{time_str}] ", style="timestamp")
            text.append(f"[{lvl_name}] ", style=style_name)
            text.append(f"[{entry.tag}] ", style=tag_style)
            text.append(f"{entry.message}")
            _rich_console.print(text)
        else:
            print(f"[{time_str}] [{lvl_name}] [{entry.tag}] {entry.message}")

    def debug(self, tag, message):
        self.log(LOG_LEVEL_DEBUG, tag, message)

    def info(self, tag, message):
        self.log(LOG_LEVEL_INFO, tag, message)

    def warning(self, tag, message):
        self.log(LOG_LEVEL_WARNING, tag, message)

    def error(self, tag, message):
        self.log(LOG_LEVEL_ERROR, tag, message)

    def critical(self, tag, message):
        self.log(LOG_LEVEL_CRITICAL, tag, message)

    def log_raw_string(self, text):
        """Parse raw incoming string from legacy logs and classify tag/level"""
        if not text:
            return

        level = LOG_LEVEL_INFO
        tag = "APP"
        clean_text = text

        # Strip ANSI escape sequences if any
        ansi_regex = re.compile(r'\x1b\[[0-9;]*m')
        clean_text = ansi_regex.sub('', clean_text).strip()

        # Check for error / warning keywords
        upper_text = clean_text.upper()
        if "ASSERTION FAILURE" in upper_text:
            level = LOG_LEVEL_ERROR
            tag = "BACKEND"
        elif "ERROR" in upper_text or "CRITICAL" in upper_text or "FAIL" in upper_text:
            level = LOG_LEVEL_ERROR
        elif "WARN" in upper_text:
            level = LOG_LEVEL_WARNING
        elif "DEBUG" in upper_text:
            level = LOG_LEVEL_DEBUG

        # Look for [carla] prefix (e.g. from backend assertions / logging)
        if clean_text.startswith("[carla]"):
            tag = "BACKEND"
            clean_text = clean_text[7:].strip()
        else:
            # Look for general [TAG] pattern at the start
            m = re.match(r"^\[([A-Za-z0-9_\-]+)\]\s*(.*)$", clean_text)
            if m:
                tag_candidate = m.group(1).upper()
                if tag_candidate in KNOWN_TAGS or tag_candidate not in ("CARLA",):
                    tag = tag_candidate
                clean_text = m.group(2)
            elif "ENGINE" in upper_text:
                tag = "ENGINE"
            elif "PATCH" in upper_text or "CANVAS" in upper_text:
                tag = "PATCHBAY"
            elif "PLUGIN" in upper_text or "SFIZZ" in upper_text or "VST" in upper_text:
                tag = "PLUGIN"
            elif "AUTOSAVE" in upper_text or "SESSION" in upper_text:
                tag = "SESSION"

        self.log(level, tag, clean_text)

# Singleton global instance
logger = CarlaLogger()
