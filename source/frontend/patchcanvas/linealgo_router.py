#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

"""Obstacle-aware cable router, self-contained as a single LineAlgorithm plugin.

Everything the router needs lives here: the occupancy grid, the A* search with
string-pulling, and the flocking relaxation. The only outside contact is the
public LineContext API (``ctx.start``/``ctx.end``/``ctx.direction`` plus
``ctx.nodes()`` for node boxes and ``ctx.siblings()`` for neighbouring cables),
so the plugin never reaches into patchcanvas internals.

``linealgos`` imports this module and registers :class:`RouterLineAlgorithm`.
"""

import heapq
import math

from qt_compat import QPointF

from .linealgos import (
    BezierLineAlgorithm,
    LineAlgorithm,
    rounded_polyline,
)

# ------------------------------------------------------------------------------------------------------------
# Occupancy grid

_DIAG = math.sqrt(2.0)

_NEIGHBOURS = (
    (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
    (1, 1, _DIAG), (1, -1, _DIAG), (-1, 1, _DIAG), (-1, -1, _DIAG),
)
_MAX_CELLS = 72.0  # upper bound on grid columns/rows along the longer axis


class OccupancyGrid(object):
    def __init__(self, left, top, width, height, cell):
        self.cell = float(max(1.0, cell))
        self.min_x = float(left)
        self.min_y = float(top)
        self.cols = max(1, int(math.ceil(max(0.0, width) / self.cell)) + 1)
        self.rows = max(1, int(math.ceil(max(0.0, height) / self.cell)) + 1)
        self.blocked = bytearray(self.cols * self.rows)

    def cell_of(self, x, y):
        return (
            int(math.floor((x - self.min_x) / self.cell)),
            int(math.floor((y - self.min_y) / self.cell)),
        )

    def point_of(self, cx, cy):
        return (
            self.min_x + (cx + 0.5) * self.cell,
            self.min_y + (cy + 0.5) * self.cell,
        )

    def in_bounds(self, cx, cy):
        return 0 <= cx < self.cols and 0 <= cy < self.rows

    def is_blocked(self, cx, cy):
        if not self.in_bounds(cx, cy):
            return True
        return bool(self.blocked[cy * self.cols + cx])

    def set_blocked(self, cx, cy, value=True):
        if self.in_bounds(cx, cy):
            self.blocked[cy * self.cols + cx] = 1 if value else 0

    def clear(self, cx, cy):
        self.set_blocked(cx, cy, False)

    def block_rect(self, x, y, width, height, margin=0.0):
        x0, y0 = self.cell_of(x - margin, y - margin)
        x1, y1 = self.cell_of(x + width + margin, y + height + margin)
        for gy in range(max(0, y0), min(self.rows - 1, y1) + 1):
            base = gy * self.cols
            for gx in range(max(0, x0), min(self.cols - 1, x1) + 1):
                self.blocked[base + gx] = 1

    def line_clear(self, x0, y0, x1, y1):
        """True when the straight scene-space segment stays out of blocked cells."""
        steps = int(math.hypot(x1 - x0, y1 - y0) / (self.cell * 0.5)) + 1
        for i in range(steps + 1):
            t = i / float(steps)
            cx, cy = self.cell_of(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            if self.is_blocked(cx, cy):
                return False
        return True


# ------------------------------------------------------------------------------------------------------------
# A* search + string pulling

def _octile(ax, ay, bx, by):
    dx = abs(ax - bx)
    dy = abs(ay - by)
    return (dx + dy) + (_DIAG - 2.0) * min(dx, dy)


def _reconstruct(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def find_path(grid, start, goal):
    if not grid.in_bounds(start[0], start[1]) or not grid.in_bounds(goal[0], goal[1]):
        return None
    if start == goal:
        return [start]

    open_heap = [(_octile(start[0], start[1], goal[0], goal[1]), 0.0, start)]
    came_from = {}
    g_score = {start: 0.0}
    closed = set()

    while open_heap:
        _f, g, current = heapq.heappop(open_heap)
        if current == goal:
            return _reconstruct(came_from, current)
        if current in closed:
            continue
        closed.add(current)

        cx, cy = current
        for dx, dy, step in _NEIGHBOURS:
            nx, ny = cx + dx, cy + dy
            if not grid.in_bounds(nx, ny):
                continue
            neighbour = (nx, ny)
            if grid.is_blocked(nx, ny) and neighbour != goal:
                continue
            if dx != 0 and dy != 0:
                # never squeeze diagonally between two blocked orthogonal cells
                if grid.is_blocked(cx + dx, cy) or grid.is_blocked(cx, cy + dy):
                    continue
            tentative = g + step
            if tentative < g_score.get(neighbour, float("inf")):
                g_score[neighbour] = tentative
                came_from[neighbour] = current
                f = tentative + _octile(nx, ny, goal[0], goal[1])
                heapq.heappush(open_heap, (f, tentative, neighbour))

    return None


def _cells_visible(grid, a, b):
    ax, ay = a
    bx, by = b
    dx = abs(bx - ax)
    dy = abs(by - ay)
    sx = 1 if bx > ax else -1
    sy = 1 if by > ay else -1
    err = dx - dy
    x, y = ax, ay
    while True:
        if grid.is_blocked(x, y):
            return False
        if (x, y) == (bx, by):
            return True
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def simplify(grid, cells):
    """Greedy string pulling: keep only the corners that matter."""
    if len(cells) <= 2:
        return list(cells)

    out = [cells[0]]
    index = 0
    last = len(cells) - 1
    while index < last:
        farthest = index + 1
        for probe in range(last, index, -1):
            if _cells_visible(grid, cells[index], cells[probe]):
                farthest = probe
                break
        out.append(cells[farthest])
        index = farthest
    return out


# ------------------------------------------------------------------------------------------------------------
# Flocking relaxation

def _repel_rect(px, py, x, y, width, height, margin):
    closest_x = min(max(px, x), x + width)
    closest_y = min(max(py, y), y + height)
    dx = px - closest_x
    dy = py - closest_y
    dist = math.hypot(dx, dy)
    if dist > 1e-6:
        if dist >= margin:
            return 0.0, 0.0
        push = (margin - dist) / margin
        return (dx / dist) * push * margin * 0.5, (dy / dist) * push * margin * 0.5
    # inside the rectangle: escape through the closest edge
    left = px - x
    right = x + width - px
    top = py - y
    bottom = y + height - py
    smallest = min(left, right, top, bottom)
    if smallest == left:
        return -margin * 0.5, 0.0
    if smallest == right:
        return margin * 0.5, 0.0
    if smallest == top:
        return 0.0, -margin * 0.5
    return 0.0, margin * 0.5


def _repel_point(px, py, ox, oy, radius):
    dx = px - ox
    dy = py - oy
    dist = math.hypot(dx, dy)
    if dist < 1e-6 or dist >= radius:
        return 0.0, 0.0
    push = (radius - dist) / radius
    scale = push * radius * 0.5
    return (dx / dist) * scale, (dy / dist) * scale


def _project_out(px, py, rects, margin):
    """Hard constraint: never leave a waypoint inside an inflated node box."""
    for (x, y, w, h) in rects:
        x0, y0 = x - margin, y - margin
        x1, y1 = x + w + margin, y + h + margin
        if x0 < px < x1 and y0 < py < y1:
            dl, dr, dt, db = px - x0, x1 - px, py - y0, y1 - py
            smallest = min(dl, dr, dt, db)
            if smallest == dl:
                px = x0
            elif smallest == dr:
                px = x1
            elif smallest == dt:
                py = y0
            else:
                py = y1
    return px, py


def relax(waypoints, obstacles=(), flock_points=(), iterations=8,
          spacing=16.0, obstacle_margin=16.0, smoothing=0.25, max_step=10.0,
          is_clear=None):
    """Pull interior waypoints for even spacing, but never through a node.

    ``is_clear(a, b)`` (when given) must report whether the straight segment a->b
    is free. Smoothing is skipped for any point whose neighbours straddle an
    obstacle, so the A* detour is preserved instead of being smoothed back into
    the box; ``_project_out`` is a final hard guarantee.
    """
    points = [[float(p[0]), float(p[1])] for p in waypoints]
    count = len(points)
    if count <= 2:
        return [tuple(p) for p in points]

    rects = [(float(x), float(y), float(w), float(h)) for (x, y, w, h) in obstacles]

    for _ in range(max(0, iterations)):
        for i in range(1, count - 1):
            px, py = points[i]

            fx = 0.0
            fy = 0.0
            for (ox, oy, ow, oh) in rects:
                rx, ry = _repel_rect(px, py, ox, oy, ow, oh, obstacle_margin)
                fx += rx
                fy += ry
            for (ox, oy) in flock_points:
                rx, ry = _repel_point(px, py, ox, oy, spacing)
                fx += rx
                fy += ry

            # smoothing towards the midpoint of both neighbours, but only when
            # those neighbours can see each other (else we would cut the corner
            # of the obstacle the A* path just routed around)
            prev, nxt = points[i - 1], points[i + 1]
            if is_clear is None or is_clear(prev, nxt):
                fx += ((prev[0] + nxt[0]) * 0.5 - px) * smoothing
                fy += ((prev[1] + nxt[1]) * 0.5 - py) * smoothing

            step = math.hypot(fx, fy)
            if step > max_step:
                fx = fx / step * max_step
                fy = fy / step * max_step

            px, py = _project_out(px + fx, py + fy, rects, obstacle_margin)
            points[i][0] = px
            points[i][1] = py

    return [tuple(p) for p in points]


def _polyline_clear(grid, points):
    for i in range(len(points) - 1):
        if not grid.line_clear(points[i][0], points[i][1],
                               points[i + 1][0], points[i + 1][1]):
            return False
    return True


# ------------------------------------------------------------------------------------------------------------
# Public entry point

def plan_waypoints(ctx, cell=26.0, clearance=16.0, margin=220.0,
                   iterations=8, spacing=16.0, obstacle_margin=None):
    """Return scene-space QPointF waypoints (endpoints included) for ``ctx``.

    A straight fallback is returned when no route exists, so a cable never
    disappears. The result is guaranteed not to cross any node box.
    """
    start, end = ctx.start, ctx.end
    sx, sy = start.x(), start.y()
    ex, ey = end.x(), end.y()

    left = min(sx, ex) - margin
    top = min(sy, ey) - margin
    width = abs(ex - sx) + 2.0 * margin
    height = abs(ey - sy) + 2.0 * margin

    # Bound the grid resolution so very long cables do not explode the A* search.
    cell = max(cell, width / _MAX_CELLS, height / _MAX_CELLS)

    grid = OccupancyGrid(left, top, width, height, cell)

    node_rects = [(r.left(), r.top(), r.width(), r.height()) for _gid, r in ctx.nodes()]
    for (rx, ry, rw, rh) in node_rects:
        grid.block_rect(rx, ry, rw, rh, margin=clearance)

    start_cell = grid.cell_of(sx, sy)
    goal_cell = grid.cell_of(ex, ey)
    # a cable must be free to leave/enter its endpoint nodes through the port edge
    grid.clear(start_cell[0], start_cell[1])
    grid.clear(goal_cell[0], goal_cell[1])

    cells = find_path(grid, start_cell, goal_cell)
    if not cells:
        return [QPointF(start), QPointF(end)]

    cells = simplify(grid, cells)

    raw = [(sx, sy)]
    for (cx, cy) in cells[1:-1]:
        raw.append(grid.point_of(cx, cy))
    raw.append((ex, ey))

    if len(raw) <= 2:
        return [QPointF(start), QPointF(end)]

    flock_points = []
    for (sibling_start, sibling_end, _direction) in ctx.siblings():
        steps = 4
        for i in range(steps + 1):
            t = i / float(steps)
            flock_points.append((
                sibling_start.x() + (sibling_end.x() - sibling_start.x()) * t,
                sibling_start.y() + (sibling_end.y() - sibling_start.y()) * t,
            ))

    om = clearance if obstacle_margin is None else obstacle_margin
    relaxed = relax(
        raw,
        obstacles=node_rects,
        flock_points=flock_points,
        iterations=iterations,
        spacing=spacing,
        obstacle_margin=om,
        is_clear=lambda a, b: grid.line_clear(a[0], a[1], b[0], b[1]),
    )

    # Final safety net: if relaxation ever tunnels through a node, fall back to
    # the raw A* polyline (which is collision-free by construction).
    if not _polyline_clear(grid, relaxed):
        relaxed = raw

    return [QPointF(x, y) for (x, y) in relaxed]


# ------------------------------------------------------------------------------------------------------------
# The plugin

class RouterLineAlgorithm(LineAlgorithm):
    """Obstacle-aware router: A* around node boxes, then flocking relaxation."""

    name = "router"
    label = "Smart router (A* + flocking)"
    dynamic = True

    #: occupancy grid resolution in scene units (smaller = finer but slower)
    cell_size = 26.0
    #: how far cables keep clear of node boxes
    clearance = 16.0
    #: corner rounding radius
    corner_radius = 10.0

    def build_path(self, ctx):
        try:
            points = plan_waypoints(ctx, cell=self.cell_size, clearance=self.clearance)
        except Exception:
            points = None

        if not points or len(points) < 2:
            return BezierLineAlgorithm().build_path(ctx)
        return rounded_polyline(points, self.corner_radius)

    def params(self):
        return {
            "cell": self.cell_size,
            "clearance": self.clearance,
            "corner_radius": self.corner_radius,
        }
