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

        # Port position doesn't change while moving around line
        self.p_itemX = self.scenePos().x()
        self.p_itemY = self.scenePos().y()
        self.p_width = parent.getPortWidth()

        if self.m_port_mode == PORT_MODE_INPUT:
            self.m_start_point = QPointF(0, float(canvas.theme.port_height) / 2)
        elif self.m_port_mode == PORT_MODE_OUTPUT:
            self.m_start_point = QPointF(self.p_width + 12, float(canvas.theme.port_height) / 2)
        else:
            self.m_start_point = QPointF(0, 0)

        self._last_scene_x = None
        self._last_scene_y = None

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

    def updateLinePos(self, scenePos):
        sx = scenePos.x()
        sy = scenePos.y()

        # Leeway deadband: skip if pointer moved less than 1.5 pixels
        if self._last_scene_x is not None:
            dx = sx - self._last_scene_x
            dy = sy - self._last_scene_y
            if (dx * dx + dy * dy) < 2.25:
                return

        self._last_scene_x = sx
        self._last_scene_y = sy

        end = QPointF(sx - self.p_itemX, sy - self.p_itemY)

        # Zero allocation straight line directly to cursor
        fast_path = QPainterPath()
        fast_path.moveTo(self.m_start_point)
        fast_path.lineTo(end)
        self.setPath(fast_path)

    def type(self):
        return self.m_algorithm.mov_line_type

    def paint(self, painter, option, widget):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, bool(options.antialiasing))
        QGraphicsPathItem.paint(self, painter, option, widget)
        painter.restore()

# ------------------------------------------------------------------------------------------------------------
