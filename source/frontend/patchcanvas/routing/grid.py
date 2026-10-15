#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

"""Uniform grid occupancy map used by the patchbay cable router.

The grid lives in scene coordinates and stores one byte per cell. Node rectangles
are stamped in (inflated by a clearance margin) so the A* search can route cables
around boxes. Nothing here touches patchcanvas internals: callers hand it plain
numbers, so it is reusable and trivially testable.
"""

import math


class OccupancyGrid(object):
    def __init__(self, left, top, width, height, cell):
        self.cell = float(max(1.0, cell))
        self.min_x = float(left)
        self.min_y = float(top)
        self.cols = max(1, int(math.ceil(max(0.0, width) / self.cell)) + 1)
        self.rows = max(1, int(math.ceil(max(0.0, height) / self.cell)) + 1)
        self.blocked = bytearray(self.cols * self.rows)

    # -- coordinate helpers ----------------------------------------------------------------------------

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

    # -- occupancy -------------------------------------------------------------------------------------

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

    def block_disc(self, x, y, radius):
        r = int(math.ceil(radius / self.cell))
        cx, cy = self.cell_of(x, y)
        rr = r * r
        for gy in range(cy - r, cy + r + 1):
            dy = gy - cy
            for gx in range(cx - r, cx + r + 1):
                dx = gx - cx
                if dx * dx + dy * dy <= rr:
                    self.set_blocked(gx, gy)

    def line_clear(self, x0, y0, x1, y1):
        """True when the straight scene-space segment stays out of blocked cells."""
        steps = int(math.hypot(x1 - x0, y1 - y0) / (self.cell * 0.5)) + 1
        for i in range(steps + 1):
            t = i / float(steps)
            cx, cy = self.cell_of(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            if self.is_blocked(cx, cy):
                return False
        return True
