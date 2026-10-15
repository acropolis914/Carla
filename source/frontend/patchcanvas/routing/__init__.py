#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

"""Obstacle-aware cable routing API (A* + flocking).

`plan_waypoints(ctx)` is the single entry point. It consumes only a LineContext
(port endpoints in scene coordinates, node bounds via ``ctx.nodes()`` and sibling
cables via `ctx.siblings()`), so it never reaches into patchcanvas internals and
any LineAlgorithm can opt into smart routing by calling it.

The result is a list of scene-space QPointF waypoints (endpoints included) ready
to be turned into a QPainterPath / rounded polyline by the caller.
"""

from qt_compat import QPointF

from .grid import OccupancyGrid
from .astar import find_path, simplify
from .flock import relax

__all__ = [
    "plan_waypoints",
    "OccupancyGrid",
    "find_path",
    "simplify",
    "relax",
]


def plan_waypoints(ctx, cell=26.0, clearance=16.0, margin=220.0,
                   flock_iterations=6, flock_spacing=16.0,
                   obstacle_margin=14.0):
    """Compute an obstacle-aware path between ctx.start and ctx.end.

    Returns a list of QPointF. On any failure (no geometry, fully blocked region)
    it degrades to a straight [start, end] so a cable is never left blank.
    """
    start = ctx.start
    end = ctx.end
    sx, sy = start.x(), start.y()
    ex, ey = end.x(), end.y()

    left = min(sx, ex) - margin
    top = min(sy, ey) - margin
    width = abs(ex - sx) + 2.0 * margin
    height = abs(ey - sy) + 2.0 * margin

    grid = OccupancyGrid(left, top, width, height, cell)

    node_rects = [rect for _group_id, rect in ctx.nodes()]
    for rect in node_rects:
        grid.block_rect(rect.left(), rect.top(), rect.width(), rect.height(),
                        margin=clearance)

    start_cell = grid.cell_of(sx, sy)
    goal_cell = grid.cell_of(end.x(), end.y())

    # a cable must be free to leave/enter its endpoint nodes through the port edge
    grid.clear(start_cell[0], start_cell[1])
    grid.clear(goal_cell[0], goal_cell[1])

    cells = find_path(grid, start_cell, goal_cell)
    if not cells:
        return [start, end]

    cells = simplify(grid, cells)

    waypoints = [(sx, sy)]
    for (cx, cy) in cells[1:-1]:
        waypoints.append(grid.point_of(cx, cy))
    waypoints.append((ex, ey))

    flock_points = []
    for (sibling_start, sibling_end, _direction) in ctx.siblings():
        steps = 4
        for i in range(steps + 1):
            t = i / float(steps)
            flock_points.append((
                sibling_start.x() + (sibling_end.x() - sibling_start.x()) * t,
                sibling_start.y() + (sibling_end.y() - sibling_start.y()) * t,
            ))

    obstacles = [(r.left(), r.top(), r.width(), r.height()) for r in node_rects]

    relaxed = relax(
        waypoints,
        obstacles=obstacles,
        flock_points=flock_points,
        iterations=flock_iterations,
        spacing=flock_spacing,
        obstacle_margin=obstacle_margin,
    )
    return [QPointF(x, y) for (x, y) in relaxed]
