#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Carla Improved (Clara) - Patchbay Layout Container
# Non-destructive backdrop container (VBox, HBox, Grid) for grouping canvas nodes.

from qt_compat import (
    QColor,
    QFont,
    QGraphicsItem,
    QGraphicsObject,
    QLinearGradient,
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

CONTAINER_PADDING = 14.0
CONTAINER_HEADER_HEIGHT = 28.0
CONTAINER_ITEM_SPACING = 12.0
CONTAINER_MIN_WIDTH = 200.0


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
        # Standby/ghost member descriptors: [{"plugin_id": ..., "pw_node_name": ..., "name": ..., "split_mode": ...}]
        self.m_standby_descriptors = []

        # Geometry
        self.m_width = CONTAINER_MIN_WIDTH
        self.m_height = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2
        self.m_target_rect = QRectF(0, 0, self.m_width, self.m_height)

        # Interaction state
        self.m_is_dragging = False
        self.m_last_scene_pos = QPointF(0, 0)
        self.m_hover_insert_idx = None  # Preview slot index when node dragged over
        self.m_active_hover_box = None

        # Graphics item configuration
        self.setZValue(-10.0)
        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def type(self):
        return CanvasContainerType

    def boundingRect(self):
        return QRectF(0, 0, self.m_width, self.m_height)

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

    def updateLayout(self):
        """Computes positions of member nodes and resizes container frame."""
        if not self.m_items:
            self.prepareGeometryChange()
            self.m_width = CONTAINER_MIN_WIDTH
            self.m_height = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2
            self.update()
            return

        pos = self.pos()
        start_x = pos.x() + CONTAINER_PADDING
        start_y = pos.y() + CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING

        if self.m_layout_mode == CONTAINER_LAYOUT_VBOX:
            # Find max child width
            max_w = max(b.boundingRect().width() for b in self.m_items)
            current_y = start_y
            for box in self.m_items:
                box.blockSignals(True)
                box.setPos(start_x, current_y)
                box.blockSignals(False)
                box.repaintLines()
                current_y += box.boundingRect().height() + CONTAINER_ITEM_SPACING

            total_h = current_y - start_y - CONTAINER_ITEM_SPACING
            new_w = max(CONTAINER_MIN_WIDTH, max_w + CONTAINER_PADDING * 2)
            new_h = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2 + total_h

        elif self.m_layout_mode == CONTAINER_LAYOUT_HBOX:
            # Find max child height
            max_h = max(b.boundingRect().height() for b in self.m_items)
            current_x = start_x
            for box in self.m_items:
                box.blockSignals(True)
                box.setPos(current_x, start_y)
                box.blockSignals(False)
                box.repaintLines()
                current_x += box.boundingRect().width() + CONTAINER_ITEM_SPACING

            total_w = current_x - start_x - CONTAINER_ITEM_SPACING
            new_w = max(CONTAINER_MIN_WIDTH, total_w + CONTAINER_PADDING * 2)
            new_h = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2 + max_h

        else:  # Grid (2-column default)
            cols = 2
            col_widths = [0] * cols
            for idx, box in enumerate(self.m_items):
                c = idx % cols
                col_widths[c] = max(col_widths[c], box.boundingRect().width())

            grid_x = start_x
            current_y = start_y
            row_max_h = 0
            for idx, box in enumerate(self.m_items):
                c = idx % cols
                if c == 0 and idx > 0:
                    current_y += row_max_h + CONTAINER_ITEM_SPACING
                    row_max_h = 0
                bx = start_x if c == 0 else start_x + col_widths[0] + CONTAINER_ITEM_SPACING
                box.blockSignals(True)
                box.setPos(bx, current_y)
                box.blockSignals(False)
                box.repaintLines()
                row_max_h = max(row_max_h, box.boundingRect().height())

            total_w = sum(col_widths) + (cols - 1) * CONTAINER_ITEM_SPACING
            total_h = (current_y + row_max_h) - start_y
            new_w = max(CONTAINER_MIN_WIDTH, total_w + CONTAINER_PADDING * 2)
            new_h = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING * 2 + total_h

        self.prepareGeometryChange()
        self.m_width = new_w
        self.m_height = new_h
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
    # Movement Lockstep (Container moves all children)
    # -------------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            rect = self.boundingRect()
            # Check if clicked on layout switcher badge (top right)
            if pos.y() <= CONTAINER_HEADER_HEIGHT:
                # Close/ungroup button: [x] at the very right
                if pos.x() >= rect.width() - 24:
                    event.accept()
                    from .patchcanvas import ungroupNode
                    for b in list(self.m_items):
                        ungroupNode(b)
                    return

                # Layout mode switcher: [VBOX/HBOX/GRID]
                if rect.width() - 85 <= pos.x() < rect.width() - 25:
                    event.accept()
                    modes = [CONTAINER_LAYOUT_VBOX, CONTAINER_LAYOUT_HBOX, CONTAINER_LAYOUT_GRID]
                    next_idx = (modes.index(self.m_layout_mode) + 1) % len(modes)
                    self.m_layout_mode = modes[next_idx]
                    self.updateLayout()
                    return

            self.m_is_dragging = True
            self.m_last_scene_pos = event.scenePos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.m_is_dragging:
            delta = event.scenePos() - self.m_last_scene_pos
            self.m_last_scene_pos = event.scenePos()

            # Translate all children by delta
            for box in self.m_items:
                box.blockSignals(True)
                box.setPos(box.pos() + delta)
                box.blockSignals(False)
                box.repaintLines()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.m_is_dragging = False
        super().mouseReleaseEvent(event)

    # -------------------------------------------------------------------------
    # Painting & Visual Rendering
    # -------------------------------------------------------------------------

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.boundingRect()

        # 1. Background Frame Panel
        bg_color = QColor(24, 25, 38, 180)  # Catppuccin Macchiato mantle with alpha
        painter.setBrush(bg_color)
        pen_color = self.m_color
        pen = QPen(pen_color, 1.5)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 8.0, 8.0)

        # 2. Header Bar
        header_rect = QRectF(0, 0, rect.width(), CONTAINER_HEADER_HEIGHT)
        header_path = QPainterPath()
        header_path.addRoundedRect(header_rect, 8.0, 8.0)
        # Clip bottom corners of header
        painter.fillPath(header_path, QColor(pen_color.red(), pen_color.green(), pen_color.blue(), 45))

        # Title text
        painter.setPen(QColor(220, 224, 232))
        font = QFont(painter.font())
        font.setBold(True)
        font.setPixelSize(12)
        painter.setFont(font)
        painter.drawText(QRectF(10, 0, rect.width() - 80, CONTAINER_HEADER_HEIGHT), Qt.AlignVCenter | Qt.AlignLeft, self.m_title)

        # Layout badge [VBox / HBox / Grid]
        badge_text = self.m_layout_mode.upper()
        painter.setPen(QColor(180, 190, 210))
        font.setBold(False)
        font.setPixelSize(10)
        painter.setFont(font)
        painter.drawText(QRectF(rect.width() - 85, 0, 55, CONTAINER_HEADER_HEIGHT), Qt.AlignVCenter | Qt.AlignRight, f"[{badge_text}]")

        # Close / ungroup button [✕]
        painter.setPen(QColor(235, 160, 172))
        font.setBold(True)
        font.setPixelSize(11)
        painter.setFont(font)
        painter.drawText(QRectF(rect.width() - 22, 0, 16, CONTAINER_HEADER_HEIGHT), Qt.AlignVCenter | Qt.AlignCenter, "✕")

        # 3. Disconnected standby chip notice if items are unplugged
        if self.m_standby_descriptors:
            standby_cnt = len(self.m_standby_descriptors)
            painter.setPen(QColor(243, 139, 168, 180))  # Catppuccin Red/Pink warning
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
            painter.setPen(QPen(QColor("#a6e3a1"), 2.5, Qt.DashLine))  # Catppuccin Green drop indicator
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
