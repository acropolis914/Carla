#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

from qt_compat import (
    Qt,
    QPointF,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QGraphicsPathItem,
)

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import (
    canvas,
    options,
    CanvasLineType,
    CanvasBezierLineType,
    ACTION_PORTS_DISCONNECT,
    EYECANDY_FULL,
    PORT_MODE_OUTPUT,
    PORT_TYPE_AUDIO_JACK,
    PORT_TYPE_MIDI_ALSA,
    PORT_TYPE_MIDI_JACK,
    PORT_TYPE_PARAMETER,
)

from .canvasportglow import CanvasPortGlow

# ------------------------------------------------------------------------------------------------------------

class CanvasLine(QGraphicsPathItem):
    """
    Unified connection line item rendering both Bézier curves, straight lines,
    and stepped/orthogonal paths, with configurable stroke patterns (solid, dotted, dashed).
    """
    def __init__(self, item1, item2, parent, shape=None, stroke=None, opacity=None):
        QGraphicsPathItem.__init__(self)
        self.setParentItem(parent)

        self.item1 = item1
        self.item2 = item2
        self.m_shape = shape if shape is not None else getattr(options, "line_style", "bezier")
        self.m_stroke = stroke if stroke is not None else getattr(options, "line_stroke", "solid")
        self.m_opacity = opacity if opacity is not None else getattr(options, "line_opacity", 100)

        self.m_locked = False
        self.m_lineSelected = None  # None sentinel — ensures updateLineGradient() fires on first call

        self._cached_pen = None
        self._cached_cosm_pen = None

        self.setBrush(QColor(0, 0, 0, 0))
        self.setGraphicsEffect(None)
        self.updateLinePos()

    def setShape(self, shape):
        if self.m_shape != shape:
            self.m_shape = shape
            self.updateLinePos()

    def getShape(self):
        return self.m_shape

    def setStroke(self, stroke):
        if self.m_stroke != stroke:
            self.m_stroke = stroke
            self.updateLineGradient()

    def getStroke(self):
        return self.m_stroke

    def setOpacityVal(self, opacity):
        if self.m_opacity != opacity:
            self.m_opacity = opacity
            self.updateLineGradient()

    def getOpacityVal(self):
        return self.m_opacity

    def isLocked(self):
        return self.m_locked

    def setLocked(self, yesno):
        self.m_locked = yesno

    def isLineSelected(self):
        return self.m_lineSelected

    def updateLineSelected(self):
        if self.m_locked:
            return

        p1 = self.item1.parentItem()
        p2 = self.item2.parentItem()
        yesno = (self.item1.isSelected() or self.item2.isSelected() or
                 (p1 is not None and p1.isSelected()) or 
                 (p2 is not None and p2.isSelected()))

        if yesno == self.m_lineSelected:
            return  # No state change — skip expensive gradient + QPen recompute

        self.m_lineSelected = yesno
        self.updateLineGradient()

    def triggerDisconnect(self):
        for connection in canvas.connection_list:
            if (connection.port_out_id == self.item1.getPortId() and connection.port_in_id == self.item2.getPortId()):
                canvas.callback(ACTION_PORTS_DISCONNECT, connection.connection_id, 0, "")
                break

    def updateLinePos(self):
        if self.item1.getPortMode() == PORT_MODE_OUTPUT:
            rect1 = self.item1.sceneBoundingRect()
            rect2 = self.item2.sceneBoundingRect()

            item1_x = rect1.right()
            item2_x = rect2.left()
            item1_y = rect1.top() + float(canvas.theme.port_height) / 2
            item2_y = rect2.top() + float(canvas.theme.port_height) / 2

            path = QPainterPath(QPointF(item1_x, item1_y))

            if self.m_shape == "straight":
                path.lineTo(item2_x, item2_y)
            elif self.m_shape == "stepped":
                mid_x = (item1_x + item2_x) / 2
                path.lineTo(mid_x, item1_y)
                path.lineTo(mid_x, item2_y)
                path.lineTo(item2_x, item2_y)
            else:
                # Default: cubic Bézier
                item1_new_x = item1_x + abs(item1_x - item2_x) / 2
                item2_new_x = item2_x - abs(item1_x - item2_x) / 2
                path.cubicTo(item1_new_x, item1_y, item2_new_x, item2_y, item2_x, item2_y)

            self.setPath(path)
            self.updateLineSelected()

    def type(self):
        if self.m_shape == "straight":
            return CanvasLineType
        return CanvasBezierLineType

    def updateLineGradient(self):
        p1 = self.item1.scenePos()
        p2 = self.item2.scenePos()
        port_gradient = QLinearGradient(p1, p2)

        # Scale alpha with user line opacity setting (20% - 100%)
        opacity_factor = max(0.2, min(1.0, float(self.m_opacity) / 100.0))

        def get_color(color_val):
            c = QColor(color_val)
            base_alpha = 255 if self.m_lineSelected else 127
            c.setAlpha(int(base_alpha * opacity_factor))
            return c

        def get_port_color(port):
            parent = port.parentItem()
            if parent is not None and hasattr(parent, "getCustomColor"):
                custom_c = parent.getCustomColor()
                if custom_c is not None:
                    return custom_c

            ptype = port.getPortType()
            theme = canvas.theme
            if ptype == PORT_TYPE_AUDIO_JACK:
                return theme.line_audio_jack_sel if self.m_lineSelected else theme.line_audio_jack
            elif ptype == PORT_TYPE_MIDI_JACK:
                return theme.line_midi_jack_sel if self.m_lineSelected else theme.line_midi_jack
            elif ptype == PORT_TYPE_MIDI_ALSA:
                return theme.line_midi_alsa_sel if self.m_lineSelected else theme.line_midi_alsa
            elif ptype == PORT_TYPE_PARAMETER:
                return theme.line_parameter_sel if self.m_lineSelected else theme.line_parameter
            return theme.line_audio_jack

        port_gradient.setColorAt(0.0, get_color(get_port_color(self.item1)))
        port_gradient.setColorAt(1.0, get_color(get_port_color(self.item2)))

        pen_style = Qt.SolidLine
        if self.m_stroke == "dotted":
            pen_style = Qt.DotLine
        elif self.m_stroke == "dashed":
            pen_style = Qt.DashLine

        cap_style = Qt.RoundCap if self.m_shape == "straight" else Qt.FlatCap

        # Cache built pen so paint() never allocates per frame
        self._cached_pen = QPen(port_gradient, 2.00001, pen_style, cap_style)
        self.setPen(self._cached_pen)

        # Pre-build cosmetic overlay pen — stored for reuse
        cosm = QPen(self._cached_pen)
        cosm.setCosmetic(True)
        cosm.setWidthF(1.00001)
        self._cached_cosm_pen = cosm

    def paint(self, painter, option, widget):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, bool(options.antialiasing))

        pen = self.pen()
        scale = canvas.scene.getScaleFactor() if hasattr(canvas.scene, "getScaleFactor") else 1.0
        min_width = max(2.0, 2.0 / scale)
        if pen.widthF() < min_width:
            pen = QPen(pen)
            pen.setWidthF(min_width)
            painter.setPen(pen)

        QGraphicsPathItem.paint(self, painter, option, widget)

        # Cosmetic glow overlay — skip entirely when eye candy is off
        if options.eyecandy:
            cosm_pen = getattr(self, "_cached_cosm_pen", None)
            if cosm_pen is not None:
                painter.setPen(cosm_pen)
                painter.setBrush(Qt.NoBrush)
                painter.setOpacity(0.2)
                painter.drawPath(self.path())

        painter.restore()

# ------------------------------------------------------------------------------------------------------------
# Backward Compatibility Alias

class CanvasBezierLine(CanvasLine):
    def __init__(self, item1, item2, parent, stroke="solid"):
        CanvasLine.__init__(self, item1, item2, parent, shape="bezier", stroke=stroke)
