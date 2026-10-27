#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

from qt_compat import (
    qWarning,
    Qt,
    QPointF,
    QPainter,
    QPainterPath,
    QPen,
    QTimer,
    QGraphicsPathItem,
)

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import (
    canvas,
    options,
    port_mode2str,
    port_type2str,
    PORT_MODE_INPUT,
    PORT_MODE_OUTPUT,
    PORT_TYPE_AUDIO_JACK,
    PORT_TYPE_MIDI_ALSA,
    PORT_TYPE_MIDI_JACK,
    PORT_TYPE_PARAMETER,
)

from .linealgos import (
    get_line_algorithm,
    LineContext,
    DIRECTION_INPUT,
    DIRECTION_OUTPUT,
)

# ------------------------------------------------------------------------------------------------------------

class CanvasLineMov(QGraphicsPathItem):
    def __init__(self, port_mode, port_type, parent, shape=None):
        QGraphicsPathItem.__init__(self)
        self.setParentItem(parent)

        self.m_port_mode = port_mode
        self.m_port_type = port_type
        self.m_shape = shape if shape is not None else getattr(options, "line_style", "bezier")
        self.m_algorithm = get_line_algorithm(self.m_shape)
        self.m_ctx = None

        self._settle_timer = QTimer()
        self._settle_timer.setSingleShot(True)
        self._settle_timer.setInterval(45)
        self._settle_timer.timeout.connect(self._on_drag_settled)

        # Port position doesn't change while moving around line
        self.p_itemX = self.scenePos().x()
        self.p_itemY = self.scenePos().y()
        self.p_width = parent.getPortWidth()

        if port_type == PORT_TYPE_AUDIO_JACK:
            pen = QPen(canvas.theme.line_audio_jack, 2)
        elif port_type == PORT_TYPE_MIDI_JACK:
            pen = QPen(canvas.theme.line_midi_jack, 2)
        elif port_type == PORT_TYPE_MIDI_ALSA:
            pen = QPen(canvas.theme.line_midi_alsa, 2)
        elif port_type == PORT_TYPE_PARAMETER:
            pen = QPen(canvas.theme.line_parameter, 2)
        else:
            qWarning("PatchCanvas::CanvasLineMov({}, {}, {}) - invalid port type".format(
                     port_mode2str(port_mode), port_type2str(port_type), parent))
            pen = QPen(Qt.black)

        pen.setCapStyle(self.m_algorithm.cap_style)
        pen.setWidthF(pen.widthF() + 0.00001)
        self.setPen(pen)

    def _on_drag_settled(self):
        if self.m_ctx is not None:
            self.setPath(self.m_algorithm.build_drag_path(self.m_ctx))

    def updateLinePos(self, scenePos):
        if self.m_port_mode == PORT_MODE_INPUT:
            start = QPointF(0, float(canvas.theme.port_height)/2)
            direction = DIRECTION_INPUT
        elif self.m_port_mode == PORT_MODE_OUTPUT:
            start = QPointF(self.p_width + 12, float(canvas.theme.port_height)/2)
            direction = DIRECTION_OUTPUT
        else:
            return

        end = QPointF(scenePos.x() - self.p_itemX, scenePos.y() - self.p_itemY)
        ctx = LineContext(start, end, direction,
                          port1=self.parentItem(), canvas=canvas, scene_pos=scenePos)
        self.m_ctx = ctx

        # Fast direct straight line during active movement
        fast_path = QPainterPath()
        fast_path.moveTo(start)
        fast_path.lineTo(end)
        self.setPath(fast_path)

        # Settle to the full bezier/configured curve once pointer settles
        self._settle_timer.start()

    def type(self):
        return self.m_algorithm.mov_line_type

    def paint(self, painter, option, widget):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, bool(options.antialiasing))
        QGraphicsPathItem.paint(self, painter, option, widget)
        painter.restore()

# ------------------------------------------------------------------------------------------------------------
