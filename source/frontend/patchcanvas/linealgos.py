#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import math

from qt_compat import (
    Qt,
    QPointF,
    QPainterPath,
)

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import (
    CanvasBoxType,
    CanvasLineType,
    CanvasBezierLineType,
    CanvasLineMovType,
    CanvasBezierLineMovType,
)

# ------------------------------------------------------------------------------------------------------------
# Line algorithm plugin registry
#
# A line algorithm decides how a cable is drawn between two ports. Algorithms receive
# a LineContext (endpoints + the whole canvas/topology), never a bare pair of points,
# so simple shapes and complex ones (cable bundles, obstacle-aware routing, ...) share
# one API.
#
# The uniform plugin interface is:
#   build_path(ctx)           -> QPainterPath    a fully connected cable
#   build_drag_path(ctx)      -> QPainterPath    the live drag preview
#   paint(painter, ctx, path) -> bool            optional custom drawing (return True to take over)
#   params()                  -> dict            optional UI-exposed tunables (name -> info)
#
# Flags:
#   dynamic = True            reads global context (siblings/nodes); the canvas re-routes
#                             every cable when a node moves so coupled bundles stay in sync
#   selection_sensitive=True  path changes with selection; the cable re-routes on select
#
# Adding a shape is one class plus @register_line_algorithm; it then shows up in the
# settings combo and is usable everywhere else with no branching changes.
#
# LineContext.start / .end are QPointF in the item's local space, .direction is
# DIRECTION_OUTPUT (+1) when the cable leaves an output port (to the right) or
# DIRECTION_INPUT (-1) when it leaves an input port. For obstacle-aware routing,
# ctx.nodes() yields (group_id, QRectF) for every node and ctx.siblings() yields the
# other cables' endpoints.
# ------------------------------------------------------------------------------------------------------------

DIRECTION_OUTPUT = 1
DIRECTION_INPUT = -1

DEFAULT_LINE_ALGORITHM = "bezier"


class LineContext(object):
    __slots__ = ("start", "end", "direction", "port1", "port2", "connection", "canvas", "scene_pos")

    def __init__(self, start, end, direction=DIRECTION_OUTPUT,
                 port1=None, port2=None, connection=None, canvas=None, scene_pos=None):
        self.start = start
        self.end = end
        self.direction = direction
        self.port1 = port1
        self.port2 = port2
        self.connection = connection
        self.canvas = canvas
        self.scene_pos = scene_pos

    def siblings(self):
        """Yield (start, end, direction) for every other cable, for coupling/bundling."""
        if self.canvas is None:
            return
        for conn in getattr(self.canvas, "connection_list", ()):
            # canvas.connection_list stores connection_dict_t wrappers; unwrap the widget
            widget = getattr(conn, "widget", conn)
            if widget is self.connection:
                continue
            getter = getattr(widget, "getEndpoints", None)
            if getter is None:
                continue
            endpoints = getter()
            if endpoints is not None:
                yield endpoints


    def nodes(self, exclude=()):
        """Yield (group_id, QRectF) scene bounds for every node, for obstacle-aware routing."""
        if self.canvas is None:
            return
        scene = getattr(self.canvas, "scene", None)
        if scene is None:
            return
        for item in scene.items():
            if item.type() != CanvasBoxType:
                continue
            getter = getattr(item, "getGroupId", None)
            group_id = getter() if getter is not None else None
            if group_id in exclude:
                continue
            yield (group_id, item.sceneBoundingRect())


class LineAlgorithm(object):
    #: registry key, also persisted in settings (Canvas/LineStyle)
    name = ""
    #: human readable name shown in the settings UI
    label = ""
    #: QGraphicsItem type used by hit-testing for connected cables
    line_type = CanvasBezierLineType
    #: QGraphicsItem type used by hit-testing for the drag preview
    mov_line_type = CanvasBezierLineMovType
    #: pen cap style
    cap_style = Qt.FlatCap
    #: True when build_path() reads other cables/nodes and needs a full re-route on moves
    dynamic = False
    #: True when the path depends on selection state and needs a re-route on select
    selection_sensitive = False

    @property
    def tracks_others(self):
        # Backward-compatible alias for `dynamic`
        return self.dynamic

    def build_path(self, ctx):
        raise NotImplementedError

    def build_drag_path(self, ctx):
        return self.build_path(ctx)

    def paint(self, painter, ctx, path):
        """Optional override. Return True when the algorithm drew the path itself."""
        return False

    def params(self):
        """Optional tunables exposed to the settings UI: {name: {...}}."""
        return {}

    def display_label(self):
        """Label shown in the settings UI."""
        return self.label


# ------------------------------------------------------------------------------------------------------------
# Geometry helpers

def rounded_polyline(points, radius):
    """Build a QPainterPath through `points`, rounding interior corners with `radius`."""
    path = QPainterPath(QPointF(points[0]))
    if len(points) < 2:
        return path

    for i in range(1, len(points) - 1):
        prev, cur, nxt = points[i - 1], points[i], points[i + 1]
        v1x, v1y = cur.x() - prev.x(), cur.y() - prev.y()
        v2x, v2y = nxt.x() - cur.x(), nxt.y() - cur.y()
        l1 = math.hypot(v1x, v1y) or 1.0
        l2 = math.hypot(v2x, v2y) or 1.0
        r = min(radius, l1 / 2.0, l2 / 2.0)
        p1 = QPointF(cur.x() - v1x / l1 * r, cur.y() - v1y / l1 * r)
        p2 = QPointF(cur.x() + v2x / l2 * r, cur.y() + v2y / l2 * r)
        path.lineTo(p1)
        path.quadTo(cur, p2)

    path.lineTo(QPointF(points[-1]))
    return path


# ------------------------------------------------------------------------------------------------------------
# Phase A - pure geometric shapes

class StraightLineAlgorithm(LineAlgorithm):
    name = "straight"
    label = "Straight line"
    line_type = CanvasLineType
    mov_line_type = CanvasLineMovType
    cap_style = Qt.RoundCap

    def build_path(self, ctx):
        path = QPainterPath(QPointF(ctx.start))
        path.lineTo(ctx.end)
        return path


class BezierLineAlgorithm(LineAlgorithm):
    name = "bezier"
    label = "Bézier curve"
    line_type = CanvasBezierLineType
    mov_line_type = CanvasBezierLineMovType
    cap_style = Qt.FlatCap

    def build_path(self, ctx):
        start, end = ctx.start, ctx.end
        span = abs(end.x() - start.x()) / 2.0
        control1_x = start.x() + ctx.direction * span
        control2_x = end.x() - ctx.direction * span
        path = QPainterPath(QPointF(start))
        path.cubicTo(control1_x, start.y(), control2_x, end.y(), end.x(), end.y())
        return path

    def build_drag_path(self, ctx):
        # Preview keeps a single shared control column, matching the classic drag feel
        start, end = ctx.start, ctx.end
        control_x = start.x() + ctx.direction * abs(end.x() - start.x()) / 2.0
        path = QPainterPath(QPointF(start))
        path.cubicTo(control_x, start.y(), control_x, end.y(), end.x(), end.y())
        return path


class SteppedLineAlgorithm(LineAlgorithm):
    name = "stepped"
    label = "Stepped / Orthogonal"
    line_type = CanvasBezierLineType
    mov_line_type = CanvasBezierLineMovType
    cap_style = Qt.FlatCap

    def build_path(self, ctx):
        start, end = ctx.start, ctx.end
        mid_x = (start.x() + end.x()) / 2.0
        path = QPainterPath(QPointF(start))
        path.lineTo(mid_x, start.y())
        path.lineTo(mid_x, end.y())
        path.lineTo(end.x(), end.y())
        return path


# ------------------------------------------------------------------------------------------------------------
# Phase B - circuit traces and the adaptive hybrid

class CircuitLineAlgorithm(LineAlgorithm):
    name = "circuit"
    label = "Circuit trace"
    line_type = CanvasBezierLineType
    mov_line_type = CanvasBezierLineMovType
    cap_style = Qt.FlatCap
    dynamic = True

    lane_spacing = 14.0
    corner_radius = 8.0
    corridor_width = 120.0

    def build_path(self, ctx):
        start, end = ctx.start, ctx.end
        lane, lanes = self._lane(ctx)
        mid_x = (start.x() + end.x()) / 2.0 + lane * self.lane_spacing
        points = [
            QPointF(start),
            QPointF(mid_x, start.y()),
            QPointF(mid_x, end.y()),
            QPointF(end),
        ]
        return rounded_polyline(points, self.corner_radius)

    def build_drag_path(self, ctx):
        # Preview is a plain centered trace (no sibling lanes while dragging)
        start, end = ctx.start, ctx.end
        mid_x = (start.x() + end.x()) / 2.0
        points = [
            QPointF(start),
            QPointF(mid_x, start.y()),
            QPointF(mid_x, end.y()),
            QPointF(end),
        ]
        return rounded_polyline(points, self.corner_radius)

    def _lane(self, ctx):
        mid = (ctx.start.x() + ctx.end.x()) / 2.0
        mine = (ctx.start.y(), ctx.end.y())
        group = [mine]
        for (s, e, _d) in ctx.siblings():
            if abs(((s.x() + e.x()) / 2.0) - mid) <= self.corridor_width:
                group.append((s.y(), e.y()))
        group.sort()
        lane = group.index(mine)
        return lane, len(group)

    def params(self):
        return {"lane_spacing": self.lane_spacing, "corner_radius": self.corner_radius}


# The `router` LineAlgorithm lives in its own self-contained plugin module
# (linealgo_router.py) together with its A* + flocking implementation. It is
# imported and registered at the bottom of this file.

# NOTE: the adaptive/hybrid dispatcher was removed; its role is now covered by the
# A* + flocking `router`. Bézier stays the default line style.


# ------------------------------------------------------------------------------------------------------------
# Registry

_LINE_ALGORITHMS = {}
_LINE_ALGORITHM_ORDER = []


def register_line_algorithm(cls):
    instance = cls()
    if not instance.name:
        raise ValueError("LineAlgorithm subclass {!r} has no name".format(cls))
    if instance.name not in _LINE_ALGORITHMS:
        _LINE_ALGORITHM_ORDER.append(instance.name)
    _LINE_ALGORITHMS[instance.name] = instance
    return cls


def get_line_algorithm(name):
    return _LINE_ALGORITHMS.get(name, _LINE_ALGORITHMS[DEFAULT_LINE_ALGORITHM])


def line_algorithm_names():
    return list(_LINE_ALGORITHM_ORDER)


def line_algorithms():
    return [(name, _LINE_ALGORITHMS[name].display_label()) for name in _LINE_ALGORITHM_ORDER]


def resolve_line_algorithm():
    # The line_style string is authoritative; the legacy use_bezier_lines boolean is ignored.
    from . import options
    return get_line_algorithm(getattr(options, "line_style", "bezier"))


def active_line_algorithm_is_dynamic():
    return resolve_line_algorithm().dynamic


def active_line_algorithm_tracks_others():
    # Backward-compatible alias
    return active_line_algorithm_is_dynamic()


# ------------------------------------------------------------------------------------------------------------

register_line_algorithm(BezierLineAlgorithm)
register_line_algorithm(StraightLineAlgorithm)
register_line_algorithm(CircuitLineAlgorithm)

# self-contained A* + flocking router plugin
from .linealgo_router import RouterLineAlgorithm  # noqa: E402
register_line_algorithm(RouterLineAlgorithm)

# self-contained Manhattan router plugin
from .linealgo_ortho import OrthogonalLineAlgorithm  # noqa: E402
register_line_algorithm(OrthogonalLineAlgorithm)

register_line_algorithm(SteppedLineAlgorithm)
