#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

"""Verification Demo for Clara's Centralized Theming Engine.

Demonstrates:
1. Direct ingestion of a theme defined ONLY with Base16 color tokens (no structural properties).
2. Automatic fallback of geometry (radii, spacing, padding) from centralized System Core Defaults.
3. Component primitives bound directly to semantic variable tokens (headers, buttons, pills, inputs, cards, rack, table).
4. Live automatic grayscale luminance flipping between Dark and Light modes (base00 <-> base07).
"""

import os
import sys

# Ensure frontend imports resolve
_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.dirname(_HERE)
for d in (_FRONTEND_DIR, _HERE):
    if d not in sys.path:
        sys.path.insert(0, d)

from qt_compat import (
    QApplication,
    QColor,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    Qt,
)
from styles.engine import ThemeEngine
from styles.theme_manager import _load_base_primitives

# ------------------------------------------------------------------------------------------------------------
# 1. Pure Base16 Theme Definition (COLORS ONLY, zero structural or geometry rules)
# ------------------------------------------------------------------------------------------------------------

RAW_BASE16_SOLARIZED = {
    "name": "Solarized",
    "base00": "#002b36",  # darkest background
    "base01": "#073642",  # surface background
    "base02": "#586e75",  # selection / hover
    "base03": "#657b83",  # borders
    "base04": "#839496",  # muted text
    "base05": "#93a1a1",  # secondary text
    "base06": "#eee8d5",  # light foreground
    "base07": "#fdf6e3",  # lightest foreground
    "base08": "#dc322f",  # red
    "base09": "#cb4b16",  # orange
    "base0A": "#b58900",  # yellow
    "base0B": "#859900",  # green
    "base0C": "#2aa198",  # cyan
    "base0D": "#268bd2",  # blue (accent)
    "base0E": "#6c71c4",  # purple
    "base0F": "#d33682",  # magenta
}

class ThemeVerificationDialog(QDialog):
    """Interactive demo showcasing Base16 ingestion and light/dark scale flipping."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clara Theme Engine - Base16 Ingestion & Primitives Verification")
        self.resize(780, 680)

        self.engine = ThemeEngine(base_primitives_template=_load_base_primitives())
        self.current_mode = "dark"

        self._build_ui()
        self._apply_current_mode()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        # Top Bar: Mode Toggle
        top_bar = QHBoxLayout()
        self.lbl_header = QLabel("Theme Engine Primitives Verification", self)
        self.lbl_header.setProperty("role", "header")

        self.btn_toggle_mode = QPushButton("🌙 Mode: Dark (Click to Flip)", self)
        self.btn_toggle_mode.clicked.connect(self._toggle_mode)

        top_bar.addWidget(self.lbl_header)
        top_bar.addStretch(1)
        top_bar.addWidget(self.btn_toggle_mode)
        root_layout.addLayout(top_bar)

        self.lbl_subtitle = QLabel(
            "Defined strictly with raw Base16 color tokens. Radii, spacing, and component rules cascade from system defaults.",
            self,
        )
        self.lbl_subtitle.setProperty("role", "subtitle")
        root_layout.addWidget(self.lbl_subtitle)

        # Section 1: Button Primitives
        sec1 = QHBoxLayout()
        sec1.setSpacing(10)
        btn_default = QPushButton("Default Button", self)
        btn_primary = QPushButton("Primary Accent", self)
        btn_primary.setProperty("primary", True)
        btn_subtle = QPushButton("Subtle Flat", self)
        btn_subtle.setProperty("flat", True)
        btn_danger = QPushButton("Danger Action", self)
        btn_danger.setProperty("danger", True)

        for b in (btn_default, btn_primary, btn_subtle, btn_danger):
            sec1.addWidget(b)
        root_layout.addLayout(sec1)

        # Section 2: Filter Pills & Badges (Dynamic auto-tint)
        sec2 = QHBoxLayout()
        sec2.setSpacing(8)
        lbl_pills = QLabel("Pills & Badges:", self)
        lbl_pills.setProperty("role", "title")
        sec2.addWidget(lbl_pills)

        pill_all = QPushButton("All Formats", self)
        pill_all.setProperty("pill", True)
        pill_all.setCheckable(True)
        pill_all.setChecked(True)

        pill_clap = QPushButton("CLAP", self)
        pill_clap.setProperty("pill", True)
        pill_clap.setCheckable(True)
        pill_clap.setChecked(False)

        pill_vst3 = QPushButton("VST3", self)
        pill_vst3.setProperty("pill", True)
        pill_vst3.setCheckable(True)
        pill_vst3.setChecked(False)

        badge = QLabel("LV2", self)
        badge.setObjectName("infoBadge")

        tag = QLabel("Stereo", self)
        tag.setObjectName("infoTag")

        for w in (pill_all, pill_clap, pill_vst3, badge, tag):
            sec2.addWidget(w)
        sec2.addStretch(1)
        root_layout.addLayout(sec2)

        # Section 3: Form Input Field
        sec3 = QHBoxLayout()
        self.input_search = QLineEdit(self)
        self.input_search.setPlaceholderText("Search plugins or inspect focus rings...")
        sec3.addWidget(self.input_search)
        root_layout.addLayout(sec3)

        # Section 4: Modular Card Primitive & Rack Unit Capsule
        sec4 = QHBoxLayout()
        sec4.setSpacing(14)

        # Modular Card
        card = QFrame(self)
        card.setObjectName("cardPluginItem")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(4)
        c_title = QLabel("Dexed FM Synth", card)
        c_title.setObjectName("cardPluginName")
        c_sub = QLabel("Digital Suburban • Modular Card", card)
        c_sub.setObjectName("infoMaker")
        card_layout.addWidget(c_title)
        card_layout.addWidget(c_sub)
        sec4.addWidget(card, 1)

        # Rack Unit Capsule
        rack = QFrame(self)
        rack.setObjectName("rackPluginItem")
        rack_layout = QHBoxLayout(rack)
        rack_layout.setContentsMargins(12, 6, 12, 6)
        r_title = QLabel("Dragonfly Reverb", rack)
        r_title.setObjectName("rackPluginName")
        r_sub = QLabel("Michael Willis • Rack Unit Capsule", rack)
        r_sub.setObjectName("infoCategory")
        rack_layout.addWidget(r_title)
        rack_layout.addStretch(1)
        rack_layout.addWidget(r_sub)
        sec4.addWidget(rack, 1)

        root_layout.addLayout(sec4)

        # Section 5: Modern Table Primitive
        self.table = QTableWidget(3, 4, self)
        self.table.setHorizontalHeaderLabels(["★", "Name", "Type", "Author"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 36)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setAlternatingRowColors(True)

        rows = [
            ("★", "Helm Synthesizer", "CLAP", "Matt Tytel"),
            ("☆", "ZLEqualizer", "LV2", "ZL Audio"),
            ("★", "ChowCentaur", "VST3", "Chowdhury DSP"),
        ]
        for row_idx, (star, name, ptype, author) in enumerate(rows):
            item_star = QTableWidgetItem(star)
            item_star.setTextAlignment(Qt.AlignCenter)
            item_star.setForeground(QColor("#eed49f" if star == "★" else "#839496"))
            self.table.setItem(row_idx, 0, item_star)
            self.table.setItem(row_idx, 1, QTableWidgetItem(name))
            self.table.setItem(row_idx, 2, QTableWidgetItem(ptype))
            self.table.setItem(row_idx, 3, QTableWidgetItem(author))

        root_layout.addWidget(self.table, 1)

    def _toggle_mode(self):
        self.current_mode = "light" if self.current_mode == "dark" else "dark"
        self._apply_current_mode()

    def _apply_current_mode(self):
        icon = "☀️ Mode: Light (Click to Flip)" if self.current_mode == "light" else "🌙 Mode: Dark (Click to Flip)"
        self.btn_toggle_mode.setText(icon)

        # Compile QSS dynamically using Base16 Solarized definition
        qss = self.engine.compile_qss(RAW_BASE16_SOLARIZED, mode=self.current_mode)
        self.setStyleSheet(qss)


def main():
    app = QApplication(sys.argv)
    dlg = ThemeVerificationDialog()
    dlg.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
