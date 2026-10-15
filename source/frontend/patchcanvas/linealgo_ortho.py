#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

"""Orthogonal (Manhattan) cable router, self-contained LineAlgorithm plugin.

A direction-aware A* over an occupancy grid: cables only travel horizontally and
vertically, bends are penalised so traces stay readable, node boxes are hard
obstacles and neighbouring cables are soft obstacles (cheaper to route through
than a box, but they nudge traces towards their own lane). Corners are rounded.

As with every LineAlgorithm it only reads the LineContext API.
"""

import heapq
import math

from qt_compat import QPointF

from .linealgos import LineAlgorithm, rounded_polyline

_DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))  # +x, +y, -x, -y
_INF = float("inf")
_MAX_CELLS = 72.0  # upper bound on grid columns/rows along the longer axis


class _Grid(object):
    def __init__(self, left, top, width, height, cell):
        self.cell = float(max(1.0, cell))
        self.min_x = float(left)
        self.min_y = float(top)
        self.rows = max(1, int((max(0.0, height) / self.cell) + 0.5) + 1)
        self.cols = max(1, int((max(0.0, width) / self.cell) + 0.5) + 1)
        self.blocked = bytearray(self.cols * self.rows)
        self.cost = [0.0] * (self.cols * self.rows)

    def cell_of(self, x, y):
        return (int(math.floor((x - self.min_x) / self.cell)),
                int(math.floor((y - self.min_y) / self.cell)))

    def point_of(self, cx, cy):
        return (self.min_x + (cx + 0.5) * self.cell,
                self.min_y + (cy + 0.5) * self.cell)

    def in_bounds(self, cx, cy):
        return 0 <= cx < self.cols and 0 <= cy < self.rows

    def is_blocked(self, cx, cy):
        if not self.in_bounds(cx, cy):
            return True
        return bool(self.blocked[cy * self.cols + cx])

    def clear(self, cx, cy):
        if self.in_bounds(cx, cy):
            self.blocked[cy * self.cols + cx] = 0

    def block_point(self, x, y):
        cx, cy = self.cell_of(x, y)
        if self.in_bounds(cx, cy):
            self.blocked[cy * self.cols + cx] = 1

    def block_rect(self, x, y, width, height, margin=0.0):
        x0, y0 = self.cell_of(x - margin, y - margin)
        x1, y1 = self.cell_of(x + width + margin, y + height + margin)
        for gy in range(max(0, y0), min(self.rows - 1, y1) + 1):
            base = gy * self.cols
            for gx in range(max(0, x0), min(self.cols - 1, x1) + 1):
                self.blocked[base + gx] = 1

    def add_soft(self, x, y, radius, value):
        cx, cy = self.cell_of(x, y)
        r = max(1, int((radius / self.cell) + 0.5))
        for gy in range(cy - r, cy + r + 1):
            for gx in range(cx - r, cx + r + 1):
                if self.in_bounds(gx, gy):
                    self.cost[gy * self.cols + gx] += value

    def cost_at(self, cx, cy):
        return self.cost[cy * self.cols + cx]


def _astar(grid, start_cell, goal_cell, start_dir, bend_penalty):
    cols = grid.cols
    rows = grid.rows
    blocked = grid.blocked
    cost = grid.cost
    gx, gy = goal_cell

    # Flat array state space: index = (cell * 4) + direction. Avoids per-node dict/tuple churn.
    dist = [_INF] * (cols * rows * 4)
    prev = [-1] * (cols * rows * 4)
    heap = []
    push = heapq.heappush
    pop = heapq.heappop
    counter = 0

    scx, scy = start_cell
    sbase = (scy * cols + scx) * 4
    for d in range(4):
        g0 = 0.0 if d == start_dir else bend_penalty
        idx = sbase + d
        dist[idx] = g0
        counter += 1
        push(heap, (g0 + abs(scx - gx) + abs(scy - gy), g0, counter, idx))

    while heap:
        _f, g, _c, idx = pop(heap)
        if g > dist[idx]:
            continue
        cell = idx >> 2
        cd = idx & 3
        cy = cell // cols
        cx = cell - cy * cols

        if cx == gx and cy == gy:
            cells = []
            cur = idx
            while cur != -1:
                c = cur >> 2
                yy = c // cols
                cells.append((c - yy * cols, yy))
                cur = prev[cur]
            cells.reverse()
            out = []
            for c in cells:
                if not out or out[-1] != c:
                    out.append(c)
            return out

        for nd, (ndx, ndy) in enumerate(_DIRS):
            nx = cx + ndx
            ny = cy + ndy
            if nx < 0 or nx >= cols or ny < 0 or ny >= rows:
                continue
            ncell = ny * cols + nx
            if blocked[ncell] and (nx != gx or ny != gy):
                continue
            ng = g + 1.0 + cost[ncell]
            if nd != cd:
                ng += bend_penalty
            nidx = (ncell << 2) | nd
            if ng < dist[nidx]:
                dist[nidx] = ng
                prev[nidx] = idx
                counter += 1
                push(heap, (ng + abs(nx - gx) + abs(ny - gy), ng, counter, nidx))

    return None


def _orthogonalize(points, horizontal_first, blocked):
    """Insert elbows so every segment is axis aligned (and never an obstacle)."""
    out = [points[0]]
    horizontal = horizontal_first
    for i in range(1, len(points)):
        px, py = out[-1]
        cx, cy = points[i]
        if px != cx and py != cy:
            a = (cx, py) if horizontal else (px, cy)
            b = (px, cy) if horizontal else (cx, py)
            elbow = a if not blocked(*a) else (b if not blocked(*b) else a)
            if elbow != (px, py):
                out.append(elbow)
        out.append((cx, cy))
    return out


def _dedupe(points):
    out = []
    for p in points:
        if not out or out[-1] != p:
            out.append(p)
    # drop midpoints that are collinear with their neighbours
    cleaned = []
    for p in out:
        if len(cleaned) >= 2:
            a, b = cleaned[-2], cleaned[-1]
            if (a[0] == b[0] == p[0]) or (a[1] == b[1] == p[1]):
                cleaned[-1] = p
                continue
        cleaned.append(p)
    return cleaned


def _route(start, end, node_rects, sibling_points, cell, clearance, margin,
           bend_penalty, start_dir):
    sx, sy = start.x(), start.y()
    ex, ey = end.x(), end.y()

    left = min(sx, ex) - margin
    top = min(sy, ey) - margin
    width = abs(ex - sx) + 2.0 * margin
    height = abs(ey - sy) + 2.0 * margin

    # Keep the A* grid bounded regardless of cable length so long links stay fast.
    cell = max(cell, width / _MAX_CELLS, height / _MAX_CELLS)

    grid = _Grid(left, top, width, height, cell)
    for (rx, ry, rw, rh) in node_rects:
        grid.block_rect(rx, ry, rw, rh, margin=clearance)

    for (px, py) in sibling_points:
        grid.add_soft(px, py, cell, 0.7)

    start_cell = grid.cell_of(sx, sy)
    goal_cell = grid.cell_of(ex, ey)
    grid.clear(start_cell[0], start_cell[1])
    grid.clear(goal_cell[0], goal_cell[1])

    cells = _astar(grid, start_cell, goal_cell, start_dir, bend_penalty)
    if not cells:
        return None

    pts = [(sx, sy)]
    for (cx, cy) in cells:
        pts.append(grid.point_of(cx, cy))
    pts.append((ex, ey))

    horizontal_first = (start_dir % 2) == 0
    blocked_at = lambda x, y: grid.is_blocked(*grid.cell_of(x, y))
    pts = _orthogonalize(pts, horizontal_first, blocked_at)
    pts = _dedupe(pts)
    return pts


def plan_orthogonal(ctx, cell=24.0, clearance=14.0, margin=200.0, bend_penalty=6.0):
    """Return scene-space (x, y) waypoints for `ctx`, Manhattan, node-avoiding."""
    node_rects = [(r.left(), r.top(), r.width(), r.height()) for _gid, r in ctx.nodes()]
    sibling_points = []
    for (s, e, _d) in ctx.siblings():
        steps = 4
        for i in range(steps + 1):
            t = i / float(steps)
            sibling_points.append((s.x() + (e.x() - s.x()) * t,
                                   s.y() + (e.y() - s.y()) * t))
    start_dir = 0 if ctx.direction >= 0 else 2
    return _route(ctx.start, ctx.end, node_rects, sibling_points, cell, clearance,
                  margin, bend_penalty, start_dir)


class OrthogonalLineAlgorithm(LineAlgorithm):
    """Manhattan router: H/V-only A* with a bend/proximity-aware cost."""

    name = "orthogonal"
    label = "Orthogonal (Manhattan)"
    dynamic = True

    cell_size = 24.0
    clearance = 14.0
    margin = 200.0
    bend_penalty = 6.0
    corner_radius = 8.0

    def build_path(self, ctx):
        try:
            pts = plan_orthogonal(ctx, cell=self.cell_size, clearance=self.clearance,
                                  margin=self.margin, bend_penalty=self.bend_penalty)
        except Exception:
            pts = None

        if not pts or len(pts) < 2:
            pts = [(ctx.start.x(), ctx.start.y()), (ctx.end.x(), ctx.end.y())]
        return rounded_polyline([QPointF(x, y) for (x, y) in pts], self.corner_radius)

    def params(self):
        return {
            "cell": self.cell_size,
            "clearance": self.clearance,
            "bend_penalty": self.bend_penalty,
            "corner_radius": self.corner_radius,
        }
