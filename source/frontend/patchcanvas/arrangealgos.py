#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

"""Auto-arrange algorithm plugin registry.

An arrange algorithm turns a set of nodes into positions by mutating them::

    arrange(nodes) -> None

The uniform plugin interface is deliberately tiny so new layouts are one class
plus ``@register_layout_algorithm``; they then show up in the Arrange Tools menu
and can be dispatched from ``patchcanvas.autoArrangeNodes()`` with no branching.
"""

DEFAULT_LAYOUT_ALGORITHM = "flow"


class LayoutAlgorithm(object):
    #: registry key, also persisted in settings (Canvas/ArrangeStyle)
    name = ""
    #: human readable name shown in the UI
    label = ""

    def arrange(self, nodes):
        raise NotImplementedError

    def display_label(self):
        return self.label


class ClassicLayoutAlgorithm(LayoutAlgorithm):
    """The original left-to-right signal-flow arrangement (all canvas nodes)."""

    name = "classic"
    label = "Classic (signal flow)"

    def arrange(self, nodes):
        # The original routine is canvas-global: it anchors hardware capture at the
        # left, hardware playback at the right and resolves strands across columns.
        from . import patchcanvas as _pc
        _pc.autoArrange()


class FlowLayoutAlgorithm(LayoutAlgorithm):
    """Columnar layout: topological layers, vertically centred, selection aware."""

    name = "flow"
    label = "Flow columns"

    node_gap = 64
    vertical_gap = 40

    def arrange(self, nodes):
        from . import options
        from . import patchcanvas as _pc

        if len(nodes) < 2:
            return

        edges, incoming, group_name = _pc._nodeGraph(nodes)

        # Longest-path layering (nodes inside a cycle settle at layer 0)
        layer = {n: 0 for n in nodes}
        for _ in range(len(nodes)):
            changed = False
            for src, targets in edges.items():
                for dst in targets:
                    if layer[dst] < layer[src] + 1:
                        layer[dst] = layer[src] + 1
                        changed = True
            if not changed:
                break

        columns = {}
        for n in nodes:
            columns.setdefault(layer[n], []).append(n)
        sorted_layers = sorted(columns.keys())

        origin_x = min(n.x() for n in nodes)
        center_y = sum(n.y() + n.boundingRect().height() / 2.0 for n in nodes) / float(len(nodes))

        col_widths = {
            lay: max(n.boundingRect().width() for n in columns[lay])
            for lay in sorted_layers
        }
        col_x = {}
        curr_x = origin_x
        for lay in sorted_layers:
            col_x[lay] = curr_x
            curr_x += col_widths[lay] + self.node_gap

        for lay in sorted_layers:
            col = columns[lay]
            col.sort(key=lambda n: group_name.get(n, "").lower())
            total_h = (
                sum(n.boundingRect().height() for n in col)
                + (len(col) - 1) * self.vertical_gap
            )
            cy = center_y - total_h / 2.0
            for n in col:
                n.setPos(col_x[lay], cy)
                cy += n.boundingRect().height() + self.vertical_gap

        if getattr(options, "snap_enabled", True):
            gs = max(1, getattr(options, "grid_size", 20))
            for n in nodes:
                n.setPos(round(n.x() / gs) * gs, round(n.y() / gs) * gs)

        _pc.syncNodePositions(nodes)


# ------------------------------------------------------------------------------------------------------------
# Registry

_LAYOUT_ALGORITHMS = {}
_LAYOUT_ALGORITHM_ORDER = []


def register_layout_algorithm(cls):
    instance = cls()
    if not instance.name:
        raise ValueError("LayoutAlgorithm subclass {!r} has no name".format(cls))
    if instance.name not in _LAYOUT_ALGORITHMS:
        _LAYOUT_ALGORITHM_ORDER.append(instance.name)
    _LAYOUT_ALGORITHMS[instance.name] = instance
    return cls


def get_layout_algorithm(name):
    return _LAYOUT_ALGORITHMS.get(name, _LAYOUT_ALGORITHMS[DEFAULT_LAYOUT_ALGORITHM])


def layout_algorithm_names():
    return list(_LAYOUT_ALGORITHM_ORDER)


def layout_algorithms():
    return [(name, _LAYOUT_ALGORITHMS[name].display_label()) for name in _LAYOUT_ALGORITHM_ORDER]


def resolve_layout_algorithm(name=None):
    if name is None:
        from . import options
        name = getattr(options, "arrange_style", DEFAULT_LAYOUT_ALGORITHM)
    return get_layout_algorithm(name)


# ------------------------------------------------------------------------------------------------------------

register_layout_algorithm(ClassicLayoutAlgorithm)
register_layout_algorithm(FlowLayoutAlgorithm)

# self-contained Sugiyama layered layout plugin
from .arrange_sugiyama import SugiyamaLayoutAlgorithm  # noqa: E402
register_layout_algorithm(SugiyamaLayoutAlgorithm)

# pattern-aware heuristic layout plugin
from .arrange_heuristic import HeuristicLayoutAlgorithm  # noqa: E402
register_layout_algorithm(HeuristicLayoutAlgorithm)
