#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)
# ------------------------------------------------------------------------------------------------------------
import re

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)
# ------------------------------------------------------------------------------------------------------------
from carla_backend import *
from carla_shared import *
from carla_widgets import *
from patchcanvas import patchcanvas

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)
# ------------------------------------------------------------------------------------------------------------
from qt_compat import (
    QApplication,
    QColor,
    QCursor,
    QEvent,
    QFont,
    QFontDatabase,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMouseEvent,
    QObject,
    QPainterPathStroker,
    QPoint,
    QPointF,
    QPushButton,
    QRect,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)

# ------------------------------------------------------------------------------------------------------------
# Stereo Autowiring and Disconnect Helpers
# ------------------------------------------------------------------------------------------------------------


def findStereoPartner(target_port, candidate_ports):
    target_name = target_port.port_name

    # 1. Single character difference at same index where one is L/l and other is R/r
    for cand in candidate_ports:
        if cand.port_id == target_port.port_id:
            continue
        c_name = cand.port_name
        if len(c_name) == len(target_name):
            diffs = [
                (i, target_name[i], c_name[i])
                for i in range(len(target_name))
                if target_name[i] != c_name[i]
            ]
            if len(diffs) == 1:
                c1, c2 = diffs[0][1].upper(), diffs[0][2].upper()
                if (c1, c2) in [("L", "R"), ("R", "L")]:
                    return cand

    # 2. Single character difference at same index where one is 1 and other is 2
    for cand in candidate_ports:
        if cand.port_id == target_port.port_id:
            continue
        c_name = cand.port_name
        if len(c_name) == len(target_name):
            diffs = [
                (i, target_name[i], c_name[i])
                for i in range(len(target_name))
                if target_name[i] != c_name[i]
            ]
            if len(diffs) == 1:
                c1, c2 = diffs[0][1], diffs[0][2]
                if (c1, c2) in [("1", "2"), ("2", "1")]:
                    return cand

    # 3. Substring 'left' vs 'right' (case-insensitive)
    for cand in candidate_ports:
        if cand.port_id == target_port.port_id:
            continue
        c_name = cand.port_name
        if (
            re.sub(r"(?i)\bleft\b", "right", target_name.lower()) == c_name.lower()
            or re.sub(r"(?i)\bright\b", "left", target_name.lower()) == c_name.lower()
        ):
            return cand

    return None


def autoConnectStereoPair(gOut, pOut, gIn, pIn):
    try:
        port_list = patchcanvas.canvas.port_list
        src_port = None
        dst_port = None
        for p in port_list:
            if p.group_id == gOut and p.port_id == pOut:
                src_port = p
            elif p.group_id == gIn and p.port_id == pIn:
                dst_port = p

        if src_port and dst_port and src_port.port_type == dst_port.port_type:
            src_cands = [
                p
                for p in port_list
                if p.group_id == gOut
                and p.port_mode == src_port.port_mode
                and p.port_type == src_port.port_type
            ]
            dst_cands = [
                p
                for p in port_list
                if p.group_id == gIn
                and p.port_mode == dst_port.port_mode
                and p.port_type == dst_port.port_type
            ]

            src_partner = findStereoPartner(src_port, src_cands)
            dst_partner = findStereoPartner(dst_port, dst_cands)

            if src_partner and dst_partner:
                log_carla(
                    f"carla_canvas: Stereo auto-wire (Alt): {gOut}:{src_partner.port_id} ('{src_partner.port_name}') -> {gIn}:{dst_partner.port_id} ('{dst_partner.port_name}')"
                )
                gCarla.gui.host.patchbay_connect(
                    gCarla.gui.fExternalPatchbay,
                    gOut,
                    src_partner.port_id,
                    gIn,
                    dst_partner.port_id,
                )
    except Exception as e:
        log_carla(f"carla_canvas: Stereo auto-wire error: {e}")


def findStereoPartnerConnection(connectionId):
    try:
        conn_info = gCarla.gui.fConnections.get(connectionId)
        if not conn_info:
            return None
        gOut, pOut, gIn, pIn = conn_info
        port_list = patchcanvas.canvas.port_list
        src_port = None
        dst_port = None
        for p in port_list:
            if p.group_id == gOut and p.port_id == pOut:
                src_port = p
            elif p.group_id == gIn and p.port_id == pIn:
                dst_port = p

        if src_port and dst_port and src_port.port_type == dst_port.port_type:
            src_cands = [
                p
                for p in port_list
                if p.group_id == gOut
                and p.port_mode == src_port.port_mode
                and p.port_type == src_port.port_type
            ]
            dst_cands = [
                p
                for p in port_list
                if p.group_id == gIn
                and p.port_mode == dst_port.port_mode
                and p.port_type == dst_port.port_type
            ]

            src_partner = findStereoPartner(src_port, src_cands)
            dst_partner = findStereoPartner(dst_port, dst_cands)

            if src_partner and dst_partner:
                for cid, (cgOut, cpOut, cgIn, cpIn) in gCarla.gui.fConnections.items():
                    if (
                        cid != connectionId
                        and cgOut == gOut
                        and cpOut == src_partner.port_id
                        and cgIn == gIn
                        and cpIn == dst_partner.port_id
                    ):
                        return cid
    except Exception as e:
        log_carla(f"carla_canvas: findStereoPartnerConnection error: {e}")
    return None


# ------------------------------------------------------------------------------------------------------------
# Patchbay Help Overlay Widget
# ------------------------------------------------------------------------------------------------------------


class PatchbayHelpOverlay(QFrame):
    """An unobtrusive, expandable cheat-sheet floating on the lower right of the patchbay canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("patchbay_help_overlay")
        self._expanded = False

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(4)

        # Header Widget (Title + Collapse button)
        self._headerWidget = QWidget(self)
        headerLayout = QHBoxLayout(self._headerWidget)
        headerLayout.setContentsMargins(4, 0, 2, 2)
        headerLayout.setSpacing(6)

        self._lblTitle = QLabel("Canvas Controls", self._headerWidget)
        self._lblTitle.setStyleSheet(
            "color: #89b4fa; font-weight: bold; font-size: 11px;"
        )

        self._btnCollapse = QPushButton("▼", self._headerWidget)
        self._btnCollapse.setFixedSize(18, 18)
        self._btnCollapse.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #a6adc8;
                font-weight: bold;
                font-size: 10px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        self._btnCollapse.clicked.connect(self.toggleExpanded)

        headerLayout.addWidget(self._lblTitle)
        headerLayout.addStretch()
        headerLayout.addWidget(self._btnCollapse)
        self._layout.addWidget(self._headerWidget)

        # Content Label (shortcuts table)
        self._lblContent = QLabel(self)
        self._lblContent.setText("""
            <table style="color: #cdd6f4; font-size: 10px; line-height: 145%;">
              <tr><td style="color: #f9e2af; font-weight: bold; padding-right: 6px;">V:</td><td>Marquee Select Mode</td></tr>
              <tr><td style="color: #94e2d5; font-weight: bold; padding-right: 6px;">H / Space:</td><td>Hand / Pan Mode</td></tr>
              <tr><td style="color: #cba6f7; font-weight: bold; padding-right: 6px;">Q / Esc:</td><td>Pointer (Default)</td></tr>
              <tr><td style="color: #89b4fa; font-weight: bold; padding-right: 6px;">Drag Port:</td><td>Connect wire</td></tr>
              <tr><td style="color: #fab387; font-weight: bold; padding-right: 6px;">Alt + Drag:</td><td>Auto-wire stereo pair</td></tr>
              <tr><td style="color: #a6e3a1; font-weight: bold; padding-right: 6px;">Drag past edge:</td><td>Auto-scroll canvas</td></tr>
              <tr><td style="color: #f38ba8; font-weight: bold; padding-right: 6px;">Alt / Mid-Click:</td><td>Disconnect cable/port</td></tr>
              <tr><td style="color: #eba0ac; font-weight: bold; padding-right: 6px;">Shift + Click:</td><td>Alt disconnect</td></tr>
              <tr><td style="color: #cba6f7; font-weight: bold; padding-right: 6px;">Ctrl + Click:</td><td>Multi-select node</td></tr>
              <tr><td style="color: #b4befe; font-weight: bold; padding-right: 6px;">Dbl-Click Node:</td><td>Open Custom UI</td></tr>
              <tr><td style="color: #89dceb; font-weight: bold; padding-right: 6px;">Ctrl + Scroll:</td><td>Zoom in / out</td></tr>
              <tr><td style="color: #f5c2e7; font-weight: bold; padding-right: 6px;">Right-Click:</td><td>Context menu / arrange</td></tr>
            </table>
        """)
        self._layout.addWidget(self._lblContent)

        # Collapsed Trigger Button (the circle with "?")
        self._btnCircle = QPushButton("?", self)
        self._btnCircle.setObjectName("patchbay_help_btn_circle")
        self._btnCircle.setFixedSize(28, 28)
        self._btnCircle.setToolTip("Show canvas mouse & keyboard shortcuts")
        self._btnCircle.setCursor(Qt.PointingHandCursor)
        self._btnCircle.clicked.connect(self.toggleExpanded)
        self._btnCircle.setStyleSheet("""
            QPushButton#patchbay_help_btn_circle {
                background-color: rgba(30, 30, 46, 0.88);
                border: 1px solid rgba(137, 180, 250, 0.6);
                border-radius: 14px;
                color: #89b4fa;
                font-weight: bold;
                font-size: 13px;
                padding: 0px;
            }
            QPushButton#patchbay_help_btn_circle:hover {
                background-color: rgba(49, 50, 68, 0.98);
                border: 1px solid #89b4fa;
                color: #ffffff;
            }
        """)

        # Set default state to expanded (open by default)
        self.setExpanded(True)
        self._dragPos = None
        self._userMoved = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragPos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragPos is not None and event.buttons() & Qt.LeftButton:
            vp = self.parentWidget()
            if vp:
                new_pos = event.globalPos() - self._dragPos
                # Constrain within viewport bounds
                x = max(0, min(new_pos.x(), vp.width() - self.width()))
                y = max(0, min(new_pos.y(), vp.height() - self.height()))
                self.move(x, y)
                self._userMoved = True
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragPos = None
        super().mouseReleaseEvent(event)

    def setExpanded(self, expanded):
        self._expanded = bool(expanded)
        if self._expanded:
            self._btnCircle.hide()
            self._headerWidget.show()
            self._lblContent.show()
            self.setFixedSize(280, 245)
            self.setStyleSheet("""
                QFrame#patchbay_help_overlay {
                    background-color: rgba(24, 24, 37, 0.93);
                    border: 1px solid #45475a;
                    border-radius: 8px;
                }
            """)
        else:
            self._headerWidget.hide()
            self._lblContent.hide()
            self._btnCircle.show()
            self.setFixedSize(28, 28)
            self.setStyleSheet("""
                QFrame#patchbay_help_overlay {
                    background: transparent;
                    border: none;
                }
            """)
        if not getattr(self, "_userMoved", False):
            self.reposition()

    def toggleExpanded(self):
        self.setExpanded(not self._expanded)

    def reposition(self):
        if getattr(self, "_userMoved", False):
            return
        vp = self.parentWidget()
        if vp is None:
            return
        W = vp.width()
        H = vp.height()
        w = self.width()
        h = self.height()
        margin = 12
        new_x = max(10, W - w - margin)
        new_y = max(10, H - h - margin)
        self.move(new_x, new_y)
        self.raise_()


# ------------------------------------------------------------------------------------------------------------
# Floating Photoshop-style Modal Toolbar
# ------------------------------------------------------------------------------------------------------------

_CACHED_NERD_FONT_FAMILY = None

def getBestNerdFont():
    global _CACHED_NERD_FONT_FAMILY
    if _CACHED_NERD_FONT_FAMILY is not None:
        return _CACHED_NERD_FONT_FAMILY

    try:
        families = QFontDatabase.families()
    except (TypeError, AttributeError):
        try:
            families = QFontDatabase().families()
        except Exception:
            families = []
    nerd_candidates = [
        "JetBrainsMono Nerd Font",
        "JetBrainsMonoNF",
        "CommitMono Nerd Font Mono",
        "Liga SFMono Nerd Font",
        "FiraCode Nerd Font",
        "Hack Nerd Font",
        "MesloLGS NF",
    ]
    for cand in nerd_candidates:
        if cand in families:
            _CACHED_NERD_FONT_FAMILY = cand
            return cand

    for fam in families:
        if "nerd" in fam.lower():
            _CACHED_NERD_FONT_FAMILY = fam
            return fam

    _CACHED_NERD_FONT_FAMILY = ""
    return _CACHED_NERD_FONT_FAMILY


class CanvasToolBarOverlay(QFrame):
    """Floating Photoshop/Blender style modal tool selection pill."""

    def __init__(self, graphicsView, parent=None):
        super().__init__(parent or graphicsView.viewport())
        self.setObjectName("canvas_toolbar_overlay")
        self.graphicsView = graphicsView
        self._dragPos = None
        self._userMoved = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(2)

        font_family = getBestNerdFont()
        font = QFont(font_family, 13) if font_family else QFont()
        if not font_family:
            font.setPointSize(12)

        # Icons: Nerd Font glyphs or clean unicode symbols
        self.icon_pointer = "\U000f01be" if font_family else "↖"   # nf-md-cursor_default / arrow
        self.icon_select  = "\U000f0485" if font_family else "⛶"   # nf-md-select_drag / marquee
        self.icon_hand    = "\U000f0361" if font_family else "✋"   # nf-md-hand_back_right / hand

        self.btnPointer = QPushButton(self.icon_pointer, self)
        self.btnPointer.setToolTip("Pointer / Default (Q / Esc)")
        self.btnPointer.setFont(font)

        self.btnSelect = QPushButton(self.icon_select, self)
        self.btnSelect.setToolTip("Marquee Selection (V)")
        self.btnSelect.setFont(font)

        self.btnHand = QPushButton(self.icon_hand, self)
        self.btnHand.setToolTip("Hand / Pan Canvas (H / Space)")
        self.btnHand.setFont(font)

        for btn in (self.btnPointer, self.btnSelect, self.btnHand):
            btn.setFixedSize(30, 28)
            btn.setCheckable(True)
            layout.addWidget(btn)

        self.btnPointer.clicked.connect(lambda: self._setMode(0))
        self.btnSelect.clicked.connect(lambda: self._setMode(1))
        self.btnHand.clicked.connect(lambda: self._setMode(2))

        self.setStyleSheet("""
            QFrame#canvas_toolbar_overlay {
                background-color: rgba(24, 24, 37, 0.92);
                border: 1px solid #45475a;
                border-radius: 8px;
            }
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 5px;
                color: #a6adc8;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(69, 71, 90, 0.7);
                color: #cdd6f4;
            }
            QPushButton:checked {
                background-color: #89b4fa;
                color: #11111b;
            }
        """)

        self.updateActiveButton(0)
        self.setFixedSize(102, 36)

    def _setMode(self, mode):
        if hasattr(self.graphicsView, "setToolMode"):
            self.graphicsView.setToolMode(mode)
        self.updateActiveButton(mode)

    def updateActiveButton(self, mode):
        self.btnPointer.setChecked(mode == 0)
        self.btnSelect.setChecked(mode == 1)
        self.btnHand.setChecked(mode == 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragPos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragPos is not None and event.buttons() & Qt.LeftButton:
            vp = self.parentWidget()
            if vp:
                new_pos = event.globalPos() - self._dragPos
                x = max(0, min(new_pos.x(), vp.width() - self.width()))
                y = max(0, min(new_pos.y(), vp.height() - self.height()))
                self.move(x, y)
                self._userMoved = True
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragPos = None
        super().mouseReleaseEvent(event)

    def reposition(self):
        if getattr(self, "_userMoved", False):
            return
        vp = self.parentWidget()
        if vp is None:
            return
        # Position top-center
        x = max(10, (vp.width() - self.width()) // 2)
        y = 12
        self.move(x, y)
        self.raise_()


# ------------------------------------------------------------------------------------------------------------
# Canvas Viewport Event Filter (Auto-Scroll & UI Disconnect)
# ------------------------------------------------------------------------------------------------------------


class CanvasViewportFilter(QObject):
    """Event filter managing boundary auto-scrolling during drag, quick disconnects, and help overlay."""

    def __init__(self, hostWindow, graphicsView):
        super().__init__(graphicsView.viewport())
        self.hostWindow = hostWindow
        self.graphicsView = graphicsView

        self._dragActive = False
        self._inSyntheticMouseMove = False

        self._scrollTimer = QTimer(self)
        self._scrollTimer.setInterval(20)  # 50 Hz smooth scrolling
        self._scrollTimer.timeout.connect(self._slot_autoScroll)

        # Create floating mode toolbar & help overlay inside the viewport
        self.toolBar = CanvasToolBarOverlay(self.graphicsView, self.graphicsView.viewport())
        self.toolBar.show()
        QTimer.singleShot(100, self.toolBar.reposition)

        self.helpOverlay = PatchbayHelpOverlay(self.graphicsView.viewport())
        self.helpOverlay.show()
        QTimer.singleShot(100, self.helpOverlay.reposition)

        # Hook up tool mode change listener to toolBar
        if hasattr(self.graphicsView, "toolModeChanged"):
            self.graphicsView.toolModeChanged.connect(self.toolBar.updateActiveButton)

        # Install self on viewport
        self.graphicsView.viewport().installEventFilter(self)

    def findPortOrCableUnderMouse(self, vp_pos):
        search_rect = QRect(vp_pos.x() - 8, vp_pos.y() - 8, 16, 16)
        items = self.graphicsView.items(search_rect)
        if not items:
            single = self.graphicsView.itemAt(vp_pos)
            if single is not None:
                items = [single]

        scene_pt = self.graphicsView.mapToScene(vp_pos)

        # 1. Search for a Port item (CanvasPort has m_port_id and m_group_id)
        for item in items:
            gid, pid = self.extractPortAndGroupIds(item)
            if gid is not None and pid is not None:
                return ("port", gid, pid)

        # 2. Check if any CanvasBox has a port under scene_pt
        for item in items:
            gid, pid = self.extractPortFromBox(item, scene_pt)
            if gid is not None and pid is not None:
                return ("port", gid, pid)

        # 3. Check if any item is directly a Cable / Connection line (CanvasBezierLine has item1, item2)
        for item in items:
            cid = self.extractConnectionId(item)
            if cid is not None:
                return ("cable", cid, None)

        # 4. Check patchcanvas.canvas.connection_list if present
        conn_list = getattr(
            getattr(patchcanvas, "canvas", None), "connection_list", None
        )
        if conn_list:
            for conn in conn_list:
                line = getattr(
                    conn, "line", getattr(conn, "fLine", getattr(conn, "m_line", None))
                )
                if line is not None and (
                    line in items or any(it is line for it in items)
                ):
                    cid = getattr(
                        conn,
                        "connection_id",
                        getattr(
                            conn,
                            "connectionId",
                            getattr(conn, "id", getattr(conn, "m_connection_id", None)),
                        ),
                    )
                    if cid is not None:
                        try:
                            return ("cable", int(cid), None)
                        except Exception:
                            pass

            try:
                stroker = QPainterPathStroker()
                stroker.setWidth(16.0)
                for conn in conn_list:
                    line = getattr(
                        conn,
                        "line",
                        getattr(conn, "fLine", getattr(conn, "m_line", None)),
                    )
                    if line is not None and hasattr(line, "shape"):
                        line_pt = line.mapFromScene(scene_pt)
                        path = line.path() if hasattr(line, "path") else line.shape()
                        hit_path = stroker.createStroke(path)
                        if hit_path.contains(line_pt):
                            cid = getattr(
                                conn,
                                "connection_id",
                                getattr(
                                    conn,
                                    "connectionId",
                                    getattr(
                                        conn,
                                        "id",
                                        getattr(conn, "m_connection_id", None),
                                    ),
                                ),
                            )
                            if cid is not None:
                                try:
                                    return ("cable", int(cid), None)
                                except Exception:
                                    pass
            except Exception as e:
                log_carla(f"carla_canvas: connection distance check error: {e}")

        return (None, None, None)

    def extractPortAndGroupIds(self, item):
        target = item
        while target is not None:
            pid = getattr(
                target,
                "m_port_id",
                getattr(
                    target,
                    "port_id",
                    getattr(target, "portId", getattr(target, "fPortId", None)),
                ),
            )
            gid = getattr(
                target,
                "m_group_id",
                getattr(
                    target,
                    "group_id",
                    getattr(
                        target,
                        "groupId",
                        getattr(
                            target,
                            "fGroupId",
                            getattr(
                                target, "clientId", getattr(target, "fClientId", None)
                            ),
                        ),
                    ),
                ),
            )

            if pid is not None and gid is None:
                parent = target.parentItem()
                if parent is not None:
                    gid = getattr(
                        parent,
                        "m_group_id",
                        getattr(
                            parent,
                            "group_id",
                            getattr(
                                parent,
                                "groupId",
                                getattr(
                                    parent,
                                    "fGroupId",
                                    getattr(
                                        parent,
                                        "clientId",
                                        getattr(parent, "fClientId", None),
                                    ),
                                ),
                            ),
                        ),
                    )

            if pid is not None and gid is not None:
                try:
                    return int(gid), int(pid)
                except Exception:
                    pass

            for attr in ("port", "fPort", "_port", "portData", "fPortData"):
                p_obj = getattr(target, attr, None)
                if p_obj is not None:
                    if isinstance(p_obj, dict):
                        p_id = p_obj.get(
                            "m_port_id",
                            p_obj.get("port_id", p_obj.get("portId", p_obj.get("id"))),
                        )
                        g_id = p_obj.get(
                            "m_group_id",
                            p_obj.get(
                                "group_id", p_obj.get("groupId", p_obj.get("clientId"))
                            ),
                        )
                    else:
                        p_id = getattr(
                            p_obj,
                            "m_port_id",
                            getattr(
                                p_obj,
                                "port_id",
                                getattr(p_obj, "portId", getattr(p_obj, "id", None)),
                            ),
                        )
                        g_id = getattr(
                            p_obj,
                            "m_group_id",
                            getattr(
                                p_obj,
                                "group_id",
                                getattr(
                                    p_obj, "groupId", getattr(p_obj, "clientId", None)
                                ),
                            ),
                        )
                    if p_id is not None and g_id is not None:
                        try:
                            return int(g_id), int(p_id)
                        except Exception:
                            pass

            if hasattr(target, "data"):
                try:
                    d = target.data(0)
                    if isinstance(d, tuple) and len(d) == 2:
                        return int(d[0]), int(d[1])
                except Exception:
                    pass

            target = target.parentItem()
        return None, None

    def extractPortFromBox(self, box_item, scene_pt):
        gid = getattr(
            box_item,
            "m_group_id",
            getattr(
                box_item,
                "group_id",
                getattr(
                    box_item,
                    "groupId",
                    getattr(
                        box_item,
                        "fGroupId",
                        getattr(
                            box_item, "clientId", getattr(box_item, "fClientId", None)
                        ),
                    ),
                ),
            ),
        )
        if gid is None:
            return None, None

        for attr in ("ports", "fPorts", "port_list", "fPortList", "_ports"):
            ports_list = getattr(box_item, attr, None)
            if ports_list:
                box_pt = box_item.mapFromScene(scene_pt)
                items_to_check = (
                    ports_list.values() if isinstance(ports_list, dict) else ports_list
                )
                for p in items_to_check:
                    pid = getattr(
                        p,
                        "m_port_id",
                        getattr(
                            p,
                            "port_id",
                            getattr(p, "portId", getattr(p, "fPortId", None)),
                        ),
                    )
                    if pid is None and isinstance(p, dict):
                        pid = p.get(
                            "m_port_id", p.get("port_id", p.get("portId", p.get("id")))
                        )
                    if pid is None:
                        continue
                    rect = getattr(
                        p, "rect", getattr(p, "fRect", getattr(p, "boundingRect", None))
                    )
                    if rect is not None:
                        r = rect() if callable(rect) else rect
                        if hasattr(r, "contains") and r.contains(box_pt):
                            return int(gid), int(pid)
                        if hasattr(r, "center"):
                            c = r.center()
                            dx = c.x() - box_pt.x()
                            dy = c.y() - box_pt.y()
                            if (dx * dx + dy * dy) <= 400:
                                return int(gid), int(pid)
        return None, None

    def extractConnectionId(self, item):
        target = item
        while target is not None:
            # 1. CanvasBezierLine has item1 and item2 as CanvasPort instances
            item1 = getattr(target, "item1", getattr(target, "m_item1", None))
            item2 = getattr(target, "item2", getattr(target, "m_item2", None))
            if item1 is not None and item2 is not None:
                g1, pt1 = self.extractPortAndGroupIds(item1)
                g2, pt2 = self.extractPortAndGroupIds(item2)
                if g1 is not None and g2 is not None:
                    # Search in patchcanvas.canvas.connection_list
                    conn_list = getattr(
                        getattr(patchcanvas, "canvas", None), "connection_list", None
                    )
                    if conn_list:
                        for conn in conn_list:
                            cgOut = getattr(
                                conn,
                                "group_out_id",
                                getattr(conn, "m_group_out_id", None),
                            )
                            cpOut = getattr(
                                conn,
                                "port_out_id",
                                getattr(conn, "m_port_out_id", None),
                            )
                            cgIn = getattr(
                                conn,
                                "group_in_id",
                                getattr(conn, "m_group_in_id", None),
                            )
                            cpIn = getattr(
                                conn, "port_in_id", getattr(conn, "m_port_in_id", None)
                            )
                            if (
                                cgOut == g1
                                and cpOut == pt1
                                and cgIn == g2
                                and cpIn == pt2
                            ) or (
                                cgOut == g2
                                and cpOut == pt2
                                and cgIn == g1
                                and cpIn == pt1
                            ):
                                cid = getattr(
                                    conn,
                                    "connection_id",
                                    getattr(
                                        conn,
                                        "connectionId",
                                        getattr(
                                            conn,
                                            "id",
                                            getattr(conn, "m_connection_id", None),
                                        ),
                                    ),
                                )
                                if cid is not None:
                                    return int(cid)
                            line = getattr(
                                conn,
                                "line",
                                getattr(conn, "fLine", getattr(conn, "m_line", None)),
                            )
                            if line is target or line is item:
                                cid = getattr(
                                    conn,
                                    "connection_id",
                                    getattr(
                                        conn,
                                        "connectionId",
                                        getattr(
                                            conn,
                                            "id",
                                            getattr(conn, "m_connection_id", None),
                                        ),
                                    ),
                                )
                                if cid is not None:
                                    return int(cid)

                    # Search in hostWindow.fConnections
                    for cid, (
                        cgOut,
                        cpOut,
                        cgIn,
                        cpIn,
                    ) in self.hostWindow.fConnections.items():
                        if (
                            cgOut == g1 and cpOut == pt1 and cgIn == g2 and cpIn == pt2
                        ) or (
                            cgOut == g2 and cpOut == pt2 and cgIn == g1 and cpIn == pt1
                        ):
                            return cid

                    # Search in item1/item2 parent box m_connection_lines
                    for port_item in (item1, item2):
                        box = (
                            port_item.parentItem()
                            if hasattr(port_item, "parentItem")
                            else None
                        )
                        if box is not None:
                            cb_lines = getattr(box, "m_connection_lines", None)
                            if cb_lines:
                                for cbl in cb_lines:
                                    line = getattr(
                                        cbl, "line", getattr(cbl, "m_line", None)
                                    )
                                    if line is target or line is item:
                                        cid = getattr(
                                            cbl,
                                            "connection_id",
                                            getattr(
                                                cbl,
                                                "connectionId",
                                                getattr(
                                                    cbl,
                                                    "id",
                                                    getattr(
                                                        cbl, "m_connection_id", None
                                                    ),
                                                ),
                                            ),
                                        )
                                        if cid is not None:
                                            return int(cid)

            # 2. Direct connection ID attributes
            for attr in (
                "connection_id",
                "connectionId",
                "fConnectionId",
                "m_connection_id",
                "id",
                "fId",
                "m_id",
                "conn_id",
                "connId",
                "connection",
                "fConnection",
                "conn",
                "fConn",
            ):
                val = getattr(target, attr, None)
                if val is not None:
                    if isinstance(val, int):
                        return val
                    elif isinstance(val, (str, float)):
                        try:
                            return int(val)
                        except Exception:
                            pass
                    elif isinstance(val, dict):
                        cid = val.get(
                            "connection_id", val.get("connectionId", val.get("id"))
                        )
                        if cid is not None:
                            try:
                                return int(cid)
                            except Exception:
                                pass
                    elif (
                        hasattr(val, "id")
                        or hasattr(val, "connection_id")
                        or hasattr(val, "connectionId")
                    ):
                        cid = getattr(
                            val,
                            "connection_id",
                            getattr(val, "connectionId", getattr(val, "id", None)),
                        )
                        if cid is not None:
                            try:
                                return int(cid)
                            except Exception:
                                pass

            # 3. QGraphicsItem.data()
            if hasattr(target, "data"):
                try:
                    for role in (0, 1, 2, 32):
                        d = target.data(role)
                        if isinstance(d, int):
                            return d
                        elif isinstance(d, (str, float)):
                            try:
                                return int(d)
                            except Exception:
                                pass
                except Exception:
                    pass

            target = target.parentItem()

        return None

    def eventFilter(self, watched, event):
        if watched is not self.graphicsView.viewport():
            return False

        if getattr(self, "_inSyntheticMouseMove", False):
            return False

        etype = event.type()
        is_press = (
            etype == QEvent.MouseButtonPress
            or (hasattr(QEvent, "Type") and etype == QEvent.Type.MouseButtonPress)
            or str(etype).endswith("MouseButtonPress")
        )
        is_move = (
            etype == QEvent.MouseMove
            or (hasattr(QEvent, "Type") and etype == QEvent.Type.MouseMove)
            or str(etype).endswith("MouseMove")
        )
        is_release = (
            etype == QEvent.MouseButtonRelease
            or (hasattr(QEvent, "Type") and etype == QEvent.Type.MouseButtonRelease)
            or str(etype).endswith("MouseButtonRelease")
        )
        is_resize = (
            etype == QEvent.Resize
            or (hasattr(QEvent, "Type") and etype == QEvent.Type.Resize)
            or str(etype).endswith("Resize")
        )

        # 1. UI-based Disconnect: Alt+Click, Shift+Click, or Middle-Click on Port or Cable
        if is_press:
            btn = event.button()
            mods = event.modifiers()
            keyboard_mods = QApplication.keyboardModifiers()
            is_alt = bool((mods & Qt.AltModifier) or (keyboard_mods & Qt.AltModifier))
            is_shift = bool(
                (mods & Qt.ShiftModifier) or (keyboard_mods & Qt.ShiftModifier)
            )
            is_middle_click = btn == Qt.MiddleButton
            is_disconnect_click = is_middle_click or (
                btn in (Qt.LeftButton, Qt.RightButton) and (is_alt or is_shift)
            )

            if is_disconnect_click:
                target_type, val1, val2 = self.findPortOrCableUnderMouse(event.pos())
                if target_type == "port":
                    gid, pid = val1, val2
                    conns_to_drop = [
                        cid
                        for cid, (cgOut, cpOut, cgIn, cpIn) in list(
                            self.hostWindow.fConnections.items()
                        )
                        if (cgOut == gid and cpOut == pid)
                        or (cgIn == gid and cpIn == pid)
                    ]
                    conn_list = getattr(
                        getattr(patchcanvas, "canvas", None), "connection_list", None
                    )
                    if conn_list:
                        for conn in conn_list:
                            cgOut = getattr(
                                conn,
                                "group_out_id",
                                getattr(conn, "m_group_out_id", None),
                            )
                            cpOut = getattr(
                                conn,
                                "port_out_id",
                                getattr(conn, "m_port_out_id", None),
                            )
                            cgIn = getattr(
                                conn,
                                "group_in_id",
                                getattr(conn, "m_group_in_id", None),
                            )
                            cpIn = getattr(
                                conn, "port_in_id", getattr(conn, "m_port_in_id", None)
                            )
                            if (cgOut == gid and cpOut == pid) or (
                                cgIn == gid and cpIn == pid
                            ):
                                cid = getattr(
                                    conn,
                                    "connection_id",
                                    getattr(
                                        conn, "connectionId", getattr(conn, "id", None)
                                    ),
                                )
                                if cid is not None and int(cid) not in conns_to_drop:
                                    conns_to_drop.append(int(cid))

                    log_carla(
                        f"carla_canvas: UI disconnect port ({gid}:{pid}) -> dropping {len(conns_to_drop)} connections (is_alt={is_alt})"
                    )
                    if conns_to_drop:
                        for cid in conns_to_drop:
                            partner_cid = (
                                findStereoPartnerConnection(cid) if is_alt else None
                            )
                            self.hostWindow.host.patchbay_disconnect(
                                self.hostWindow.fExternalPatchbay, cid
                            )
                            if partner_cid is not None:
                                log_carla(
                                    f"carla_canvas: Also disconnecting stereo partner connection {partner_cid}"
                                )
                                self.hostWindow.host.patchbay_disconnect(
                                    self.hostWindow.fExternalPatchbay, partner_cid
                                )
                        return True

                elif target_type == "cable":
                    conn_id = val1
                    log_carla(
                        f"carla_canvas: UI disconnect cable (connectionId={conn_id}, is_alt={is_alt})"
                    )
                    partner_cid = (
                        findStereoPartnerConnection(conn_id) if is_alt else None
                    )
                    self.hostWindow.host.patchbay_disconnect(
                        self.hostWindow.fExternalPatchbay, conn_id
                    )
                    if partner_cid is not None:
                        log_carla(
                            f"carla_canvas: Also disconnecting stereo partner connection {partner_cid}"
                        )
                        self.hostWindow.host.patchbay_disconnect(
                            self.hostWindow.fExternalPatchbay, partner_cid
                        )
                    return True

            # Normal drag tracking for auto-scrolling
            if btn in (Qt.LeftButton, Qt.MiddleButton, Qt.RightButton):
                self._dragActive = True

        elif is_move:
            if getattr(self, "_dragActive", False):
                self._checkStartAutoScroll()

        elif is_release:
            if QApplication.mouseButtons() == Qt.NoButton:
                self._dragActive = False
                if self._scrollTimer.isActive():
                    self._scrollTimer.stop()

        elif is_resize:
            if hasattr(self, "toolBar") and self.toolBar:
                self.toolBar.reposition()
            if hasattr(self, "helpOverlay") and self.helpOverlay:
                self.helpOverlay.reposition()

        return False

    def _checkStartAutoScroll(self):
        vp = self.graphicsView.viewport()
        cur_vp_pos = vp.mapFromGlobal(QCursor.pos())
        x = cur_vp_pos.x()
        y = cur_vp_pos.y()
        W = vp.width()
        H = vp.height()
        margin = 40

        near_edge = x < margin or x > W - margin or y < margin or y > H - margin
        if near_edge:
            if not self._scrollTimer.isActive():
                self._scrollTimer.start()
        else:
            if self._scrollTimer.isActive():
                self._scrollTimer.stop()

    def _slot_autoScroll(self):
        if (
            not getattr(self, "_dragActive", False)
            or QApplication.mouseButtons() == Qt.NoButton
        ):
            self._dragActive = False
            if self._scrollTimer.isActive():
                self._scrollTimer.stop()
            return

        vp = self.graphicsView.viewport()
        cur_global_pos = QCursor.pos()
        cur_vp_pos = vp.mapFromGlobal(cur_global_pos)
        x = cur_vp_pos.x()
        y = cur_vp_pos.y()
        W = vp.width()
        H = vp.height()
        margin = 40

        dx = 0
        dy = 0

        if x < margin:
            dist = margin - x
            dx = -min(40, max(5, int(dist * 0.4)))
        elif x > W - margin:
            dist = x - (W - margin)
            dx = min(40, max(5, int(dist * 0.4)))

        if y < margin:
            dist = margin - y
            dy = -min(40, max(5, int(dist * 0.4)))
        elif y > H - margin:
            dist = y - (H - margin)
            dy = min(40, max(5, int(dist * 0.4)))

        if dx != 0 or dy != 0:
            hsb = self.graphicsView.horizontalScrollBar()
            vsb = self.graphicsView.verticalScrollBar()
            if dx != 0:
                hsb.setValue(hsb.value() + dx)
            if dy != 0:
                vsb.setValue(vsb.value() + dy)

            # Keep dragging lines / items updated by sending a synthetic mouse move
            try:
                self._inSyntheticMouseMove = True
                fake_event = QMouseEvent(
                    QEvent.MouseMove,
                    QPointF(cur_vp_pos),
                    QPointF(cur_global_pos),
                    Qt.NoButton,
                    QApplication.mouseButtons(),
                    QApplication.keyboardModifiers(),
                )
                QApplication.sendEvent(vp, fake_event)
            except Exception:
                pass
            finally:
                self._inSyntheticMouseMove = False
        else:
            if self._scrollTimer.isActive():
                self._scrollTimer.stop()


# ------------------------------------------------------------------------------------------------------------
# Canvas Action Callback
# ------------------------------------------------------------------------------------------------------------


def canvasCallback(action, value1, value2, valueStr):
    host = gCarla.gui.host

    if getattr(gCarla.gui, "fCustomStopAction", 0) == getattr(
        gCarla.gui, "CUSTOM_ACTION_APP_CLOSE", 1
    ):
        return

    if (
        action == patchcanvas.ACTION_GROUP_INFO
        or action == patchcanvas.ACTION_GROUP_RENAME
    ):
        pass

    elif action == patchcanvas.ACTION_GROUP_SPLIT:
        groupId = value1
        patchcanvas.splitGroup(groupId)
        gCarla.gui.updateMiniCanvasLater()

    elif action == patchcanvas.ACTION_GROUP_JOIN:
        groupId = value1
        patchcanvas.joinGroup(groupId)
        gCarla.gui.updateMiniCanvasLater()

    elif action == patchcanvas.ACTION_GROUP_POSITION:
        if gCarla.gui.fIsProjectLoading:
            return
        if not host.is_engine_running():
            return
        groupId = value1
        x1, y1, x2, y2 = tuple(int(i) for i in valueStr.split(":"))
        host.patchbay_set_group_pos(
            gCarla.gui.fExternalPatchbay, groupId, x1, y1, x2, y2
        )
        if hasattr(gCarla.gui, "markProjectModified"):
            gCarla.gui.markProjectModified()
        if hasattr(gCarla.gui, "fSessionManager") and gCarla.gui.fSessionManager:
            gCarla.gui.fSessionManager.queue_node_position_sync()
        gCarla.gui.updateMiniCanvasLater()

    elif (
        action == patchcanvas.ACTION_PORT_INFO
        or action == patchcanvas.ACTION_PORT_RENAME
    ):
        pass

    elif action == patchcanvas.ACTION_PORTS_CONNECT:
        gOut, pOut, gIn, pIn = tuple(int(i) for i in valueStr.split(":"))
        log_carla(
            f"carla_canvas: ACTION_PORTS_CONNECT {gOut}:{pOut} -> {gIn}:{pIn} (external={gCarla.gui.fExternalPatchbay})"
        )

        if not host.patchbay_connect(
            gCarla.gui.fExternalPatchbay, gOut, pOut, gIn, pIn
        ):
            err = host.get_last_error()
            log_carla(f"carla_canvas: Connection failed: {err}")
            print("Connection failed:", err)
        else:
            log_carla("carla_canvas: Connection request succeeded")
            if hasattr(gCarla.gui, "markProjectModified"):
                gCarla.gui.markProjectModified()
            if QApplication.keyboardModifiers() & Qt.AltModifier:
                autoConnectStereoPair(gOut, pOut, gIn, pIn)

    elif action == patchcanvas.ACTION_PORTS_DISCONNECT:
        connectionId = value1
        log_carla(
            f"carla_canvas: ACTION_PORTS_DISCONNECT connectionId={connectionId} (external={gCarla.gui.fExternalPatchbay})"
        )

        alt_pressed = bool(QApplication.keyboardModifiers() & Qt.AltModifier)
        partner_conn_id = None
        if alt_pressed:
            partner_conn_id = findStereoPartnerConnection(connectionId)

        if not host.patchbay_disconnect(gCarla.gui.fExternalPatchbay, connectionId):
            err = host.get_last_error()
            log_carla(f"carla_canvas: Disconnect failed: {err}")
            print("Disconnect failed:", err)
        else:
            log_carla("carla_canvas: Disconnect request succeeded")
            if hasattr(gCarla.gui, "markProjectModified"):
                gCarla.gui.markProjectModified()
            if partner_conn_id is not None:
                log_carla(
                    f"carla_canvas: Stereo auto-disconnect (Alt): connectionId={partner_conn_id}"
                )
                host.patchbay_disconnect(gCarla.gui.fExternalPatchbay, partner_conn_id)

    elif action == patchcanvas.ACTION_PLUGIN_CLONE:
        pluginId = value1

        if not host.clone_plugin(pluginId):
            CustomMessageBox(
                gCarla.gui,
                QMessageBox.Warning,
                gCarla.gui.tr("Error"),
                gCarla.gui.tr("Operation failed"),
                host.get_last_error(),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )

    elif action == patchcanvas.ACTION_PLUGIN_EDIT:
        pluginId = value1
        pwidget = gCarla.gui.getPluginSlotWidget(pluginId)

        if pwidget is not None:
            pwidget.showEditDialog()

    elif action == patchcanvas.ACTION_PLUGIN_RENAME:
        pluginId = value1
        pwidget = gCarla.gui.getPluginSlotWidget(pluginId)

        if pwidget is not None:
            pwidget.showRenameDialog()

    elif action == patchcanvas.ACTION_PLUGIN_REPLACE:
        pluginId = value1
        pwidget = gCarla.gui.getPluginSlotWidget(pluginId)

        if pwidget is not None:
            pwidget.showReplaceDialog()

    elif action == patchcanvas.ACTION_PLUGIN_REMOVE:
        pluginId = value1

        if not host.remove_plugin(pluginId):
            CustomMessageBox(
                gCarla.gui,
                QMessageBox.Warning,
                gCarla.gui.tr("Error"),
                gCarla.gui.tr("Operation failed"),
                host.get_last_error(),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )

    elif action == patchcanvas.ACTION_PLUGIN_SHOW_UI:
        pluginId = value1
        pwidget = gCarla.gui.getPluginSlotWidget(pluginId)

        if pwidget is not None:
            pwidget.showCustomUI()

    elif action == patchcanvas.ACTION_BG_RIGHT_CLICK:
        gCarla.gui.slot_showPluginActionsMenu()

    elif action == patchcanvas.ACTION_INLINE_DISPLAY:
        if gCarla.gui.fIsProjectLoading:
            return
        if not host.is_engine_running():
            return
        pluginId = value1
        width, height = [int(v) for v in valueStr.split(":")]
        return host.render_inline_display(pluginId, width, height)

    elif action == getattr(patchcanvas, "ACTION_PLUGIN_COLOR", 17):
        pluginId = value1
        colorStr = valueStr
        if colorStr:
            c = QColor(colorStr)
            color_tuple = (c.red(), c.green(), c.blue())
            color_data_str = f"{c.red()};{c.green()};{c.blue()}"
            gCarla.gui.changePluginColor(pluginId, color_tuple, color_data_str)
        else:
            gCarla.gui.changePluginColor(pluginId, (255, 255, 255), "255;255;255")
