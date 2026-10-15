#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

"""A* grid search with an octile heuristic and string-pulling simplification.

`find_path` returns a list of (cx, cy) cells (start and goal included) or None.
`simplify` collapses that staircase into the fewest waypoints that keep the same
line-of-sight, which is what a cable actually needs.
"""

import heapq
import math

_DIAG = math.sqrt(2.0)

_NEIGHBOURS = (
    (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
    (1, 1, _DIAG), (1, -1, _DIAG), (-1, 1, _DIAG), (-1, -1, _DIAG),
)


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
    if not grid.in_bounds(start[0], start[1]):
        return None
    if not grid.in_bounds(goal[0], goal[1]):
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
