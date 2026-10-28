#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Carla Improved (Clara) - Patchbay Layout Container
# Non-destructive backdrop container (VBox, HBox, Grid) for grouping canvas nodes.

from qt_compat import (
    QAction,
    QColor,
    QColorDialog,
    QFont,
    QGraphicsItem,
    QGraphicsObject,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPainter,
    QPainterPath,
    QPen,
    QPointF,
    QRectF,
    Qt,
)

from . import (
    canvas,
    CanvasBoxType,
    CanvasContainerType,
    options,
)

CONTAINER_LAYOUT_VBOX = "vbox"
CONTAINER_LAYOUT_HBOX = "hbox"
CONTAINER_LAYOUT_GRID = "grid"
CONTAINER_LAYOUT_FREEFORM = "freeform"

CONTAINER_PADDING = 14.0
CONTAINER_HEADER_HEIGHT = 28.0
CONTAINER_ITEM_SPACING = 12.0
CONTAINER_MIN_WIDTH = 220.0

CATPPUCCIN_PALETTE = [
    ("Blue", "#89b4fa"),
    ("Mauve", "#cba6f7"),
    ("Green", "#a6e3a1"),
    ("Peach", "#fab387"),
    ("Teal", "#94e2d5"),
    ("Lavender", "#b4befe"),
    ("Flamingo", "#f2cdcd"),
    ("Red", "#f38ba8"),
    ("Yellow", "#f9e2af"),
]


class CanvasContainer(QGraphicsObject):
    """
    Backdrop layout container for grouping patchbay nodes.
    Placed behind canvas items (z = -10). Moves child nodes without reparenting them,
    preserving cable trajectories and native port coordinates.
    """

    def __init__(self, container_id, title="Group", layout_mode=CONTAINER_LAYOUT_VBOX, parent=None):
        super().__init__(parent)

        self.m_id = container_id
        self.m_title = title
        self.m_layout_mode = layout_mode
        self.m_collapsed = False
        self.m_color = QColor("#89b4fa")  # Catppuccin Blue default

        # Ordered list of child CanvasBox items currently attached
        self.m_items = []
        # Relative coordinate offsets: box -> (rel_x, rel_y) from container origin
        self.m_item_offsets = {}
        # Standby/ghost member descriptors: [{"plugin_id": ..., "pw_node_name": ..., "name": ..., "split_mode": ...}]
        self.m_standby_descriptors = []

        # Geometry
        self.m_width = CONTAINER_MIN_WIDTH
        self.m_height = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2
        self.m_expanded_height = self.m_height

        # Interaction state
        self.m_is_dragging = False
        self.m_drag_start_item_pos = QPointF(0, 0)
        self.m_drag_start_mouse_pos = QPointF(0, 0)
        self.m_hover_insert_idx = None
        self.m_active_hover_box = None

        # Graphics item configuration - strictly NO ItemIsMovable to avoid dual-offset drift!
        self.setZValue(-10.0)
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def type(self):
        return CanvasContainerType

    def boundingRect(self):
        h = CONTAINER_HEADER_HEIGHT if self.m_collapsed else self.m_height
        return QRectF(0, 0, self.m_width, h)

    def shape(self):
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 8.0, 8.0)
        return path

    # -------------------------------------------------------------------------
    # Member & Lifecycle Management
    # -------------------------------------------------------------------------

    @staticmethod
    def getBoxDescriptor(box):
        """Generates a stable composite identifier for a CanvasBox."""
        return {
            "plugin_id": getattr(box, "m_plugin_id", -1),
            "pw_node_name": getattr(box, "pw_node_name", None),
            "name": getattr(box, "m_group_name", ""),
            "split_mode": getattr(box, "m_split_mode", 0) if hasattr(box, "m_split_mode") else (1 if getattr(box, "isSplit", lambda: False)() else 0),
        }

    def matchesDescriptor(self, box, desc):
        """Checks if a CanvasBox matches a stored descriptor."""
        p_id = getattr(box, "m_plugin_id", -1)
        if p_id >= 0 and desc.get("plugin_id", -1) >= 0:
            return p_id == desc.get("plugin_id")

        pw_name = getattr(box, "pw_node_name", None)
        if pw_name and desc.get("pw_node_name"):
            return pw_name == desc.get("pw_node_name")

        return getattr(box, "m_group_name", "") == desc.get("name")

    def addItem(self, box, index=None):
        if box in self.m_items:
            return
        if index is None or index < 0 or index > len(self.m_items):
            self.m_items.append(box)
        else:
            self.m_items.insert(index, box)

        setattr(box, "_canvas_container", self)
        # Remove from standby list if it was resting there
        self.m_standby_descriptors = [
            d for d in self.m_standby_descriptors if not self.matchesDescriptor(box, d)
        ]
        self.updateLayout()

    def removeItem(self, box, to_standby=False):
        if box in self.m_items:
            self.m_items.remove(box)
            if box in self.m_item_offsets:
                del self.m_item_offsets[box]
            if hasattr(box, "_canvas_container"):
                delattr(box, "_canvas_container")
            if to_standby:
                desc = self.getBoxDescriptor(box)
                if desc not in self.m_standby_descriptors:
                    self.m_standby_descriptors.append(desc)
            self.updateLayout()

    def containsBox(self, box):
        return box in self.m_items

    # -------------------------------------------------------------------------
    # Layout Solvers
    # -------------------------------------------------------------------------

    def addFreeformItem(self, box, rel_x=None, rel_y=None):
        if box not in self.m_items:
            self.m_items.append(box)
        setattr(box, "_canvas_container", self)
        if rel_x is None or rel_y is None:
            rel_x = box.x() - self.x()
            rel_y = box.y() - self.y()
        self.m_item_offsets[box] = (max(CONTAINER_PADDING, rel_x), max(CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING, rel_y))
        self.updateLayout()

    def updateLayout(self):
        """Computes positions of member nodes and resizes container frame with zero drift."""
        if not self.m_items:
            self.prepareGeometryChange()
            self.m_width = CONTAINER_MIN_WIDTH
            self.m_height = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2
            self.m_item_offsets.clear()
            self.update()
            return

        start_rel_x = CONTAINER_PADDING
        start_rel_y = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING

        if self.m_layout_mode == CONTAINER_LAYOUT_FREEFORM:
            # Calculate bounding hull of child nodes relative to container origin
            min_x = min_y = float("inf")
            max_r = max_b = float("-inf")
            for box in self.m_items:
                if box not in self.m_item_offsets:
                    self.m_item_offsets[box] = (max(start_rel_x, box.x() - self.x()), max(start_rel_y, box.y() - self.y()))
                rx, ry = self.m_item_offsets[box]
                min_x = min(min_x, rx)
                min_y = min(min_y, ry)
                max_r = max(max_r, rx + box.boundingRect().width())
                max_b = max(max_b, ry + box.boundingRect().height())

            new_w = max(CONTAINER_MIN_WIDTH, max_r + CONTAINER_PADDING)
            new_h = max(CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2, max_b + CONTAINER_PADDING)

        elif self.m_layout_mode == CONTAINER_LAYOUT_VBOX:
            self.m_item_offsets.clear()
            max_w = max(b.boundingRect().width() for b in self.m_items)
            current_y = start_rel_y
            for box in self.m_items:
                self.m_item_offsets[box] = (start_rel_x, current_y)
                current_y += box.boundingRect().height() + CONTAINER_ITEM_SPACING

            total_h = current_y - start_rel_y - CONTAINER_ITEM_SPACING
            new_w = max(CONTAINER_MIN_WIDTH, max_w + CONTAINER_PADDING * 2)
            new_h = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2 + total_h

        elif self.m_layout_mode == CONTAINER_LAYOUT_HBOX:
            self.m_item_offsets.clear()
            max_h = max(b.boundingRect().height() for b in self.m_items)
            current_x = start_rel_x
            for box in self.m_items:
                self.m_item_offsets[box] = (current_x, start_rel_y)
                current_x += box.boundingRect().width() + CONTAINER_ITEM_SPACING

            total_w = current_x - start_rel_x - CONTAINER_ITEM_SPACING
            new_w = max(CONTAINER_MIN_WIDTH, total_w + CONTAINER_PADDING * 2)
            new_h = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2 + max_h

        else:  # Grid (2-column default)
            self.m_item_offsets.clear()
            cols = 2
            col_widths = [0] * cols
            for idx, box in enumerate(self.m_items):
                c = idx % cols
                col_widths[c] = max(col_widths[c], box.boundingRect().width())

            current_y = start_rel_y
            row_max_h = 0
            for idx, box in enumerate(self.m_items):
                c = idx % cols
                if c == 0 and idx > 0:
                    current_y += row_max_h + CONTAINER_ITEM_SPACING
                    row_max_h = 0
                bx = start_rel_x if c == 0 else start_rel_x + col_widths[0] + CONTAINER_ITEM_SPACING
                self.m_item_offsets[box] = (bx, current_y)
                row_max_h = max(row_max_h, box.boundingRect().height())

            total_w = sum(col_widths) + (cols - 1) * CONTAINER_ITEM_SPACING
            total_h = (current_y + row_max_h) - start_rel_y
            new_w = max(CONTAINER_MIN_WIDTH, total_w + CONTAINER_PADDING * 2)
            new_h = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2 + total_h

        self.prepareGeometryChange()
        self.m_width = new_w
        self.m_height = new_h
        if not self.m_collapsed:
            self.m_expanded_height = new_h

        # Apply absolute coordinates strictly anchored to container origin
        self.syncChildrenPositions()
        self.update()

    def syncChildrenPositions(self):
        """Positions all child boxes precisely at container.pos() + offset without cumulative drift."""
        c_pos = self.pos()
        visible = not self.m_collapsed
        for box, (rel_x, rel_y) in self.m_item_offsets.items():
            box.setVisible(visible)
            if visible:
                box.blockSignals(True)
                box.setPos(c_pos.x() + rel_x, c_pos.y() + rel_y)
                box.blockSignals(False)
                box.repaintLines()
                for conn in box.m_connection_lines:
                    conn.line.setVisible(True)
            else:
                for conn in box.m_connection_lines:
                    conn.line.setVisible(False)

    def toggleCollapse(self):
        self.m_collapsed = not self.m_collapsed
        self.prepareGeometryChange()
        self.syncChildrenPositions()
        self.update()

    # -------------------------------------------------------------------------
    # Drag & Drop Interception
    # -------------------------------------------------------------------------

    def calculateInsertionIndex(self, scene_pos):
        """Calculates nearest insertion slot index based on mouse scene coordinates."""
        if not self.m_items:
            return 0

        if self.m_layout_mode == CONTAINER_LAYOUT_VBOX:
            target_y = scene_pos.y()
            for idx, box in enumerate(self.m_items):
                b_center_y = box.scenePos().y() + box.boundingRect().height() / 2.0
                if target_y < b_center_y:
                    return idx
            return len(self.m_items)

        elif self.m_layout_mode == CONTAINER_LAYOUT_HBOX:
            target_x = scene_pos.x()
            for idx, box in enumerate(self.m_items):
                b_center_x = box.scenePos().x() + box.boundingRect().width() / 2.0
                if target_x < b_center_x:
                    return idx
            return len(self.m_items)

        return len(self.m_items)

    def setHoverPreview(self, box, scene_pos):
        self.m_active_hover_box = box
        self.m_hover_insert_idx = self.calculateInsertionIndex(scene_pos)
        self.update()

    def clearHoverPreview(self):
        if self.m_hover_insert_idx is not None or self.m_active_hover_box is not None:
            self.m_hover_insert_idx = None
            self.m_active_hover_box = None
            self.update()

    # -------------------------------------------------------------------------
    # Movement Lockstep (Zero Drift)
    # -------------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            rect = self.boundingRect()

            # Check header controls
            if pos.y() <= CONTAINER_HEADER_HEIGHT:
                # Close/ungroup button: [✕] at very right
                if pos.x() >= rect.width() - 24:
                    event.accept()
                    self.ungroup()
                    return

                # Collapse / Expand button: [-] / [+]
                if rect.width() - 48 <= pos.x() < rect.width() - 26:
                    event.accept()
                    self.toggleCollapse()
                    return

                # Layout switcher badge: [VBOX/HBOX/GRID/FREE]
                if rect.width() - 110 <= pos.x() < rect.width() - 50:
                    event.accept()
                    modes = [CONTAINER_LAYOUT_VBOX, CONTAINER_LAYOUT_HBOX, CONTAINER_LAYOUT_GRID, CONTAINER_LAYOUT_FREEFORM]
                    next_idx = (modes.index(self.m_layout_mode) + 1) % len(modes)
                    self.m_layout_mode = modes[next_idx]
                    self.updateLayout()
                    return

            self.m_is_dragging = True
            self.m_drag_start_item_pos = self.pos()
            self.m_drag_start_mouse_pos = event.scenePos()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.m_is_dragging:
            delta = event.scenePos() - self.m_drag_start_mouse_pos
            # Set absolute item position
            self.setPos(self.m_drag_start_item_pos + delta)
            # Re-anchor children with zero drift
            self.syncChildrenPositions()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.m_is_dragging:
            self.m_is_dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() <= CONTAINER_HEADER_HEIGHT:
            event.accept()
            self.promptRename()
            return
        super().mouseDoubleClickEvent(event)

    # -------------------------------------------------------------------------
    # Context Menu & Actions
    # -------------------------------------------------------------------------

    def contextMenuEvent(self, event):
        menu = QMenu()

        act_rename = menu.addAction("Rename...")
        act_rename.triggered.connect(self.promptRename)

        # Layout Modes
        layout_menu = menu.addMenu("Layout Mode")
        act_vbox = layout_menu.addAction("VBox (Vertical)")
        act_hbox = layout_menu.addAction("HBox (Horizontal)")
        act_grid = layout_menu.addAction("Grid (Matrix)")
        act_freeform = layout_menu.addAction("Freeform (Unconstrained)")
        act_vbox.setCheckable(True)
        act_hbox.setCheckable(True)
        act_grid.setCheckable(True)
        act_freeform.setCheckable(True)
        act_vbox.setChecked(self.m_layout_mode == CONTAINER_LAYOUT_VBOX)
        act_hbox.setChecked(self.m_layout_mode == CONTAINER_LAYOUT_HBOX)
        act_grid.setChecked(self.m_layout_mode == CONTAINER_LAYOUT_GRID)
        act_freeform.setChecked(self.m_layout_mode == CONTAINER_LAYOUT_FREEFORM)

        act_vbox.triggered.connect(lambda: self.setLayoutMode(CONTAINER_LAYOUT_VBOX))
        act_hbox.triggered.connect(lambda: self.setLayoutMode(CONTAINER_LAYOUT_HBOX))
        act_grid.triggered.connect(lambda: self.setLayoutMode(CONTAINER_LAYOUT_GRID))
        act_freeform.triggered.connect(lambda: self.setLayoutMode(CONTAINER_LAYOUT_FREEFORM))

        # Color Accent
        color_menu = menu.addMenu("Color Accent")
        for label, hex_code in CATPPUCCIN_PALETTE:
            act_c = color_menu.addAction(label)
            act_c.triggered.connect(lambda checked=False, col=hex_code: self.setColor(QColor(col)))
        color_menu.addSeparator()
        act_custom_col = color_menu.addAction("Custom Color...")
        act_custom_col.triggered.connect(self.promptCustomColor)

        menu.addSeparator()

        act_collapse = menu.addAction("Expand" if self.m_collapsed else "Collapse")
        act_collapse.triggered.connect(self.toggleCollapse)

        act_ungroup = menu.addAction("Ungroup Container")
        act_ungroup.triggered.connect(self.ungroup)

        menu.exec_(event.screenPos())
        event.accept()

    def promptRename(self):
        new_title, ok = QInputDialog.getText(
            None, "Rename Group", "Enter container title:", QLineEdit.Normal, self.m_title
        )
        if ok and new_title.strip():
            self.m_title = new_title.strip()
            self.update()

    def promptCustomColor(self):
        chosen = QColorDialog.getColor(self.m_color, None, "Select Container Accent Color")
        if chosen.isValid():
            self.setColor(chosen)

    def setColor(self, color):
        self.m_color = color
        self.update()

    def setLayoutMode(self, mode):
        self.m_layout_mode = mode
        self.updateLayout()

    def ungroup(self):
        reply = QMessageBox.question(
            None,
            "Ungroup Container",
            f"Are you sure you want to ungroup '{self.m_title}'?\nAll items will remain on the canvas.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        from .patchcanvas import ungroupNode
        # Ensure all boxes are visible and keep their current canvas coordinates
        if self.m_collapsed:
            self.toggleCollapse()

        for b in list(self.m_items):
            ungroupNode(b)

    # -------------------------------------------------------------------------
    # Painting & Visual Rendering
    # -------------------------------------------------------------------------

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.boundingRect()

        # 1. Background Frame Panel
        bg_color = QColor(24, 25, 38, 195)  # Catppuccin Macchiato mantle
        painter.setBrush(bg_color)
        pen_color = self.m_color
        pen = QPen(pen_color, 1.5)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 8.0, 8.0)

        # 2. Header Bar
        header_rect = QRectF(0, 0, rect.width(), CONTAINER_HEADER_HEIGHT)
        header_path = QPainterPath()
        header_path.addRoundedRect(header_rect, 8.0, 8.0)
        painter.fillPath(header_path, QColor(pen_color.red(), pen_color.green(), pen_color.blue(), 50))

        # Title text
        painter.setPen(QColor(220, 224, 232))
        font = QFont(painter.font())
        font.setBold(True)
        font.setPixelSize(12)
        painter.setFont(font)
        painter.drawText(QRectF(10, 0, rect.width() - 120, CONTAINER_HEADER_HEIGHT), Qt.AlignVCenter | Qt.AlignLeft, self.m_title)

        # Layout badge [VBOX / HBOX / GRID]
        badge_text = self.m_layout_mode.upper()
        painter.setPen(QColor(180, 190, 210))
        font.setBold(False)
        font.setPixelSize(10)
        painter.setFont(font)
        painter.drawText(QRectF(rect.width() - 110, 0, 55, CONTAINER_HEADER_HEIGHT), Qt.AlignVCenter | Qt.AlignRight, f"[{badge_text}]")

        # Collapse toggle [-] / [+]
        collapse_char = "[+]" if self.m_collapsed else "[-]"
        painter.setPen(QColor(180, 190, 210))
        painter.drawText(QRectF(rect.width() - 48, 0, 20, CONTAINER_HEADER_HEIGHT), Qt.AlignVCenter | Qt.AlignCenter, collapse_char)

        # Close / ungroup button [✕]
        painter.setPen(QColor(235, 160, 172))
        font.setBold(True)
        font.setPixelSize(11)
        painter.setFont(font)
        painter.drawText(QRectF(rect.width() - 24, 0, 16, CONTAINER_HEADER_HEIGHT), Qt.AlignVCenter | Qt.AlignCenter, "✕")

        if self.m_collapsed:
            return

        # 3. Disconnected standby chip notice if items are unplugged
        if self.m_standby_descriptors:
            standby_cnt = len(self.m_standby_descriptors)
            painter.setPen(QColor(243, 139, 168, 180))  # Catppuccin Red/Pink
            font.setItalic(True)
            font.setPixelSize(10)
            painter.setFont(font)
            painter.drawText(
                QRectF(10, rect.height() - 18, rect.width() - 20, 14),
                Qt.AlignVCenter | Qt.AlignLeft,
                f"• {standby_cnt} item{'s' if standby_cnt > 1 else ''} standby (unplugged)",
            )

        # 4. Interactive Drop Slot Indicator Line
        if self.m_hover_insert_idx is not None:
            painter.setPen(QPen(QColor("#a6e3a1"), 2.5, Qt.DashLine))
            if self.m_layout_mode == CONTAINER_LAYOUT_VBOX:
                if self.m_hover_insert_idx < len(self.m_items):
                    b = self.m_items[self.m_hover_insert_idx]
                    local_y = b.y() - self.y() - CONTAINER_ITEM_SPACING / 2.0
                else:
                    local_y = rect.height() - CONTAINER_PADDING / 2.0
                painter.drawLine(QPointF(CONTAINER_PADDING, local_y), QPointF(rect.width() - CONTAINER_PADDING, local_y))
            elif self.m_layout_mode == CONTAINER_LAYOUT_HBOX:
                if self.m_hover_insert_idx < len(self.m_items):
                    b = self.m_items[self.m_hover_insert_idx]
                    local_x = b.x() - self.x() - CONTAINER_ITEM_SPACING / 2.0
                else:
                    local_x = rect.width() - CONTAINER_PADDING / 2.0
                painter.drawLine(QPointF(local_x, CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING), QPointF(local_x, rect.height() - CONTAINER_PADDING))
