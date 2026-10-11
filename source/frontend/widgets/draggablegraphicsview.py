#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ---------------------------------------------------------------------------------------------------------------------
# Imports (Global)

import os

from qt_compat import qt_config

if qt_config == 5:
    from PyQt5.QtCore import Qt, QT_VERSION, QEvent, pyqtSignal
    from PyQt5.QtGui import QCursor, QMouseEvent, QKeySequence
    from PyQt5.QtWidgets import (
        QGraphicsView,
        QMessageBox,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QShortcut,
    )
elif qt_config == 6:
    from PyQt6.QtCore import Qt, QT_VERSION, QEvent, pyqtSignal
    from PyQt6.QtGui import QCursor, QMouseEvent, QKeySequence, QShortcut
    from PyQt6.QtWidgets import (
        QGraphicsView,
        QMessageBox,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
    )

# ---------------------------------------------------------------------------------------------------------------------
# Imports (Custom Stuff)

from carla_backend import CARLA_OS_MAC
from carla_shared import CustomMessageBox, gCarla

# Modal Tool Constants
TOOL_POINTER = 0   # Default mode (Q / Esc)
TOOL_SELECT  = 1   # Marquee selection mode (V)
TOOL_HAND    = 2   # Canvas hand/drag mode (H / Space)

# ---------------------------------------------------------------------------------------------------------------------
# Widget Class

class DraggableGraphicsView(QGraphicsView):
    toolModeChanged = pyqtSignal(int)

    def __init__(self, parent):
        QGraphicsView.__init__(self, parent)

        self.fPanning = False
        self.fToolMode = TOOL_POINTER
        self.fSpacePanning = False

        exts = gCarla.utils.get_supported_file_extensions()

        self.fSupportedExtensions = tuple(("." + i) for i in exts)
        self.fWasLastDragValid = False

        self.setAcceptDrops(True)
        self.initSearchWidgets()

    def setToolMode(self, mode):
        self.fToolMode = mode
        if mode == TOOL_HAND:
            self.setCursor(QCursor(Qt.OpenHandCursor))
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        elif mode == TOOL_SELECT:
            self.setCursor(QCursor(Qt.CrossCursor))
            self.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            self.fToolMode = TOOL_POINTER
            self.unsetCursor()
            self.setDragMode(QGraphicsView.NoDrag)
        self.toolModeChanged.emit(self.fToolMode)

    def keyPressEvent(self, event):
        # Ignore tool hotkeys if searching
        if hasattr(self, "fSearchEdit") and self.fSearchEdit.isVisible():
            QGraphicsView.keyPressEvent(self, event)
            return

        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_F:
            event.accept()
            self.toggleSearch()
            return

        # Modal shortcuts: V = Select, H = Hand, Q/Esc = Pointer
        if not (event.modifiers() & (Qt.ControlModifier | Qt.AltModifier)):
            if event.key() == Qt.Key_V:
                event.accept()
                self.setToolMode(TOOL_SELECT)
                return
            elif event.key() == Qt.Key_H:
                event.accept()
                self.setToolMode(TOOL_HAND)
                return
            elif event.key() in (Qt.Key_Q, Qt.Key_Escape):
                event.accept()
                self.setToolMode(TOOL_POINTER)
                return
            elif event.key() == Qt.Key_Space and not event.isAutoRepeat():
                event.accept()
                self.fSpacePanning = True
                self.setCursor(QCursor(Qt.OpenHandCursor))
                self.setDragMode(QGraphicsView.ScrollHandDrag)
                return

        QGraphicsView.keyPressEvent(self, event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat() and getattr(self, "fSpacePanning", False):
            event.accept()
            self.fSpacePanning = False
            self.setToolMode(self.fToolMode)
            return
        QGraphicsView.keyReleaseEvent(self, event)

    # -----------------------------------------------------------------------------------------------------------------

    def isDragUrlValid(self, filename):
        lfilename = filename.lower()

        if os.path.isdir(filename):
            #if os.path.exists(os.path.join(filename, "manifest.ttl")):
                #return True
            if CARLA_OS_MAC and lfilename.endswith(".vst"):
                return True
            if lfilename.endswith(".vst3") and ".vst3" in self.fSupportedExtensions:
                return True

        elif os.path.isfile(filename):
            if lfilename.endswith(self.fSupportedExtensions):
                return True

        return False

    # -----------------------------------------------------------------------------------------------------------------

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()

        for url in urls:
            if self.isDragUrlValid(url.toLocalFile()):
                self.fWasLastDragValid = True
                event.acceptProposedAction()
                return

        self.fWasLastDragValid = False
        QGraphicsView.dragEnterEvent(self, event)

    def dragMoveEvent(self, event):
        if not self.fWasLastDragValid:
            QGraphicsView.dragMoveEvent(self, event)
            return

        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.fWasLastDragValid = False
        QGraphicsView.dragLeaveEvent(self, event)

    # -----------------------------------------------------------------------------------------------------------------

    def dropEvent(self, event):
        event.acceptProposedAction()

        urls = event.mimeData().urls()

        if len(urls) == 0:
            return

        for url in urls:
            filename = url.toLocalFile()

            if not gCarla.gui.host.load_file(filename):
                CustomMessageBox(self, QMessageBox.Critical, self.tr("Error"),
                                 self.tr("Failed to load file"),
                                 gCarla.gui.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok)

    def mousePressEvent(self, event):
        if (event.button() == Qt.MiddleButton and not (event.modifiers() & Qt.ControlModifier)) or (
            event.button() == Qt.LeftButton and (self.fToolMode == TOOL_HAND or getattr(self, "fSpacePanning", False))
        ):
            self.fPanning = True
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            timestamp = event.timestamp()
            QGraphicsView.mousePressEvent(self, event)
            if timestamp is not None:
                if qt_config == 5:
                    synth_event = QMouseEvent(QEvent.MouseButtonPress,
                                        event.localPos(), event.windowPos(), event.screenPos(),
                                        Qt.LeftButton, Qt.LeftButton,
                                        Qt.NoModifier,
                                        Qt.MouseEventSynthesizedByApplication)
                    synth_event.setTimestamp(timestamp)
                else:
                    synth_event = QMouseEvent(QEvent.MouseButtonPress,
                                        event.position(), event.scenePosition(), event.globalPosition(),
                                        Qt.LeftButton, Qt.LeftButton,
                                        Qt.NoModifier)
                QGraphicsView.mousePressEvent(self, synth_event)
            return

        if event.button() == Qt.LeftButton and self.fToolMode == TOOL_SELECT:
            self.setDragMode(QGraphicsView.RubberBandDrag)
            QGraphicsView.mousePressEvent(self, event)
            return

        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if getattr(self, "fPanning", False) and (
            event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton
        ):
            self.fPanning = False
            if getattr(self, "fSpacePanning", False):
                self.setCursor(QCursor(Qt.OpenHandCursor))
            else:
                self.setToolMode(self.fToolMode)

        QGraphicsView.mouseReleaseEvent(self, event)

    def wheelEvent(self, event):
        if event.buttons() & Qt.MiddleButton:
            event.ignore()
            return
            
        # Standard: Ctrl+Scroll -> Zoom
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y() if hasattr(event, "angleDelta") else event.delta()
            sc = self.scene()
            if sc and hasattr(sc, "zoom_wheel"):
                sc.zoom_wheel(delta)
            else:
                zoom_factor = 1.15 if delta > 0 else 1.0 / 1.15
                self.scale(zoom_factor, zoom_factor)
            event.accept()
            return
            
        # Standard: Shift+Scroll -> Horizontal Pan
        if event.modifiers() & Qt.ShiftModifier:
            delta = event.angleDelta().y() if hasattr(event, "angleDelta") else event.delta()
            if hasattr(event, "angleDelta") and event.angleDelta().x() != 0:
                delta = event.angleDelta().x()
                
            sb = self.horizontalScrollBar()
            if sb:
                sb.setValue(sb.value() - delta)
            event.accept()
            return

        QGraphicsView.wheelEvent(self, event)

    # -----------------------------------------------------------------------------------------------------------------
    # Canvas Node Quick Search

    def initSearchWidgets(self):
        if hasattr(self, "fSearchEdit"):
            return

        self.fSearchEdit = QLineEdit(self)
        self.fSearchEdit.setPlaceholderText("Search canvas nodes... (Esc to close)")
        self.fSearchEdit.setStyleSheet(
            "QLineEdit { background: #222; color: #fff; border: 1.5px solid #ffaa00; "
            "border-radius: 4px; padding: 4px 8px; font-size: 13px; }"
        )
        self.fSearchEdit.hide()

        self.fSearchList = QListWidget(self)
        self.fSearchList.setStyleSheet(
            "QListWidget { background: #1c1c1c; color: #ddd; border: 1px solid #444; "
            "border-radius: 4px; outline: none; font-size: 12px; }"
            "QListWidget::item { padding: 4px 8px; }"
            "QListWidget::item:selected, QListWidget::item:hover { background: #ff8800; color: #000; font-weight: bold; }"
        )
        self.fSearchList.hide()

        self.fSearchEdit.textChanged.connect(self._onSearchTextChanged)
        self.fSearchEdit.returnPressed.connect(self._onSearchAccept)
        self.fSearchList.itemClicked.connect(self._onSearchItemClicked)
        self.fSearchList.currentRowChanged.connect(self._onSearchRowChanged)

        self.fSearchEdit.installEventFilter(self)
        self.fSearchList.installEventFilter(self)

        shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut.activated.connect(self.toggleSearch)

    def toggleSearch(self):
        self.initSearchWidgets()
        if self.fSearchEdit.isVisible():
            self.hideSearch()
        else:
            w = 260
            self.fSearchEdit.setGeometry(12, 12, w, 28)
            self.fSearchEdit.clear()
            self.fSearchEdit.show()
            self.fSearchEdit.raise_()
            self.fSearchEdit.setFocus()

    def hideSearch(self):
        self._clearHighlights()
        if hasattr(self, "fSearchEdit"):
            self.fSearchEdit.hide()
        if hasattr(self, "fSearchList"):
            self.fSearchList.hide()
        self.setFocus()

    def _getCanvasBoxes(self):
        from patchcanvas import canvas
        boxes = []
        for grp in getattr(canvas, "group_list", []):
            if grp.widgets and grp.widgets[0]:
                boxes.append((grp.group_name, grp.widgets[0]))
        return boxes

    def _clearHighlights(self):
        for _, box in self._getCanvasBoxes():
            if getattr(box, "m_search_highlight", 0) != 0:
                box.m_search_highlight = 0
                box.update()

    def _fuzzyScore(self, pattern, text):
        import difflib
        p, t = pattern.lower(), text.lower()
        if p in t:
            return 100.0 + (len(p) / float(len(t)))
        return difflib.SequenceMatcher(None, p, t).ratio() * 100.0

    def _onSearchTextChanged(self, text):
        pattern = text.strip()
        self._clearHighlights()
        self.fSearchList.clear()

        if not pattern:
            self.fSearchList.hide()
            return

        matches = []
        for name, box in self._getCanvasBoxes():
            score = self._fuzzyScore(pattern, name)
            if score > 35.0:
                matches.append((score, name, box))

        matches.sort(key=lambda x: x[0], reverse=True)

        for _, name, box in matches:
            box.m_search_highlight = 1
            box.update()
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, box)
            self.fSearchList.addItem(item)

        if matches:
            list_h = min(160, max(40, len(matches) * 26 + 6))
            self.fSearchList.setGeometry(12, 42, 260, list_h)
            self.fSearchList.show()
            self.fSearchList.raise_()
            self.fSearchList.setCurrentRow(0)
        else:
            self.fSearchList.hide()

    def _onSearchRowChanged(self, row):
        for i in range(self.fSearchList.count()):
            item = self.fSearchList.item(i)
            box = item.data(Qt.UserRole)
            if box:
                box.m_search_highlight = 2 if i == row else 1
                box.update()

    def _onSearchAccept(self):
        item = self.fSearchList.currentItem()
        if item:
            self._selectAndCenter(item.data(Qt.UserRole))

    def _onSearchItemClicked(self, item):
        if item:
            self._selectAndCenter(item.data(Qt.UserRole))

    def _selectAndCenter(self, target_box):
        self.hideSearch()
        if not target_box or not self.scene():
            return
        self.scene().clearSelection()
        self.centerOn(target_box)
        target_box.setSelected(True)

    def eventFilter(self, obj, event):
        key_press_type = QEvent.Type.KeyPress if hasattr(QEvent, "Type") else QEvent.KeyPress
        if event.type() == key_press_type:
            if event.key() == Qt.Key_Escape:
                self.hideSearch()
                return True
            if obj == self.fSearchEdit:
                if event.key() in (Qt.Key_Down, Qt.Key_Up):
                    if self.fSearchList.isVisible():
                        self.fSearchList.setFocus()
                        if event.key() == Qt.Key_Down and self.fSearchList.currentRow() < self.fSearchList.count() - 1:
                            self.fSearchList.setCurrentRow(self.fSearchList.currentRow() + 1)
                        elif event.key() == Qt.Key_Up and self.fSearchList.currentRow() > 0:
                            self.fSearchList.setCurrentRow(self.fSearchList.currentRow() - 1)
                        return True
            elif obj == self.fSearchList:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    self._onSearchAccept()
                    return True
                elif event.key() == Qt.Key_Up and self.fSearchList.currentRow() == 0:
                    self.fSearchEdit.setFocus()
                    return True
        return QGraphicsView.eventFilter(self, obj, event)

# ---------------------------------------------------------------------------------------------------------------------
