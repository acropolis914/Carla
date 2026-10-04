#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import json
import subprocess

from qt_compat import qt_config

if qt_config == 5:
    from PyQt5.QtCore import qCritical, QPointF, QTimer
elif qt_config == 6:
    from PyQt6.QtCore import qCritical, QPointF, QTimer

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import bool2str, canvas, CanvasBoxType
import sys

try:
    from carla_shared import log_carla
except Exception:
    def log_carla(msg, level="info"):
        try:
            with open("/tmp/carla.log", "a") as f:
                f.write(str(msg) + "\n")
        except Exception:
            pass
        print(str(msg), file=sys.stderr, flush=True)


# Optional PipeWire display names, keyed by JACK client and port names.
_pipewire_port_names = {}
_pipewire_port_name_candidates = {}
_pipewire_serial_to_media = {}
_pipewire_node_first_serial = {}
_pipewire_available = True
_pipewire_last_dump_time = 0.0


def _updatePipewirePortNames():
    global _pipewire_available, _pipewire_last_dump_time
    import time
    if not _pipewire_available:
        return

    now = time.time()
    if now - _pipewire_last_dump_time < 2.0:
        return
    _pipewire_last_dump_time = now

    _pipewire_port_names.clear()
    _pipewire_port_name_candidates.clear()
    _pipewire_serial_to_media.clear()
    _pipewire_node_first_serial.clear()
    try:
        output = subprocess.check_output(
            ("pw-dump",), stderr=subprocess.DEVNULL, text=True
        )
        objects = json.loads(output)
        nodes = {
            obj["id"]: obj.get("info", {}).get("props", {})
            for obj in objects
            if obj.get("type") == "PipeWire:Interface:Node"
        }
        for obj in objects:
            if obj.get("type") != "PipeWire:Interface:Port":
                continue
            props = obj.get("info", {}).get("props", {})
            node_props = nodes.get(props.get("node.id"), {})
            display_name = node_props.get("media.name")
            node_name = node_props.get("node.name")
            port_name = props.get("port.name")
            port_alias = props.get("port.alias", "")
            serial = props.get("object.serial")
            if serial is not None and display_name:
                _pipewire_serial_to_media[str(serial)] = display_name
            if node_name and display_name:
                if node_name not in _pipewire_node_first_serial:
                    _pipewire_node_first_serial[node_name] = display_name
            if display_name and node_name and port_name:
                key = (node_name, port_name)
                candidates = _pipewire_port_name_candidates.setdefault(key, [])
                if display_name not in candidates:
                    candidates.append(display_name)
                if ":" in port_alias:
                    alias_group, alias_port = port_alias.rsplit(":", 1)
                    alias_key = (alias_group, alias_port)
                    candidates = _pipewire_port_name_candidates.setdefault(
                        alias_key, []
                    )
                    if display_name not in candidates:
                        candidates.append(display_name)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        _pipewire_available = False


def CanvasGetPortDisplayName(group_name, port_name):
    raw_group_name = group_name.split(": ", 1)[0] if ": " in group_name else group_name
    key = (raw_group_name, port_name)
    if key not in _pipewire_port_names:
        _updatePipewirePortNames()

    display_name = _pipewire_port_names.get(key)
    if display_name is None and "-" in port_name:
        base_name, suffix = port_name.rsplit("-", 1)
        if suffix.isdigit():
            display_name = _pipewire_serial_to_media.get(suffix)
    if display_name is None and "-" not in port_name:
        if raw_group_name in _pipewire_node_first_serial:
            display_name = _pipewire_node_first_serial[raw_group_name]
    if display_name is None:
        candidates = _pipewire_port_name_candidates.get(key, [])
        if candidates:
            display_name = candidates[0]

    result = display_name or port_name
    _pipewire_port_names[key] = result
    if group_name != raw_group_name:
        _pipewire_port_names[(group_name, port_name)] = result
    return result


from .canvasfadeanimation import CanvasFadeAnimation

# ------------------------------------------------------------------------------------------------------------


def CanvasGetNewGroupPos(horizontal):
    if canvas.debug:
        print("PatchCanvas::CanvasGetNewGroupPos(%s)" % bool2str(horizontal))

    new_pos = QPointF(canvas.initial_pos)
    items = canvas.scene.items()

    # break_loop = False
    while True:
        break_for = False
        for i, item in enumerate(items):
            if item and item.type() == CanvasBoxType:
                if item.sceneBoundingRect().adjusted(-5, -5, 5, 5).contains(new_pos):
                    itemRect = item.boundingRect()
                    if horizontal:
                        new_pos += QPointF(itemRect.width() + 50, 0)
                    else:
                        itemHeight = itemRect.height()
                        if itemHeight < 30:
                            new_pos += QPointF(0, itemHeight + 50)
                        else:
                            new_pos.setY(item.scenePos().y() + itemHeight + 20)
                    break_for = True
                    break
        else:
            if not break_for:
                break
            # break_loop = True

    return new_pos


def CanvasGetFullPortName(group_id, port_id):
    if canvas.debug:
        print("PatchCanvas::CanvasGetFullPortName(%i, %i)" % (group_id, port_id))

    for port in canvas.port_list:
        if port.group_id == group_id and port.port_id == port_id:
            group_id = port.group_id
            for group in canvas.group_list:
                if group.group_id == group_id:
                    return group.group_name + ":" + port.port_name
            break

    qCritical(
        "PatchCanvas::CanvasGetFullPortName(%i, %i) - unable to find port"
        % (group_id, port_id)
    )
    return ""


def CanvasGetPortConnectionList(group_id, port_id):
    if canvas.debug:
        print("PatchCanvas::CanvasGetPortConnectionList(%i, %i)" % (group_id, port_id))

    conn_list = []

    for connection in canvas.connection_list:
        if connection.group_out_id == group_id and connection.port_out_id == port_id:
            conn_list.append(
                (
                    connection.connection_id,
                    connection.group_in_id,
                    connection.port_in_id,
                )
            )
        elif connection.group_in_id == group_id and connection.port_in_id == port_id:
            conn_list.append(
                (
                    connection.connection_id,
                    connection.group_out_id,
                    connection.port_out_id,
                )
            )

    return conn_list


def CanvasCallback(action, value1, value2, value_str):
    if canvas.debug:
        print(
            "PatchCanvas::CanvasCallback(%i, %i, %i, %s)"
            % (action, value1, value2, value_str.encode())
        )

    canvas.callback(action, value1, value2, value_str)


def CanvasItemFX(item, show, destroy):
    if canvas.debug:
        print(
            "PatchCanvas::CanvasItemFX(%s, %s, %s)"
            % (item, bool2str(show), bool2str(destroy))
        )

    # Check if the item already has an animation
    for animation in canvas.animation_list:
        if animation.item() == item:
            animation.forceStop()
            canvas.animation_list.remove(animation)
            del animation
            break

    animation = CanvasFadeAnimation(item, show)
    animation.setDuration(750 if show else 500)

    if show:
        animation.finished.connect(canvas.qobject.AnimationFinishedShow)
    else:
        if destroy:
            animation.finished.connect(canvas.qobject.AnimationFinishedDestroy)
        else:
            animation.finished.connect(canvas.qobject.AnimationFinishedHide)

    canvas.animation_list.append(animation)

    animation.start()


def CanvasRemoveItemFX(item):
    if canvas.debug:
        print("PatchCanvas::CanvasRemoveItemFX(%s)" % item)

    if item.type() == CanvasBoxType:
        item.removeIconFromScene()

    canvas.scene.removeItem(item)
    del item

    QTimer.singleShot(0, canvas.scene.update)


# ------------------------------------------------------------------------------------------------------------
