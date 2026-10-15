#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

"""Heuristic, pattern-aware arrange plugin.

Instead of laying every node out with one uniform rule, this algorithm first
looks at the *connection topology* and only then places nodes:

* split the graph into connected components and treat each as a separate island
  (rule 10 / 60),
* inside a component recognise the common shapes and place them accordingly:
  exclusive pairs side by side (1 / 6), fan-out with the source beside a vertical
  stack of destinations (2 / 12), merges with the sources aligned before the sink
  (3 / 13), fully connected cliques as a compact grid (5), stars / hub-and-spoke
  (18), and plain chains following the signal flow (11),
* anything else falls back to a layered (Sugiyama-style) pass with barycenter
  crossing reduction (4 / 56 / 57).

It is deliberately deterministic (ties broken by node name) and reuses the shared
``_nodeGraph`` / ``syncNodePositions`` helpers, so it composes with the rest of
the arrange plugins.
"""

import math

from .arrangealgos import LayoutAlgorithm


class HeuristicLayoutAlgorithm(LayoutAlgorithm):
    name = "heuristic"
    label = "Heuristic (pattern-aware)"

    node_gap = 64
    vertical_gap = 40
    island_gap = 96

    def _name(self, group_name, node):
        return group_name.get(node, "").lower()

    def arrange(self, nodes):
        from . import options
        from . import patchcanvas as _pc

        if len(nodes) < 2:
            return

        edges, incoming, group_name = _pc._nodeGraph(nodes)
        nbr = {n: set(edges[n]) | set(incoming[n]) for n in nodes}

        ordered = sorted(nodes, key=lambda n: self._name(group_name, n))
        comps = self._components(ordered, nbr)
        comps.sort(key=lambda c: self._name(group_name, sorted(c, key=lambda n: self._name(group_name, n))[0]))

        blocks = []
        for comp in comps:
            pos, width, height = self._arrange_component(comp, edges, incoming, group_name)
            blocks.append((comp, pos, width, height))

        origin_x = min(n.x() for n in nodes)
        center_y = sum(n.y() + n.boundingRect().height() / 2.0 for n in nodes) / float(len(nodes))

        cur_x = origin_x
        for comp, pos, width, height in blocks:
            y0 = center_y - height / 2.0
            for n in comp:
                lx, ly = pos[n]
                n.setPos(cur_x + lx, y0 + ly)
            cur_x += width + self.island_gap

        if getattr(options, "snap_enabled", True):
            gs = max(1, getattr(options, "grid_size", 20))
            for n in nodes:
                n.setPos(round(n.x() / gs) * gs, round(n.y() / gs) * gs)

        _pc.syncNodePositions(nodes)

    # -- topology helpers ------------------------------------------------------------------------------------

    def _components(self, ordered, nbr):
        seen = set()
        comps = []
        for start in ordered:
            if start in seen:
                continue
            seen.add(start)
            stack = [start]
            comp = []
            while stack:
                u = stack.pop()
                comp.append(u)
                for v in nbr[u]:
                    if v not in seen:
                        seen.add(v)
                        stack.append(v)
            comps.append(comp)
        return comps

    def _arrange_component(self, comp, edges, incoming, group_name):
        if len(comp) == 1:
            node = comp[0]
            return {node: (0.0, 0.0)}, node.boundingRect().width(), node.boundingRect().height()

        for detector in (
            self._try_pair,
            self._try_clique,
            self._try_star,
            self._try_chain,
        ):
            result = detector(comp, edges, incoming, group_name)
            if result is not None:
                return result

        return self._layered(comp, edges, incoming, group_name)

    def _try_pair(self, comp, edges, incoming, group_name):
        if len(comp) != 2:
            return None
        a, b = comp
        if b not in edges[a] and a not in edges[b]:
            return None
        gap = self.node_gap
        ra, rb = a.boundingRect(), b.boundingRect()
        pos = {a: (0.0, 0.0), b: (ra.width() + gap, 0.0)}
        return pos, ra.width() + gap + rb.width(), max(ra.height(), rb.height())

    def _try_clique(self, comp, edges, incoming, group_name):
        n = len(comp)
        if n < 3:
            return None
        for u in comp:
            if len(edges[u] | incoming[u]) < n - 1:
                return None

        ordered = sorted(comp, key=lambda x: self._name(group_name, x))
        cols = int(math.ceil(math.sqrt(n)))
        cell_w = max(x.boundingRect().width() for x in comp)
        cell_h = max(x.boundingRect().height() for x in comp)
        gap, vgap = self.node_gap, self.vertical_gap

        pos = {}
        for i, node in enumerate(ordered):
            r, c = divmod(i, cols)
            pos[node] = (c * (cell_w + gap), r * (cell_h + vgap))
        rows = int(math.ceil(n / float(cols)))
        return pos, cols * cell_w + (cols - 1) * gap, rows * cell_h + (rows - 1) * vgap

    def _try_star(self, comp, edges, incoming, group_name):
        n = len(comp)
        if n < 3:
            return None

        hub = None
        for u in comp:
            if len(edges[u] | incoming[u]) == n - 1:
                hub = u
                break
        if hub is None:
            return None
        for o in comp:
            if o is hub:
                continue
            if (edges[o] | incoming[o]) - {hub}:
                return None

        others = sorted((o for o in comp if o is not hub), key=lambda x: self._name(group_name, x))
        hb = hub.boundingRect()
        has_out = bool(edges[hub])
        has_in = bool(incoming[hub])

        def stack(x, items):
            pos = {}
            y = 0.0
            for o in items:
                pos[o] = (x, y)
                y += o.boundingRect().height() + self.vertical_gap
            return pos, (y - self.vertical_gap if items else 0.0)

        if has_out and not has_in:
            pos, total = stack(hb.width() + self.node_gap, others)
            pos[hub] = (0.0, total / 2.0 - hb.height() / 2.0)
            width = hb.width() + self.node_gap + max(o.boundingRect().width() for o in others)
            return pos, width, max(total, hb.height())

        if has_in and not has_out:
            pos, total = stack(0.0, others)
            hub_x = max(o.boundingRect().width() for o in others) + self.node_gap
            pos[hub] = (hub_x, total / 2.0 - hb.height() / 2.0)
            return pos, hub_x + hb.width(), max(total, hb.height())

        if has_in and has_out:
            sources = sorted(incoming[hub], key=lambda x: self._name(group_name, x))
            sinks = sorted(edges[hub], key=lambda x: self._name(group_name, x))
            left, left_h = stack(0.0, sources)
            left_w = max((o.boundingRect().width() for o in sources), default=0.0)
            mid_x = left_w + self.node_gap
            right, right_h = stack(mid_x + hb.width() + self.node_gap, sinks)
            total = max(left_h, right_h, hb.height())
            left.update(right)
            left[hub] = (mid_x, total / 2.0 - hb.height() / 2.0)
            right_w = max((o.boundingRect().width() for o in sinks), default=0.0)
            width = mid_x + hb.width() + self.node_gap + right_w
            return left, width, total

        return None

    def _try_chain(self, comp, edges, incoming, group_name):
        n = len(comp)
        if n < 2:
            return None
        nbr = {u: set(edges[u]) | set(incoming[u]) for u in comp}
        for u in comp:
            if len(nbr[u]) > 2:
                return None

        starts = [u for u in comp if len(nbr[u]) == 1]
        if starts:
            sources = [u for u in starts if not incoming[u]]
            start = min(sources or starts, key=lambda x: self._name(group_name, x))
        else:
            start = min(comp, key=lambda x: self._name(group_name, x))

        order = []
        seen = set()
        cur, prev = start, None
        while cur is not None and cur not in seen:
            order.append(cur)
            seen.add(cur)
            nxts = [v for v in nbr[cur] if v is not prev]
            prev, cur = cur, (min(nxts, key=lambda x: self._name(group_name, x)) if nxts else None)

        pos = {}
        x = 0.0
        max_h = 0.0
        for o in order:
            r = o.boundingRect()
            pos[o] = (x, 0.0)
            x += r.width() + self.node_gap
            max_h = max(max_h, r.height())
        return pos, x - self.node_gap, max_h

    def _layered(self, comp, edges, incoming, group_name):
        layer = {u: 0 for u in comp}
        for _ in range(len(comp)):
            changed = False
            for u in comp:
                for v in edges[u]:
                    if v in layer and layer[v] < layer[u] + 1:
                        layer[v] = layer[u] + 1
                        changed = True
            if not changed:
                break

        layers = {}
        for u in comp:
            layers.setdefault(layer[u], []).append(u)
        keys = sorted(layers)
        for k in keys:
            layers[k].sort(key=lambda x: self._name(group_name, x))

        index = {u: i for k in keys for i, u in enumerate(layers[k])}
        for s in range(6):
            order = keys if s % 2 == 0 else list(reversed(keys))
            neigh = edges if s % 2 == 0 else incoming
            for k in order:
                col = layers[k]

                def bary(u):
                    rel = [index[m] for m in neigh[u] if m in index]
                    return sum(rel) / float(len(rel)) if rel else float(index[u])

                col.sort(key=bary)
                for i, u in enumerate(col):
                    index[u] = i

        col_w = {k: max(u.boundingRect().width() for u in layers[k]) for k in keys}
        col_x = {}
        cx = 0.0
        for k in keys:
            col_x[k] = cx
            cx += col_w[k] + self.node_gap

        total_h = 0.0
        for k in keys:
            col = layers[k]
            th = sum(u.boundingRect().height() for u in col) + (len(col) - 1) * self.vertical_gap
            total_h = max(total_h, th)

        pos = {}
        for k in keys:
            col = layers[k]
            th = sum(u.boundingRect().height() for u in col) + (len(col) - 1) * self.vertical_gap
            cy = (total_h - th) / 2.0
            for u in col:
                pos[u] = (col_x[k], cy)
                cy += u.boundingRect().height() + self.vertical_gap

        return pos, cx - self.node_gap, total_h
