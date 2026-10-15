#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

"""Graph introspection model for the patchbay.

Everything that reasons about the patchbay *as a graph* (layout plugins, the
future claractl / scripting API) goes through this one place, so there is a
single, JSON-serialisable view of the canvas:

    {
      "nodes": [
        {"index": 0, "group_id": 1, "name": "Carla", "split": 1,
         "pos": [x, y], "size": [w, h], "rect": [x, y, w, h],
         "ports": [
            {"port_id": 0, "name": "out1", "mode": 2,
             "mode_str": "PORT_MODE_OUTPUT", "type": 1,
             "type_str": "PORT_TYPE_AUDIO_JACK", "alternate": false},
            ...
         ]},
        ...
      ],
      "connections": [
        {"connection_id": 0,
         "out": {"node": 0, "group_id": 1, "port_id": 0},
         "in":  {"node": 1, "group_id": 2, "port_id": 0}},
        ...
      ],
      "topology": {
        "edges": [[1], [2], []],      # node index -> [dst node index, ...]
        "incoming": [[], [0], [1]],   # node index -> [src node index, ...]
        "degree": [1, 2, 1],
        "components": [[0, 1, 2]],
        "layers": [0, 1, 2]
      }
    }

Coordinates are scene coordinates (floats). The model is a plain dict/list
tree with no Qt objects, so it can be ``json.dumps``\\ 'd directly.
"""

import json


def _all_node_widgets():
    from . import canvas

    for group in canvas.group_list:
        for widget in group.widgets:
            if widget is not None:
                yield group, widget


def collect_graph(nodes=None, include_topology=True):
    """Build the graph model.

    ``nodes`` optionally restricts the model to a set of canvas box widgets
    (e.g. the current selection). When None, every node on the canvas is used.
    Connections are only kept when both endpoints are inside that set.
    """
    from . import canvas, port_mode2str, port_type2str

    node_set = set(nodes) if nodes else None

    node_index = {}
    node_list = []

    for group, widget in _all_node_widgets():
        if node_set is not None and widget not in node_set:
            continue
        rect = widget.sceneBoundingRect()
        node_index[widget] = len(node_list)
        node_list.append({
            "index": len(node_list),
            "group_id": getattr(group, "group_id", -1),
            "name": getattr(group, "group_name", ""),
            "split": getattr(group, "split", 0),
            "pos": [float(rect.left()), float(rect.top())],
            "size": [float(rect.width()), float(rect.height())],
            "rect": [float(rect.left()), float(rect.top()),
                     float(rect.width()), float(rect.height())],
            "ports": [],
        })

    # ports: map (group_id, port_id) -> owning node index, and append to the node
    port_node = {}
    for port in canvas.port_list:
        widget = getattr(port, "widget", None)
        if widget is None:
            continue
        node_widget = widget.parentItem()
        idx = node_index.get(node_widget)
        if idx is None:
            continue
        port_node[(port.group_id, port.port_id)] = idx
        node_list[idx]["ports"].append({
            "port_id": port.port_id,
            "name": getattr(port, "port_name", ""),
            "mode": port.port_mode,
            "mode_str": port_mode2str(port.port_mode),
            "type": port.port_type,
            "type_str": port_type2str(port.port_type),
            "alternate": bool(getattr(port, "is_alternate", False)),
        })

    connection_list = []
    for connection in canvas.connection_list:
        out_idx = port_node.get((connection.group_out_id, connection.port_out_id))
        in_idx = port_node.get((connection.group_in_id, connection.port_in_id))
        if out_idx is None or in_idx is None:
            continue
        connection_list.append({
            "connection_id": connection.connection_id,
            "out": {
                "node": out_idx,
                "group_id": connection.group_out_id,
                "port_id": connection.port_out_id,
            },
            "in": {
                "node": in_idx,
                "group_id": connection.group_in_id,
                "port_id": connection.port_in_id,
            },
        })

    graph = {
        "nodes": node_list,
        "connections": connection_list,
    }

    if include_topology:
        graph["topology"] = _topology(len(node_list), connection_list)

    return graph


def _topology(count, connection_list):
    edges = [set() for _ in range(count)]
    incoming = [set() for _ in range(count)]

    for connection in connection_list:
        src = connection["out"]["node"]
        dst = connection["in"]["node"]
        if src == dst:
            continue
        edges[src].add(dst)
        incoming[dst].add(src)

    edges = [sorted(s) for s in edges]
    incoming = [sorted(s) for s in incoming]

    neighbours = [set(edges[i]) | set(incoming[i]) for i in range(count)]
    degree = [len(neighbours[i]) for i in range(count)]

    # connected components over the undirected graph
    seen = set()
    components = []
    for start in range(count):
        if start in seen:
            continue
        seen.add(start)
        stack = [start]
        comp = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in neighbours[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        components.append(sorted(comp))

    # longest-path layering (nodes inside a cycle settle at their first layer)
    layer = [0] * count
    for _ in range(count):
        changed = False
        for src in range(count):
            for dst in edges[src]:
                if layer[dst] < layer[src] + 1:
                    layer[dst] = layer[src] + 1
                    changed = True
        if not changed:
            break

    return {
        "edges": edges,
        "incoming": incoming,
        "degree": degree,
        "components": components,
        "layers": layer,
    }


def nodes_of_graph(graph):
    """Return the raw node dicts of a graph model."""
    return graph.get("nodes", [])


def graph_to_json(graph, indent=None):
    """Serialise a :func:`collect_graph` result to a JSON string."""
    return json.dumps(graph, indent=indent, sort_keys=False)
