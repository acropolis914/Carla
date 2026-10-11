#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import json
import xml.etree.ElementTree as ET

class ProjectFormatError(Exception):
    pass

def xml_elem_to_dict(elem):
    """Losslessly converts an XML ElementTree element into a Python dict/data structure."""
    node = {}
    if elem.attrib:
        node["@attributes"] = dict(elem.attrib)

    text = elem.text.strip() if elem.text and elem.text.strip() else None
    children = list(elem)
    if children:
        child_dict = {}
        for child in children:
            cd = xml_elem_to_dict(child)
            tag = child.tag
            if tag in child_dict:
                if not isinstance(child_dict[tag], list):
                    child_dict[tag] = [child_dict[tag]]
                child_dict[tag].append(cd)
            else:
                child_dict[tag] = cd
        if text:
            child_dict["#text"] = text
        node.update(child_dict)
    elif text:
        if elem.attrib:
            node["#text"] = text
            return node
        return text

    return node

def dict_to_xml_elem(tag, data):
    """Reconstructs an XML ElementTree element from the dictionary structure."""
    elem = ET.Element(tag)
    if isinstance(data, dict):
        if "@attributes" in data:
            for k, v in data["@attributes"].items():
                elem.set(str(k), str(v))
        if "#text" in data:
            elem.text = str(data["#text"])

        for k, v in data.items():
            if k in ("@attributes", "#text"):
                continue
            if isinstance(v, list):
                for item in v:
                    elem.append(dict_to_xml_elem(k, item))
            else:
                elem.append(dict_to_xml_elem(k, v))
    elif data is not None:
        elem.text = str(data)

    return elem


class BaseProjectHandler:
    def can_handle(self, filepath):
        raise NotImplementedError

    def load_positions(self, filepath):
        raise NotImplementedError

    def save_positions(self, filepath, positions):
        raise NotImplementedError

    def load_full_project_as_xml_path(self, filepath):
        """Returns a path to an XML project file (either the file itself or a converted tmp file)"""
        raise NotImplementedError

    def save_full_project_from_xml_path(self, target_filepath, source_xml_path):
        """Saves a full project to target_filepath from source_xml_path"""
        raise NotImplementedError


class CarlaXmlProjectHandler(BaseProjectHandler):
    """Handler for Carla .carxp XML projects (100% backward compatible)"""
    def can_handle(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return False
        if filepath.lower().endswith(".carxp"):
            return True
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(256)
                return "<CARLA-PROJECT" in head
        except Exception:
            return False

    def load_positions(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return []
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            if root.tag != "CARLA-PROJECT":
                return []

            data_list = []
            canvas_elem = root.find("CanvasPositions")
            if canvas_elem is not None:
                for p_elem in canvas_elem.findall("Position"):
                    name = p_elem.get("name", "")
                    if name:
                        data_list.append({
                            "name": name,
                            "pos1x": float(p_elem.get("pos1x", 0)),
                            "pos1y": float(p_elem.get("pos1y", 0)),
                            "pos2x": float(p_elem.get("pos2x", 0)),
                            "pos2y": float(p_elem.get("pos2y", 0)),
                            "split": p_elem.get("split") in ("1", "true", "True"),
                        })

            if not data_list:
                for pb_tag in ("Patchbay", "ExternalPatchbay"):
                    pb_elem = root.find(pb_tag)
                    if pb_elem is not None:
                        pos_elem = pb_elem.find("Positions")
                        if pos_elem is not None:
                            for p_elem in pos_elem.findall("Position"):
                                name_elem = p_elem.find("Name")
                                name = name_elem.text if name_elem is not None else ""
                                if name:
                                    x1 = float(p_elem.get("x1", 0))
                                    y1 = float(p_elem.get("y1", 0))
                                    x2 = float(p_elem.get("x2", 0))
                                    y2 = float(p_elem.get("y2", 0))
                                    data_list.append({
                                        "name": name,
                                        "pos1x": x1,
                                        "pos1y": y1,
                                        "pos2x": x2,
                                        "pos2y": y2,
                                        "split": (x2 != 0 or y2 != 0),
                                    })
            return data_list
        except Exception as e:
            print("CarlaXmlProjectHandler::load_positions error:", e)
            return []

    def save_positions(self, filepath, positions):
        if not filepath or not os.path.exists(filepath):
            return False
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            if root.tag != "CARLA-PROJECT":
                return False

            for child in list(root):
                if child.tag == "CanvasPositions":
                    root.remove(child)

            canvas_pos_elem = ET.SubElement(root, "CanvasPositions")
            for pos_data in positions:
                name = str(pos_data.get("name", "")).strip()
                if not name:
                    continue
                p_elem = ET.SubElement(canvas_pos_elem, "Position")
                p_elem.set("name", name)
                p_elem.set("pos1x", str(int(round(pos_data.get("pos1x", 0)))))
                p_elem.set("pos1y", str(int(round(pos_data.get("pos1y", 0)))))
                p_elem.set("pos2x", str(int(round(pos_data.get("pos2x", 0)))))
                p_elem.set("pos2y", str(int(round(pos_data.get("pos2y", 0)))))
                p_elem.set("split", "1" if pos_data.get("split") else "0")

            tree.write(filepath, encoding="UTF-8", xml_declaration=True)
            return True
        except Exception as e:
            print("CarlaXmlProjectHandler::save_positions error:", e)
            return False

    def load_full_project_as_xml_path(self, filepath, force_bridged=False):
        if not force_bridged:
            return filepath
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            if root.tag == "CARLA-PROJECT":
                eng_settings = root.find("EngineSettings")
                if eng_settings is None:
                    eng_settings = ET.SubElement(root, "EngineSettings")
                pref = eng_settings.find("PreferPluginBridges")
                if pref is None:
                    pref = ET.SubElement(eng_settings, "PreferPluginBridges")
                pref.text = "true"
                tmp_xml = filepath + "._tmp_force_bridge.carxp"
                tree.write(tmp_xml, encoding="UTF-8", xml_declaration=True)
                return tmp_xml
        except Exception as e:
            print("CarlaXmlProjectHandler::load_full_project_as_xml_path force_bridged error:", e)
        return filepath

    def save_full_project_from_xml_path(self, target_filepath, source_xml_path):
        if target_filepath != source_xml_path:
            import shutil
            shutil.copy2(source_xml_path, target_filepath)
        return True


class CarlaJsonProjectHandler(BaseProjectHandler):
    """Handler for modern Carla JSON projects (.carjp, .json) with full validation"""
    def can_handle(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return False
        if filepath.lower().endswith((".carjp", ".json")):
            return True
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(128).strip()
                return head.startswith("{") and ("carla" in head.lower() or "canvas_positions" in head.lower())
        except Exception:
            return False

    def _read_json(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            doc = json.load(f)
        if not isinstance(doc, dict):
            raise ProjectFormatError("Invalid JSON root: expected object")
        return doc

    def load_positions(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return []
        try:
            doc = self._read_json(filepath)
            positions = []
            if "CARLA-PROJECT" in doc and isinstance(doc["CARLA-PROJECT"], dict):
                c_pos = doc["CARLA-PROJECT"].get("CanvasPositions", {})
                if isinstance(c_pos, dict):
                    pos_entries = c_pos.get("Position", [])
                    if isinstance(pos_entries, dict):
                        pos_entries = [pos_entries]
                    for pe in pos_entries:
                        attrs = pe.get("@attributes", pe)
                        if "name" in attrs:
                            positions.append({
                                "name": str(attrs["name"]),
                                "pos1x": float(attrs.get("pos1x", 0)),
                                "pos1y": float(attrs.get("pos1y", 0)),
                                "pos2x": float(attrs.get("pos2x", 0)),
                                "pos2y": float(attrs.get("pos2y", 0)),
                                "split": str(attrs.get("split", "0")) in ("1", "true", "True"),
                            })

            if not positions:
                raw_positions = doc.get("canvas_positions", doc.get("positions", []))
                for p in raw_positions:
                    if isinstance(p, dict) and "name" in p:
                        positions.append({
                            "name": str(p["name"]),
                            "pos1x": float(p.get("pos1x", 0)),
                            "pos1y": float(p.get("pos1y", 0)),
                            "pos2x": float(p.get("pos2x", 0)),
                            "pos2y": float(p.get("pos2y", 0)),
                            "split": bool(p.get("split", False)),
                        })

            return positions
        except Exception as e:
            print("CarlaJsonProjectHandler::load_positions error:", e)
            return []

    def save_positions(self, filepath, positions):
        try:
            doc = {}
            if os.path.exists(filepath):
                try:
                    doc = self._read_json(filepath)
                except Exception:
                    doc = {}

            if "CARLA-PROJECT" in doc and isinstance(doc["CARLA-PROJECT"], dict):
                canvas_pos_elem = {"Position": []}
                for p in positions:
                    name = str(p.get("name", "")).strip()
                    if not name:
                        continue
                    canvas_pos_elem["Position"].append({
                        "@attributes": {
                            "name": name,
                            "pos1x": str(int(round(p.get("pos1x", 0)))),
                            "pos1y": str(int(round(p.get("pos1y", 0)))),
                            "pos2x": str(int(round(p.get("pos2x", 0)))),
                            "pos2y": str(int(round(p.get("pos2y", 0)))),
                            "split": "1" if p.get("split") else "0",
                        }
                    })
                doc["CARLA-PROJECT"]["CanvasPositions"] = canvas_pos_elem
            else:
                doc["format"] = "carla-project-json"
                doc["version"] = "1.0"
                clean_positions = []
                for p in positions:
                    name = str(p.get("name", "")).strip()
                    if not name:
                        continue
                    clean_positions.append({
                        "name": name,
                        "pos1x": int(round(p.get("pos1x", 0))),
                        "pos1y": int(round(p.get("pos1y", 0))),
                        "pos2x": int(round(p.get("pos2x", 0))),
                        "pos2y": int(round(p.get("pos2y", 0))),
                        "split": bool(p.get("split", False)),
                    })
                doc["canvas_positions"] = clean_positions

            tmp_path = filepath + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent="\t")
            os.replace(tmp_path, filepath)
            return True
        except Exception as e:
            print("CarlaJsonProjectHandler::save_positions error:", e)
            return False

    def load_full_project_as_xml_path(self, filepath, force_bridged=False):
        """Converts full JSON project (.carjp) into an XML ElementTree file for Carla backend loading."""
        doc = self._read_json(filepath)
        if "CARLA-PROJECT" not in doc:
            raise ProjectFormatError("Missing CARLA-PROJECT root key in JSON project")

        project_dict = dict(doc["CARLA-PROJECT"])
        if force_bridged:
            eng_settings = dict(project_dict.get("EngineSettings", {}))
            eng_settings["PreferPluginBridges"] = "true"
            project_dict["EngineSettings"] = eng_settings

        root = dict_to_xml_elem("CARLA-PROJECT", project_dict)
        tree = ET.ElementTree(root)

        tmp_xml_path = filepath + "._tmp_carla_load.carxp"
        tree.write(tmp_xml_path, encoding="UTF-8", xml_declaration=True)
        return tmp_xml_path

    def save_full_project_from_xml_path(self, target_filepath, source_xml_path):
        """Converts saved XML project from Carla backend into validated .carjp JSON format."""
        tree = ET.parse(source_xml_path)
        root = tree.getroot()
        if root.tag != "CARLA-PROJECT":
            raise ProjectFormatError("Source is not a valid CARLA-PROJECT XML")

        doc = {
            "format": "carla-project-json",
            "version": "1.0",
            "CARLA-PROJECT": xml_elem_to_dict(root)
        }

        tmp_target = target_filepath + ".tmp"
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent="\t")
        os.replace(tmp_target, target_filepath)
        return True


class ProjectStorageManager:
    """Dispatches and coordinates project file persistence across formats"""
    EXTENSION_MAP = {
        "xml": ".carxp",
        "json": ".carjp",
    }

    def __init__(self):
        self._handlers = [
            CarlaJsonProjectHandler(),
            CarlaXmlProjectHandler(),
        ]

    def get_handler(self, filepath):
        for h in self._handlers:
            if h.can_handle(filepath):
                return h
        # Fallback to extension check
        if str(filepath).lower().endswith((".carjp", ".json")):
            return self._handlers[0]
        return self._handlers[1]

    def load_canvas_positions(self, filepath):
        handler = self.get_handler(filepath)
        return handler.load_positions(filepath)

    def save_canvas_positions(self, filepath, positions):
        handler = self.get_handler(filepath)
        return handler.save_positions(filepath, positions)

    def prepare_for_backend_load(self, filepath, force_bridged=False):
        """Prepares a file path readable by the C++ engine (converts .carjp to temporary xml if needed)"""
        handler = self.get_handler(filepath)
        return handler.load_full_project_as_xml_path(filepath, force_bridged=force_bridged)

    def finalize_from_backend_save(self, target_filepath, backend_saved_filepath, positions=None):
        """Finalizes backend save into target format and writes canvas positions."""
        handler = self.get_handler(target_filepath)
        handler.save_full_project_from_xml_path(target_filepath, backend_saved_filepath)
        if positions is not None:
            handler.save_positions(target_filepath, positions)
        return True

storage_manager = ProjectStorageManager()
