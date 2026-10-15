#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

"""Force-based waypoint relaxation ("flocking").

After A* gives a coarse staircase, this nudges the interior waypoints so that:

* they keep away from node rectangles (obstacle repulsion),
* they keep away from sibling cables (cable-to-cable spacing / flocking),
* they lean towards the midpoint of their neighbours (smoothing),

producing the flowing, evenly-spaced traces that plain grid paths lack. The two
endpoints are always pinned so the cable still lands exactly on its ports.
"""

import math


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


def relax(waypoints, obstacles=(), flock_points=(), iterations=6,
          spacing=16.0, obstacle_margin=14.0, smoothing=0.25, max_step=10.0):
    points = [[float(p[0]), float(p[1])] for p in waypoints]
    count = len(points)
    if count <= 2:
        return [tuple(p) for p in points]

    for _ in range(max(0, iterations)):
        for i in range(1, count - 1):
            px, py = points[i]

            fx = 0.0
            fy = 0.0
            for (ox, oy, ow, oh) in obstacles:
                rx, ry = _repel_rect(px, py, ox, oy, ow, oh, obstacle_margin)
                fx += rx
                fy += ry
            for (ox, oy) in flock_points:
                rx, ry = _repel_point(px, py, ox, oy, spacing)
                fx += rx
                fy += ry

            # smoothing towards the midpoint of both neighbours
            mid_x = (points[i - 1][0] + points[i + 1][0]) * 0.5
            mid_y = (points[i - 1][1] + points[i + 1][1]) * 0.5
            fx += (mid_x - px) * smoothing
            fy += (mid_y - py) * smoothing

            step = math.hypot(fx, fy)
            if step > max_step:
                fx = fx / step * max_step
                fy = fy / step * max_step

            points[i][0] = px + fx
            points[i][1] = py + fy

    return [tuple(p) for p in points]
