#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import json
import subprocess
from qt_compat import qt_config

if qt_config == 5:
    from PyQt5.QtCore import (
        pyqtSignal,
        pyqtSlot,
        qCritical,
        QT_VERSION,
        Qt,
        QPointF,
        QRectF,
        QTimer,
    )
    from PyQt5.QtGui import (
        QCursor,
        QFont,
        QFontMetrics,
        QImage,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPen,
    )
    from PyQt5.QtSvg import QGraphicsSvgItem
    from PyQt5.QtWidgets import (
        QApplication,
        QGraphicsItem,
        QGraphicsObject,
        QMenu,
        QDialog,
        QTabWidget,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QFormLayout,
        QLabel,
        QLineEdit,
        QDialogButtonBox,
        QFrame,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QGroupBox,
        QCheckBox,
        QPushButton,
    )
elif qt_config == 6:
    from PyQt6.QtCore import (
        pyqtSignal,
        pyqtSlot,
        qCritical,
        QT_VERSION,
        Qt,
        QPointF,
        QRectF,
        QTimer,
    )
    from PyQt6.QtGui import (
        QCursor,
        QFont,
        QFontMetrics,
        QImage,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPen,
    )
    from PyQt6.QtSvgWidgets import QGraphicsSvgItem
    from PyQt6.QtWidgets import (
        QApplication,
        QGraphicsItem,
        QGraphicsObject,
        QMenu,
        QDialog,
        QTabWidget,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QFormLayout,
        QLabel,
        QLineEdit,
        QDialogButtonBox,
        QFrame,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QGroupBox,
        QCheckBox,
        QPushButton,
    )

# ------------------------------------------------------------------------------------------------------------
# Backwards-compatible horizontalAdvance/width call, depending on Qt version


def fontHorizontalAdvance(font, string):
    if QT_VERSION >= 0x50B00:
        return QFontMetrics(font).horizontalAdvance(string)
    return QFontMetrics(font).width(string)


def getSystemFont(size=None, weight=None):
    base_font = QApplication.font() if QApplication.instance() else QFont()
    font = QFont(base_font)
    if size is not None and size > 0:
        font.setPixelSize(size)
    if weight is not None:
        font.setWeight(weight)
    return font


# ------------------------------------------------------------------------------------------------------------
# PipeWire Property Formatting Dictionary

PW_PRETTY_MAP = {
    # Application / Client
    "application.name": "Application Name",
    "application.process.id": "Process ID",
    "application.process.user": "Process User",
    "application.process.host": "Process Host",
    "application.process.binary": "Process Binary",
    "application.language": "Language",
    "client.api": "Client API",
    "client.id": "Client ID",
    # ALSA Specifics
    "alsa.card": "ALSA Card ID",
    "alsa.card_name": "ALSA Card Name",
    "alsa.class": "ALSA Class",
    "alsa.components": "ALSA Components",
    "alsa.device": "ALSA Device ID",
    "alsa.driver_name": "ALSA Driver Name",
    "alsa.id": "ALSA ID",
    "alsa.long_card_name": "ALSA Long Card Name",
    "alsa.mixer_name": "ALSA Mixer Name",
    "alsa.name": "ALSA Name",
    "alsa.resolution_bits": "ALSA Resolution (Bits)",
    "alsa.subclass": "ALSA Subclass",
    "alsa.subdevice": "ALSA Subdevice ID",
    "alsa.subdevice_name": "ALSA Subdevice Name",
    "alsa.sync.id": "ALSA Sync ID",
    "api.alsa.card.longname": "ALSA API Card Longname",
    "api.alsa.card.name": "ALSA API Card Name",
    "api.alsa.headroom": "ALSA API Headroom",
    "api.alsa.path": "ALSA API Path",
    "api.alsa.pcm.card": "ALSA PCM Card",
    "api.alsa.pcm.stream": "ALSA PCM Stream",
    "api.alsa.period-num": "ALSA Period Count",
    "api.alsa.period-size": "ALSA Period Size",
    # Audio & Clock
    "audio.channels": "Channels",
    "audio.rate": "Sample Rate",
    "audio.position": "Channel Map",
    "audio.format": "Audio Format",
    "clock.quantum-limit": "Quantum Limit",
    "clock.rate": "Clock Rate",
    "clock.allowed-rates": "Allowed Rates",
    # Device
    "card.profile.device": "Card Profile Device",
    "device.api": "Device API",
    "device.bus": "Device Bus",
    "device.class": "Device Class",
    "device.icon-name": "Device Icon",
    "device.id": "Device ID",
    "device.description": "Device Description",
    "device.name": "Device Name",
    "device.nick": "Device Nickname",
    "device.profile.description": "Device Profile Description",
    "device.profile.name": "Device Profile Name",
    "device.routes": "Device Routes",
    # Core / Internal
    "factory.name": "Factory Name",
    "factory.id": "Factory ID",
    "library.name": "Library Name",
    "object.id": "Object ID",
    "object.serial": "Object Serial",
    "object.path": "Object Path",
    # Media
    "media.class": "Media Class",
    "media.type": "Media Type",
    "media.role": "Media Role",
    "media.name": "Media Name",
    # Node
    "node.description": "Description",
    "node.name": "Node Name",
    "node.nick": "Nickname",
    "node.latency": "Latency",
    "node.max-latency": "Maximum Latency",
    "node.driver": "Is Driver",
    "node.driver-id": "Driver Node ID",
    "node.loop.name": "Loop Name",
    "node.pause-on-idle": "Pause on Idle",
    # Port & Stream
    "port.name": "Port Name",
    "port.direction": "Port Direction",
    "port.alias": "Port Alias",
    "port.group": "Port Group",
    "stream.is-live": "Is Live Stream",
    # Priority
    "priority.driver": "Driver Priority",
    "priority.session": "Session Priority",
}
# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import (
    canvas,
    features,
    options,
    port_dict_t,
    CanvasBoxType,
    ANTIALIASING_FULL,
    ACTION_PLUGIN_EDIT,
    ACTION_PLUGIN_SHOW_UI,
    ACTION_PLUGIN_CLONE,
    ACTION_PLUGIN_REMOVE,
    ACTION_PLUGIN_RENAME,
    ACTION_PLUGIN_REPLACE,
    ACTION_GROUP_INFO,
    ACTION_GROUP_JOIN,
    ACTION_GROUP_SPLIT,
    ACTION_GROUP_RENAME,
    ACTION_PORTS_DISCONNECT,
    ACTION_INLINE_DISPLAY,
    EYECANDY_FULL,
    PORT_MODE_NULL,
    PORT_MODE_INPUT,
    PORT_MODE_OUTPUT,
    PORT_TYPE_NULL,
    PORT_TYPE_AUDIO_JACK,
    PORT_TYPE_MIDI_ALSA,
    PORT_TYPE_MIDI_JACK,
    PORT_TYPE_PARAMETER,
    MAX_PLUGIN_ID_ALLOWED,
)

from .canvasboxshadow import CanvasBoxShadow
from .canvasicon import CanvasIcon
from .canvasport import CanvasPort
from .theme import Theme
from .utils import (
    CanvasItemFX,
    CanvasGetFullPortName,
    CanvasGetPortConnectionList,
    log_carla,
)

# ------------------------------------------------------------------------------------------------------------


class cb_line_t(object):
    def __init__(self, line, connection_id):
        self.line = line
        self.connection_id = connection_id


# ------------------------------------------------------------------------------------------------------------


class BoxPropertiesDialog(QDialog):
    def __init__(self, box, parent=None):
        super().__init__(parent)
        self.box = box
        self.setWindowTitle(f"{box.getGroupName()} Properties")
        self.resize(520, 680)

        # Fetch PipeWire properties early using the node's query name
        query_name = (
            getattr(self.box, "pw_node_name", None)
            or self.box.getGroupName()
        )
        self.pw_props = self.get_pw_properties(query_name)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # Tabs
        self.tabs = QTabWidget()
        self.general_tab = QWidget()
        self.ports_tab = QWidget()
        self.pw_tab = QWidget()

        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.ports_tab, "Ports")
        self.tabs.addTab(self.pw_tab, "PipeWire Raw")

        layout.addWidget(self.tabs)

        self.setup_general_tab()
        self.setup_ports_tab()
        self.setup_pipewire_tab()

        # Bottom Buttons (OK, Cancel, Apply)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self.apply_changes
        )
        layout.addWidget(self.button_box)

    def get_pw_properties(self, search_name):
        try:
            # 1. Try querying pw-dump directly with search_name (pw-dump accepts node.name or id)
            if search_name:
                try:
                    out = subprocess.check_output(
                        ["pw-dump", str(search_name)],
                        text=True,
                        stderr=subprocess.DEVNULL,
                    )
                    if out.strip():
                        data = json.loads(out)
                        for obj in data:
                            if obj.get("type") in (
                                "PipeWire:Interface:Node",
                                "PipeWire:Interface:Client",
                            ):
                                props = obj.get("info", {}).get("props", {})
                                if props:
                                    if "node.name" in props and hasattr(self.box, "pw_node_name"):
                                        self.box.pw_node_name = props["node.name"]
                                    return props
                except (subprocess.SubprocessError, json.JSONDecodeError):
                    pass

            # 2. Fall back to dumping state and matching against node names, descriptions, or nicks
            out = subprocess.check_output(["pw-dump"], text=True, stderr=subprocess.DEVNULL)
            state = json.loads(out)

            box_title = self.box.getGroupName() if hasattr(self.box, "getGroupName") else ""
            for obj in state:
                if obj.get("type") in (
                    "PipeWire:Interface:Node",
                    "PipeWire:Interface:Client",
                ):
                    props = obj.get("info", {}).get("props", {})
                    candidates = (
                        props.get("node.name"),
                        props.get("node.description"),
                        props.get("node.nick"),
                        props.get("client.name"),
                        props.get("application.name"),
                        props.get("media.name"),
                    )

                    if (search_name and search_name in candidates) or (
                        box_title and box_title in candidates
                    ):
                        if "node.name" in props and hasattr(self.box, "pw_node_name"):
                            self.box.pw_node_name = props["node.name"]
                        return props

        except Exception as e:
            print(f"Failed to fetch PipeWire data: {e}")

        return None

    def create_group_box(self, title):
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 13px;
                padding-top: 18px; 
                margin-top: 12px;
                border: 1px solid rgba(128, 128, 128, 0.3);
                border-radius: 4px;
            } 
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px 0 5px;
            }
        """)
        return group

    def setup_general_tab(self):
        layout = QVBoxLayout(self.general_tab)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # --- 1. Header (H1 Equivalent) ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        icon_label = QLabel()
        icon_label.setPixmap(
            self.style()
            .standardIcon(self.style().StandardPixmap.SP_FileIcon)
            .pixmap(48, 48)
        )
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)

        self.name_edit = QLineEdit(self.box.getGroupName())
        font = self.name_edit.font()
        font.setPointSize(16)
        font.setBold(True)
        self.name_edit.setFont(font)
        self.name_edit.setStyleSheet("""
            QLineEdit { 
                border: 1px solid transparent; 
                border-bottom: 1px solid rgba(128, 128, 128, 0.4); 
                background: transparent; 
                padding: 0px;
                margin-bottom: 2px;
            } 
            QLineEdit:focus { 
                border-bottom: 2px solid palette(highlight); 
            }
        """)
        title_layout.addWidget(self.name_edit)

        type_str = "Plugin Node" if self.box.m_plugin_id >= 0 else "Canvas Group"
        type_subtitle = QLabel(
            f"<span style='color: #777; font-size: 11pt;'>{type_str}</span>"
        )
        title_layout.addWidget(type_subtitle)
        title_layout.addStretch()

        header_layout.addLayout(title_layout)
        layout.addLayout(header_layout)

        # Separator
        line1 = QFrame()
        line1.setFrameShape(
            QFrame.Shape.HLine if hasattr(QFrame, "Shape") else QFrame.HLine
        )
        line1.setFrameShadow(
            QFrame.Shadow.Sunken if hasattr(QFrame, "Shadow") else QFrame.Sunken
        )
        layout.addWidget(line1)

        # --- 2. PipeWire Identity Box (Most Important) ---
        if self.pw_props:
            pw_group = self.create_group_box("PipeWire Identity")
            pw_layout = QFormLayout(pw_group)
            pw_layout.setSpacing(8)
            pw_layout.setContentsMargins(15, 15, 15, 15)

            desc = self.pw_props.get(
                "node.description", self.pw_props.get("node.nick", "N/A")
            )
            media_class = self.pw_props.get("media.class", "N/A")
            app_name = self.pw_props.get("application.name", "N/A")
            node_name = self.pw_props.get("node.name", "N/A")

            lbl_desc = QLabel(
                f"<span style='font-size: 11pt; font-weight: bold;'>{desc}</span>"
            )
            lbl_desc.setWordWrap(True)

            pw_layout.addRow("Description:", lbl_desc)

            if media_class != "N/A":
                pw_layout.addRow(
                    "Media Class:",
                    QLabel(
                        f"<code style='color: #2b78e4; font-size: 10pt;'>{media_class}</code>"
                    ),
                )

            if app_name != "N/A":
                pw_layout.addRow("Application:", QLabel(f"<b>{app_name}</b>"))

            pw_layout.addRow("Node Name:", QLabel(str(node_name)))
            layout.addWidget(pw_group)

        # --- 3. Node Identity Box ---
        info_group = self.create_group_box("Node Details")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(15, 15, 15, 15)

        info_layout.addRow("Canvas Group ID:", QLabel(str(self.box.getGroupId())))
        if self.box.m_plugin_id >= 0:
            info_layout.addRow("Plugin ID:", QLabel(f"<b>{self.box.m_plugin_id}</b>"))
            info_layout.addRow(
                "Custom UI:",
                QLabel("<b>Available</b>" if self.box.m_plugin_ui else "Not Available"),
            )

        layout.addWidget(info_group)

        # --- 4. Geometry Box (Least Important) ---
        geo_group = self.create_group_box("Geometry & Layout")
        geo_layout = QFormLayout(geo_group)
        geo_layout.setSpacing(8)
        geo_layout.setContentsMargins(15, 15, 15, 15)

        geo_layout.addRow(
            "Position (X, Y):", QLabel(f"{int(self.box.x())}, {int(self.box.y())}")
        )
        geo_layout.addRow(
            "Dimensions:",
            QLabel(f"{int(self.box.p_width)}w × {int(self.box.p_height)}h pixels"),
        )
        geo_layout.addRow(
            "Split Mode:",
            QLabel(
                "<span style='color: #2e8b57; font-weight: bold;'>Active</span>"
                if self.box.isSplit()
                else "Inactive"
            ),
        )

        layout.addWidget(geo_group)
        layout.addStretch()

    def setup_ports_tab(self):
        layout = QVBoxLayout(self.ports_tab)
        layout.setContentsMargins(15, 15, 15, 15)

        port_group = self.create_group_box("Port Configuration")
        form = QFormLayout(port_group)
        form.setSpacing(12)
        form.setContentsMargins(15, 20, 15, 15)

        form.addRow(
            "Total Ports:",
            QLabel(
                f"<span style='font-size: 12pt; font-weight: bold;'>{self.box.getPortCount()}</span>"
            ),
        )

        # Count inputs and outputs
        ins = outs = 0
        for port in canvas.port_list:
            if (
                port.widget.parentItem() == self.box
                and port.port_id in self.box.m_port_list_ids
            ):
                if port.port_mode == PORT_MODE_INPUT:
                    ins += 1
                elif port.port_mode == PORT_MODE_OUTPUT:
                    outs += 1

        form.addRow("Input Ports:", QLabel(str(ins)))
        form.addRow("Output Ports:", QLabel(str(outs)))

        layout.addWidget(port_group)
        layout.addStretch()

    def setup_pipewire_tab(self):
        layout = QVBoxLayout(self.pw_tab)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        if not self.pw_props:
            target_str = f"<b>{self.box.getGroupName()}</b>"
            if getattr(self.box, "pw_node_name", None) and self.box.pw_node_name != self.box.getGroupName():
                target_str += f" (<code>{self.box.pw_node_name}</code>)"
            lbl = QLabel(
                f"Could not find matching PipeWire properties for {target_str}.<br><br>Ensure the node is active and named identically in the PipeWire graph."
            )
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            layout.addStretch()
            return

        # Top Controls Layout
        controls_layout = QHBoxLayout()

        self.pretty_checkbox = QCheckBox("Show user-friendly property names")
        self.pretty_checkbox.setChecked(True)
        self.pretty_checkbox.toggled.connect(self.populate_pw_table)
        controls_layout.addWidget(self.pretty_checkbox)

        controls_layout.addStretch()

        self.btn_copy = QPushButton("Copy JSON")
        self.btn_copy.setToolTip("Copy raw PipeWire JSON to clipboard")
        self.btn_copy.clicked.connect(self.copy_pw_json)
        controls_layout.addWidget(self.btn_copy)

        layout.addLayout(controls_layout)

        # Create a table to show properties
        self.pw_table = QTableWidget(0, 2)
        self.pw_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.pw_table.horizontalHeader().setStretchLastSection(True)
        self.pw_table.setColumnWidth(0, 200)
        self.pw_table.verticalHeader().setVisible(False)
        self.pw_table.setAlternatingRowColors(True)

        # Reduce vertical padding in rows
        self.pw_table.verticalHeader().setDefaultSectionSize(24)

        # Disable editing
        if hasattr(QTableWidget, "EditTrigger"):
            self.pw_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        else:
            self.pw_table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.pw_table)

        # Initial population
        self.populate_pw_table()

    def populate_pw_table(self):
        if not hasattr(self, "pw_table") or not self.pw_props:
            return

        use_pretty = self.pretty_checkbox.isChecked()
        self.pw_table.setRowCount(0)
        self.pw_table.setRowCount(len(self.pw_props))

        for i, (key, val) in enumerate(sorted(self.pw_props.items())):
            display_key = PW_PRETTY_MAP.get(key, key) if use_pretty else key

            key_item = QTableWidgetItem(str(display_key))
            # Keep original raw key in tooltip for power users
            key_item.setToolTip(str(key))

            val_item = QTableWidgetItem(str(val))
            val_item.setToolTip(str(val))

            self.pw_table.setItem(i, 0, key_item)
            self.pw_table.setItem(i, 1, val_item)

    def copy_pw_json(self):
        if self.pw_props:
            QApplication.clipboard().setText(json.dumps(self.pw_props, indent=4))
            self.btn_copy.setText("Copied!")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("Copy JSON"))

    def apply_changes(self):
        # Update name if changed
        new_name = self.name_edit.text()
        if new_name != self.box.getGroupName():
            self.box.setGroupName(new_name)
            self.setWindowTitle(f"{new_name} Properties")

    def accept(self):
        self.apply_changes()
        super().accept()


# ------------------------------------------------------------------------------------------------------------


class CanvasBox(QGraphicsObject):
    # signals
    positionChanged = pyqtSignal(int, bool, int, int)

    # enums
    INLINE_DISPLAY_DISABLED = 0
    INLINE_DISPLAY_ENABLED = 1
    INLINE_DISPLAY_CACHED = 2

    # Box Width Limits
    MIN_BOX_WIDTH = 120  # Sensible minimum width
    MAX_BOX_WIDTH_TITLE = 200  # Max width driven by the title
    MAX_BOX_WIDTH_ABSOLUTE = 350  # Absolute hard limit for the box

    def __init__(self, group_id, group_name, icon, parent=None, pw_node_name=None):
        QGraphicsObject.__init__(self)
        self.setParentItem(parent)

        # Save Variables, useful for later
        self.m_group_id = group_id
        self.m_group_name = group_name
        self.setToolTip(self.m_group_name)

        # PipeWire accepted query name for nodes (node.name)
        self.pw_node_name = pw_node_name or group_name

        # plugin Id, < 0 if invalid
        self.m_plugin_id = -1
        self.m_plugin_ui = False
        self.m_plugin_inline = self.INLINE_DISPLAY_DISABLED

        # Base Variables
        self.p_width = 50
        self.p_width_in = 0
        self.p_width_out = 0
        self.p_height = (
            canvas.theme.box_header_height + canvas.theme.box_header_spacing + 1
        )

        self.m_last_pos = QPointF()
        self.m_split = False
        self.m_split_mode = PORT_MODE_NULL

        self.m_cursor_moving = False
        self.m_forced_split = False
        self.m_mouse_down = False
        self.m_inline_image = None
        self.m_inline_scaling = 1.0
        self.m_inline_first = True
        self.m_will_signal_pos_change = False

        self.m_port_list_ids = []
        self.m_connection_lines = []

        # Set Font
        self.m_font_name = getSystemFont(
            canvas.theme.box_font_size, canvas.theme.box_font_state
        )
        self.m_font_port = getSystemFont(
            canvas.theme.port_font_size, canvas.theme.port_font_state
        )

        # Icon
        if canvas.theme.box_use_icon:
            self.icon_svg = CanvasIcon(icon, self.m_group_name, self)
        else:
            self.icon_svg = None

        # Shadow
        if options.eyecandy and QT_VERSION >= 0x50C00:
            self.shadow = CanvasBoxShadow(self.toGraphicsObject())
            self.shadow.setFakeParent(self)
            self.setGraphicsEffect(self.shadow)
        else:
            self.shadow = None

        # Final touches
        self.setFlags(
            QGraphicsItem.ItemIsFocusable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )

        # Wait for at least 1 port
        if options.auto_hide_groups:
            self.setVisible(False)

        if options.auto_select_items:
            self.setAcceptHoverEvents(True)

        self.updatePositions()

        self.visibleChanged.connect(self.slot_signalPositionChangedLater)
        self.xChanged.connect(self.slot_signalPositionChangedLater)
        self.yChanged.connect(self.slot_signalPositionChangedLater)

        canvas.scene.addItem(self)
        QTimer.singleShot(0, self.fixPos)

    def showPropertiesDialog(self):
        parent_view = (
            self.scene().views()[0] if self.scene() and self.scene().views() else None
        )
        self.prop_dialog = BoxPropertiesDialog(self, parent_view)
        self.prop_dialog.show()

    def getGroupId(self):
        return self.m_group_id

    def getGroupName(self):
        return self.m_group_name

    def getPwNodeName(self):
        return self.pw_node_name

    def setPwNodeName(self, name):
        self.pw_node_name = name

    @property
    def node_name(self):
        return self.pw_node_name

    @node_name.setter
    def node_name(self, value):
        self.pw_node_name = value

    def isSplit(self):
        return self.m_split

    def getSplitMode(self):
        return self.m_split_mode

    def getPortCount(self):
        return len(self.m_port_list_ids)

    def getPortList(self):
        return self.m_port_list_ids

    def redrawInlineDisplay(self):
        if self.m_plugin_inline == self.INLINE_DISPLAY_CACHED:
            self.m_plugin_inline = self.INLINE_DISPLAY_ENABLED
            self.update()

    def removeAsPlugin(self):
        self.m_plugin_id = -1
        self.m_plugin_ui = False
        self.m_plugin_inline = self.INLINE_DISPLAY_DISABLED

    def setAsPlugin(self, plugin_id, hasUI, hasInlineDisplay):
        if hasInlineDisplay and not options.inline_displays:
            hasInlineDisplay = False

        if not hasInlineDisplay:
            self.m_inline_image = None
            self.m_inline_scaling = 1.0

        self.m_plugin_id = plugin_id
        self.m_plugin_ui = hasUI
        self.m_plugin_inline = (
            self.INLINE_DISPLAY_ENABLED
            if hasInlineDisplay
            else self.INLINE_DISPLAY_DISABLED
        )
        self.update()

    def setIcon(self, icon):
        if self.icon_svg is not None:
            self.icon_svg.setIcon(icon, self.m_group_name)

    def setSplit(self, split, mode=PORT_MODE_NULL):
        self.m_split = split
        self.m_split_mode = mode

    def setGroupName(self, group_name):
        self.m_group_name = group_name
        self.setToolTip(self.m_group_name)
        self.updatePositions()

    def setShadowOpacity(self, opacity):
        if self.shadow is not None:
            self.shadow.setOpacity(opacity)

    def addPortFromGroup(
        self,
        port_id,
        port_mode,
        port_type,
        port_name,
        is_alternate,
        backend_group_id=None,
    ):
        if len(self.m_port_list_ids) == 0:
            if options.auto_hide_groups:
                log_carla(
                    f"CanvasBox.addPortFromGroup: unhiding box '{self.m_group_name}' (id={self.m_group_id}) on first port '{port_name}'"
                )
                if options.eyecandy == EYECANDY_FULL:
                    CanvasItemFX(self, True, False)
                self.blockSignals(True)
                self.setVisible(True)
                self.blockSignals(False)

        new_widget = CanvasPort(
            self.m_group_id if backend_group_id is None else backend_group_id,
            port_id,
            port_name,
            port_mode,
            port_type,
            is_alternate,
            self,
        )

        port_dict = port_dict_t()
        port_dict.group_id = self.m_group_id
        port_dict.port_id = port_id
        port_dict.port_name = port_name
        port_dict.port_mode = port_mode
        port_dict.port_type = port_type
        port_dict.is_alternate = is_alternate
        port_dict.widget = new_widget

        self.m_port_list_ids.append(port_id)

        return new_widget

    def removePortFromGroup(self, port_id):
        if port_id in self.m_port_list_ids:
            self.m_port_list_ids.remove(port_id)
        else:
            qCritical(
                "PatchCanvas::CanvasBox.removePort(%i) - unable to find port to remove"
                % port_id
            )
            return

        if len(self.m_port_list_ids) > 0:
            self.updatePositions()

        elif self.isVisible():
            if options.auto_hide_groups:
                if options.eyecandy == EYECANDY_FULL:
                    CanvasItemFX(self, False, False)
                else:
                    self.blockSignals(True)
                    self.setVisible(False)
                    self.blockSignals(False)

    def addLineFromGroup(self, line, connection_id):
        new_cbline = cb_line_t(line, connection_id)
        self.m_connection_lines.append(new_cbline)

    def removeLineFromGroup(self, connection_id):
        for connection in self.m_connection_lines:
            if connection.connection_id == connection_id:
                self.m_connection_lines.remove(connection)
                return
        qCritical(
            "PatchCanvas::CanvasBox.removeLineFromGroup(%i) - unable to find line to remove"
            % connection_id
        )

    def checkItemPos(self):
        if canvas.size_rect.isNull():
            return

        pos = self.scenePos()
        if canvas.size_rect.contains(pos) and canvas.size_rect.contains(
            pos + QPointF(self.p_width, self.p_height)
        ):
            return

        if pos.x() < canvas.size_rect.x():
            self.setPos(canvas.size_rect.x(), pos.y())
        elif pos.x() + self.p_width > canvas.size_rect.width():
            self.setPos(canvas.size_rect.width() - self.p_width, pos.y())

        pos = self.scenePos()
        if pos.y() < canvas.size_rect.y():
            self.setPos(pos.x(), canvas.size_rect.y())
        elif pos.y() + self.p_height > canvas.size_rect.height():
            self.setPos(pos.x(), canvas.size_rect.height() - self.p_height)

    def removeIconFromScene(self):
        if self.icon_svg is None:
            return

        item = self.icon_svg
        self.icon_svg = None
        canvas.scene.removeItem(item)
        del item

    def updatePositions(self):
        self.prepareGeometryChange()

        # Check Text Name size with Hard & Soft Limits
        # Add 30px buffer for margins/icons
        app_name_size = fontHorizontalAdvance(self.m_font_name, self.m_group_name) + 30

        # Apply minimum width and title maximum width
        self.p_width = max(
            self.MIN_BOX_WIDTH, min(app_name_size, self.MAX_BOX_WIDTH_TITLE)
        )

        # Get Port List
        port_list = []
        for port in canvas.port_list:
            if (
                port.widget.parentItem() == self
                and port.port_id in self.m_port_list_ids
            ):
                port_list.append(port)

        if len(port_list) == 0:
            self.p_height = canvas.theme.box_header_height
            self.p_width_in = 0
            self.p_width_out = 0
        else:
            max_in_width = max_out_width = 0
            port_spacing = canvas.theme.port_height + canvas.theme.port_spacing

            # Get Max Box Width, vertical ports re-positioning
            port_types = (
                PORT_TYPE_AUDIO_JACK,
                PORT_TYPE_MIDI_JACK,
                PORT_TYPE_MIDI_ALSA,
                PORT_TYPE_PARAMETER,
            )
            last_in_type = last_out_type = PORT_TYPE_NULL
            last_in_pos = last_out_pos = (
                canvas.theme.box_header_height + canvas.theme.box_header_spacing
            )

            for port_type in port_types:
                for port in port_list:
                    if port.port_type != port_type:
                        continue

                    size = fontHorizontalAdvance(self.m_font_port, port.port_name)

                    if port.port_mode == PORT_MODE_INPUT:
                        max_in_width = max(max_in_width, size)
                        if port.port_type != last_in_type:
                            if last_in_type != PORT_TYPE_NULL:
                                last_in_pos += canvas.theme.port_spacingT
                            last_in_type = port.port_type
                        port.widget.setY(last_in_pos)
                        last_in_pos += port_spacing

                    elif port.port_mode == PORT_MODE_OUTPUT:
                        max_out_width = max(max_out_width, size)
                        if port.port_type != last_out_type:
                            if last_out_type != PORT_TYPE_NULL:
                                last_out_pos += canvas.theme.port_spacingT
                            last_out_type = port.port_type
                        port.widget.setY(last_out_pos)
                        last_out_pos += port_spacing

            self.p_width = max(self.p_width, 30 + max_in_width + max_out_width)
            self.p_width = min(
                self.p_width, self.MAX_BOX_WIDTH_ABSOLUTE
            )  # Absolute hard limit
            self.p_width_in = max_in_width
            self.p_width_out = max_out_width

            self.p_height = max(last_in_pos, last_out_pos)
            self.p_height += (
                max(canvas.theme.port_spacing, canvas.theme.port_spacingT)
                - canvas.theme.port_spacing
            )
            self.p_height += canvas.theme.box_pen.width()

            self.repositionPorts(port_list)

        self.repaintLines(True)
        self.update()

    def repositionPorts(self, port_list=None):
        if port_list is None:
            port_list = []
            for port in canvas.port_list:
                if (
                    port.widget.parentItem() == self
                    and port.port_id in self.m_port_list_ids
                ):
                    port_list.append(port)

        # Horizontal ports re-positioning
        inX = canvas.theme.port_offset
        outX = self.p_width - self.p_width_out - canvas.theme.port_offset - 12
        for port in port_list:
            if port.port_mode == PORT_MODE_INPUT:
                port.widget.setX(inX)
                port.widget.setPortWidth(self.p_width_in)

            elif port.port_mode == PORT_MODE_OUTPUT:
                port.widget.setX(outX)
                port.widget.setPortWidth(self.p_width_out)

    def repaintLines(self, forced=False):
        if self.pos() != self.m_last_pos or forced:
            for connection in self.m_connection_lines:
                connection.line.updateLinePos()

        self.m_last_pos = self.pos()

    def resetLinesZValue(self):
        for connection in canvas.connection_list:
            if (
                connection.port_out_id in self.m_port_list_ids
                and connection.port_in_id in self.m_port_list_ids
            ):
                z_value = canvas.last_z_value
            else:
                z_value = canvas.last_z_value - 1

            connection.widget.setZValue(z_value)

    def triggerSignalPositionChanged(self):
        self.positionChanged.emit(
            self.m_group_id, self.m_split, int(self.x()), int(self.y())
        )
        self.m_will_signal_pos_change = False

    @pyqtSlot()
    def slot_signalPositionChangedLater(self):
        if self.m_will_signal_pos_change:
            return
        self.m_will_signal_pos_change = True
        QTimer.singleShot(0, self.triggerSignalPositionChanged)

    def type(self):
        return CanvasBoxType

    def contextMenuEvent(self, event):
        event.accept()
        menu = QMenu()

        # Conenct menu stuff
        connMenu = QMenu("Connect", menu)

        our_port_types = []
        our_port_outs = {
            PORT_TYPE_AUDIO_JACK: [],
            PORT_TYPE_MIDI_JACK: [],
            PORT_TYPE_MIDI_ALSA: [],
            PORT_TYPE_PARAMETER: [],
        }
        for port in canvas.port_list:
            if port.widget.parentItem() != self:
                continue
            if port.port_mode != PORT_MODE_OUTPUT:
                continue
            if port.port_id not in self.m_port_list_ids:
                continue
            if port.port_type not in our_port_types:
                our_port_types.append(port.port_type)
            our_port_outs[port.port_type].append((port.group_id, port.port_id))

        if len(our_port_types) != 0:
            act_x_conn = None
            for group in canvas.group_list:
                if self.m_group_id == group.group_id:
                    continue

                has_ports = False
                target_ports = {
                    PORT_TYPE_AUDIO_JACK: [],
                    PORT_TYPE_MIDI_JACK: [],
                    PORT_TYPE_MIDI_ALSA: [],
                    PORT_TYPE_PARAMETER: [],
                }

                for port in canvas.port_list:
                    if port.widget.parentItem() != group.widgets[0] and (
                        not group.split or port.widget.parentItem() != group.widgets[1]
                    ):
                        continue
                    if port.port_mode != PORT_MODE_INPUT:
                        continue
                    if port.port_type not in our_port_types:
                        continue
                    has_ports = True
                    target_ports[port.port_type].append((port.group_id, port.port_id))

                if not has_ports:
                    continue

                act_x_conn = connMenu.addAction(group.group_name)
                act_x_conn.setData((our_port_outs, target_ports))
                act_x_conn.triggered.connect(canvas.qobject.PortContextMenuConnect)

            if act_x_conn is None:
                act_x_disc = connMenu.addAction("Nothing to connect to")
                act_x_disc.setEnabled(False)

        else:
            act_x_disc = connMenu.addAction("No output ports")
            act_x_disc.setEnabled(False)

        # Disconnect menu stuff
        discMenu = QMenu("Disconnect", menu)

        conn_list = []
        conn_list_ids = []

        for port_id in self.m_port_list_ids:
            tmp_conn_list = CanvasGetPortConnectionList(self.m_group_id, port_id)
            for tmp_conn_id, tmp_group_id, tmp_port_id in tmp_conn_list:
                if tmp_conn_id not in conn_list_ids:
                    conn_list.append((tmp_conn_id, tmp_group_id, tmp_port_id))
                    conn_list_ids.append(tmp_conn_id)

        if len(conn_list) > 0:
            for conn_id, group_id, port_id in conn_list:
                act_x_disc = discMenu.addAction(
                    CanvasGetFullPortName(group_id, port_id)
                )
                act_x_disc.setData(conn_id)
                act_x_disc.triggered.connect(canvas.qobject.PortContextMenuDisconnect)
        else:
            act_x_disc = discMenu.addAction("No connections")
            act_x_disc.setEnabled(False)

        menu.addMenu(connMenu)
        menu.addMenu(discMenu)
        act_x_disc_all = menu.addAction("Disconnect &All")
        act_x_sep1 = menu.addSeparator()
        act_x_info = menu.addAction("Info")
        act_x_rename = menu.addAction("Rename")
        act_x_sep2 = menu.addSeparator()
        act_x_split_join = menu.addAction("Join" if self.m_split else "Split")

        menu.addSeparator()
        act_x_properties = menu.addAction("Properties")

        if not features.group_info:
            act_x_info.setVisible(False)

        if not features.group_rename:
            act_x_rename.setVisible(False)

        if not (features.group_info and features.group_rename):
            act_x_sep1.setVisible(False)

        if self.m_plugin_id >= 0 and self.m_plugin_id <= MAX_PLUGIN_ID_ALLOWED:
            menu.addSeparator()
            act_p_edit = menu.addAction("Edit")
            act_p_ui = menu.addAction("Show Custom UI")
            menu.addSeparator()
            act_p_clone = menu.addAction("Clone")
            act_p_rename = menu.addAction("Rename...")
            act_p_replace = menu.addAction("Replace...")
            act_p_remove = menu.addAction("Remove")

            if not self.m_plugin_ui:
                act_p_ui.setVisible(False)

        else:
            act_p_edit = act_p_ui = None
            act_p_clone = act_p_rename = None
            act_p_replace = act_p_remove = None

        haveIns = haveOuts = False
        for port in canvas.port_list:
            if (
                port.group_id == self.m_group_id
                and port.port_id in self.m_port_list_ids
            ):
                if port.port_mode == PORT_MODE_INPUT:
                    haveIns = True
                elif port.port_mode == PORT_MODE_OUTPUT:
                    haveOuts = True

        if not (self.m_split or bool(haveIns and haveOuts)):
            act_x_sep2.setVisible(False)
            act_x_split_join.setVisible(False)

        act_selected = menu.exec_(event.screenPos())

        if act_selected is None:
            pass

        elif act_selected == act_x_properties:
            self.showPropertiesDialog()

        elif act_selected == act_x_disc_all:
            for conn_id in conn_list_ids:
                canvas.callback(ACTION_PORTS_DISCONNECT, conn_id, 0, "")

        elif act_selected == act_x_info:
            canvas.callback(ACTION_GROUP_INFO, self.m_group_id, 0, "")

        elif act_selected == act_x_rename:
            canvas.callback(ACTION_GROUP_RENAME, self.m_group_id, 0, "")

        elif act_selected == act_x_split_join:
            if self.m_split:
                canvas.callback(ACTION_GROUP_JOIN, self.m_group_id, 0, "")
            else:
                canvas.callback(ACTION_GROUP_SPLIT, self.m_group_id, 0, "")

        elif act_selected == act_p_edit:
            canvas.callback(ACTION_PLUGIN_EDIT, self.m_plugin_id, 0, "")

        elif act_selected == act_p_ui:
            canvas.callback(ACTION_PLUGIN_SHOW_UI, self.m_plugin_id, 0, "")

        elif act_selected == act_p_clone:
            canvas.callback(ACTION_PLUGIN_CLONE, self.m_plugin_id, 0, "")

        elif act_selected == act_p_rename:
            canvas.callback(ACTION_PLUGIN_RENAME, self.m_plugin_id, 0, "")

        elif act_selected == act_p_replace:
            canvas.callback(ACTION_PLUGIN_REPLACE, self.m_plugin_id, 0, "")

        elif act_selected == act_p_remove:
            canvas.callback(ACTION_PLUGIN_REMOVE, self.m_plugin_id, 0, "")

    def keyPressEvent(self, event):
        if self.m_plugin_id >= 0 and event.key() == Qt.Key_Delete:
            event.accept()
            canvas.callback(ACTION_PLUGIN_REMOVE, self.m_plugin_id, 0, "")
            return
        QGraphicsObject.keyPressEvent(self, event)

    def hoverEnterEvent(self, event):
        if options.auto_select_items:
            if len(canvas.scene.selectedItems()) > 0:
                canvas.scene.clearSelection()
            self.setSelected(True)
        QGraphicsObject.hoverEnterEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        if self.m_plugin_id >= 0:
            event.accept()
            canvas.callback(
                ACTION_PLUGIN_SHOW_UI if self.m_plugin_ui else ACTION_PLUGIN_EDIT,
                self.m_plugin_id,
                0,
                "",
            )
            return

        QGraphicsObject.mouseDoubleClickEvent(self, event)

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MiddleButton
            or event.source() == Qt.MouseEventSynthesizedByApplication
        ):
            event.ignore()
            return

        canvas.last_z_value += 1
        self.setZValue(canvas.last_z_value)
        self.resetLinesZValue()
        self.m_cursor_moving = False

        if event.button() == Qt.RightButton:
            event.accept()
            canvas.scene.clearSelection()
            self.setSelected(True)
            self.m_mouse_down = False
            return

        elif event.button() == Qt.LeftButton:
            if self.sceneBoundingRect().contains(event.scenePos()):
                self.m_mouse_down = True
            else:
                # FIXME: Check if still valid: Fix a weird Qt behaviour with right-click mouseMove
                self.m_mouse_down = False
                event.ignore()
                return

        else:
            self.m_mouse_down = False

        QGraphicsObject.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.m_mouse_down:
            if not self.m_cursor_moving:
                self.setCursor(QCursor(Qt.SizeAllCursor))
                self.m_cursor_moving = True
            self.repaintLines()
        QGraphicsObject.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.m_cursor_moving:
            self.unsetCursor()
            QTimer.singleShot(0, self.fixPos)
        self.m_mouse_down = False
        self.m_cursor_moving = False
        QGraphicsObject.mouseReleaseEvent(self, event)

    def fixPos(self):
        self.blockSignals(True)
        self.setX(round(self.x()))
        self.setY(round(self.y()))
        self.blockSignals(False)

    def boundingRect(self):
        return QRectF(0, 0, self.p_width, self.p_height)

    def shape(self):
        path = QPainterPath()
        radius = options.node_radius if getattr(options, "rounded_nodes", False) else 0
        if radius > 0:
            path.addRoundedRect(
                QRectF(0, 0, self.p_width, self.p_height), radius, radius
            )
        else:
            path.addRect(QRectF(0, 0, self.p_width, self.p_height))
        return path

    def updateTheme(self):
        self.m_font_name = getSystemFont(
            canvas.theme.box_font_size, canvas.theme.box_font_state
        )
        self.m_font_port = getSystemFont(
            canvas.theme.port_font_size, canvas.theme.port_font_state
        )
        if self.shadow is not None:
            self.shadow.setColor(canvas.theme.box_shadow)
        self.update()

    def paint(self, painter, option, widget):
        painter.save()
        radius = options.node_radius if getattr(options, "rounded_nodes", False) else 0
        painter.setRenderHint(
            QPainter.Antialiasing,
            bool(options.antialiasing == ANTIALIASING_FULL or radius > 0),
        )
        rect = QRectF(0, 0, self.p_width, self.p_height)

        # Draw rectangle
        pen = QPen(
            canvas.theme.box_pen_sel if self.isSelected() else canvas.theme.box_pen
        )
        pen.setWidthF(pen.widthF() + 0.00001)
        painter.setPen(pen)
        lineHinting = pen.widthF() / 2

        if canvas.theme.box_bg_type == Theme.THEME_BG_GRADIENT:
            box_gradient = QLinearGradient(0, 0, 0, self.p_height)
            box_gradient.setColorAt(0, canvas.theme.box_bg_1)
            box_gradient.setColorAt(1, canvas.theme.box_bg_2)
            painter.setBrush(box_gradient)
        else:
            painter.setBrush(canvas.theme.box_bg_1)

        rect.adjust(lineHinting, lineHinting, -lineHinting, -lineHinting)
        if radius > 0:
            painter.drawRoundedRect(rect, radius, radius)
        else:
            painter.drawRect(rect)

        # Draw plugin inline display if supported
        self.paintInlineDisplay(painter)

        # Draw header
        header_height = canvas.theme.box_header_height
        if header_height > 0:
            header_rect = QRectF(
                lineHinting, lineHinting, self.p_width - 2 * lineHinting, header_height
            )
            painter.save()
            if radius > 0:
                header_clip = QPainterPath()
                header_clip.addRoundedRect(rect, radius, radius)
                clipOp = (
                    Qt.ClipOperation.IntersectClip
                    if hasattr(Qt, "ClipOperation")
                    else Qt.IntersectClip
                )
                painter.setClipPath(header_clip, clipOp)

            if canvas.theme.box_header_pixmap:
                painter.setPen(Qt.NoPen)
                painter.setBrush(canvas.theme.box_bg_2)
                painter.drawRect(header_rect)
                painter.drawTiledPixmap(
                    header_rect, canvas.theme.box_header_pixmap, header_rect.topLeft()
                )
            else:
                header_bg = canvas.theme.box_bg_2
                if header_bg:
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(header_bg)
                    painter.drawRect(header_rect)
                    painter.setPen(canvas.theme.box_pen)
                    painter.drawLine(
                        QPointF(header_rect.left(), header_rect.bottom()),
                        QPointF(header_rect.right(), header_rect.bottom()),
                    )

            painter.restore()

        # Draw text (Truncated with Ellipsis)
        painter.setFont(self.m_font_name)

        if self.isSelected():
            painter.setPen(canvas.theme.box_text_sel)
        else:
            painter.setPen(canvas.theme.box_text)

        metrics = QFontMetrics(self.m_font_name)
        elide_mode = (
            Qt.TextElideMode.ElideRight
            if hasattr(Qt, "TextElideMode")
            else Qt.ElideRight
        )

        # Calculate available width with safer padding
        if canvas.theme.box_use_icon:
            available_width = self.p_width - 35  # Account for icon width + padding
            textPos = QPointF(25, canvas.theme.box_text_ypos)
        else:
            available_width = self.p_width - 20  # 10px padding on each side

        # Truncate string gracefully based on available pixel width
        elided_name = metrics.elidedText(
            self.m_group_name, elide_mode, int(max(0, available_width))
        )

        if not canvas.theme.box_use_icon:
            # Re-center based on the actual drawn (potentially elided) text size
            drawn_name_size = fontHorizontalAdvance(self.m_font_name, elided_name)
            rem = self.p_width - drawn_name_size
            textPos = QPointF(rem / 2, canvas.theme.box_text_ypos)

        painter.drawText(textPos, elided_name)

        painter.restore()

    def paintInlineDisplay(self, painter):
        if self.m_plugin_inline == self.INLINE_DISPLAY_DISABLED:
            return
        if not options.inline_displays:
            return

        inwidth = self.p_width - 16 - self.p_width_in - self.p_width_out
        inheight = (
            self.p_height
            - 3
            - canvas.theme.box_header_height
            - canvas.theme.box_header_spacing
            - canvas.theme.port_spacing
        )

        scaling = canvas.scene.getScaleFactor() * canvas.scene.getDevicePixelRatioF()

        if (
            self.m_plugin_id >= 0
            and self.m_plugin_id <= MAX_PLUGIN_ID_ALLOWED
            and (
                self.m_plugin_inline == self.INLINE_DISPLAY_ENABLED
                or self.m_inline_scaling != scaling
            )
        ):
            if self.m_inline_first:
                size = "%i:%i" % (int(50 * scaling), int(50 * scaling))
            else:
                size = "%i:%i" % (int(inwidth * scaling), int(inheight * scaling))
            data = canvas.callback(ACTION_INLINE_DISPLAY, self.m_plugin_id, 0, size)
            if data is None:
                return

            img_format = (
                QImage.Format.Format_ARGB32 if qt_config == 6 else QImage.Format_ARGB32
            )
            self.m_inline_image = QImage(
                data["data"],
                data["width"],
                data["height"],
                data["stride"],
                img_format,
            ).copy()
            self.m_inline_scaling = scaling
            self.m_plugin_inline = self.INLINE_DISPLAY_CACHED

            # make room for inline display, in a square shape
            if self.m_inline_first:
                self.m_inline_first = False
                aspectRatio = data["width"] / data["height"]
                self.p_height = int(max(50 * scaling, self.p_height))
                self.p_width += int(
                    max(
                        0,
                        min(
                            (80 - 14) * scaling,
                            (inheight - inwidth) * aspectRatio * scaling,
                        ),
                    )
                )
                self.repositionPorts()
                self.repaintLines(True)
                self.update()
                return

        if self.m_inline_image is None:
            print(
                "ERROR: inline display image is None for",
                self.m_plugin_id,
                self.m_group_name,
            )
            return

        swidth = self.m_inline_image.width() / scaling
        sheight = self.m_inline_image.height() / scaling

        srcx = int(
            self.p_width_in
            + (self.p_width - self.p_width_in - self.p_width_out) / 2
            - swidth / 2
        )
        srcy = int(
            canvas.theme.box_header_height
            + canvas.theme.box_header_spacing
            + 1
            + (inheight - sheight) / 2
        )

        painter.drawImage(QRectF(srcx, srcy, swidth, sheight), self.m_inline_image)

    def itemChange(self, change, value):
        from qt_compat import qt_config

        pos_change = 1
        if qt_config == 6:
            from PyQt6.QtWidgets import QGraphicsItem

            pos_change = QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged

        if change == pos_change or change == 1:
            self.repaintLines()
            self.slot_signalPositionChangedLater()

        return super().itemChange(change, value)


# ------------------------------------------------------------------------------------------------------------
