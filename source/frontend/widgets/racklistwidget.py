#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import os

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)

from qt_compat import (
    Qt,
    QSize,
    QRect,
    QEvent,
    QColor,
    QPainter,
    QPixmap,
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QTimer,
)

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom Stuff)

from carla_backend import CARLA_OS_MAC, CUSTOM_DATA_TYPE_PROPERTY
from carla_shared import gCarla, CustomMessageBox, CARLA_KEY_CANVAS_THEME, CARLA_DEFAULT_CANVAS_THEME
from carla_skin import createPluginSlot
from utils import QSafeSettings
from patchcanvas.theme import Theme

# ------------------------------------------------------------------------------------------------------------
# Rack Widget item

class RackListItem(QListWidgetItem):
    kRackItemType = QListWidgetItem.UserType + 1
    kMinimumWidth = 200

    def __init__(self, parent, pluginId, useClassicSkin):
        QListWidgetItem.__init__(self, parent, self.kRackItemType)
        self.host = parent.host

        # ----------------------------------------------------------------------------------------------------
        # Internal stuff

        self.fParent   = parent
        self.fPluginId = pluginId
        self.fWidget   = None

        color   = self.host.get_custom_data_value(pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor")
        skin    = self.host.get_custom_data_value(pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin")
        compact = bool(self.host.get_custom_data_value(pluginId,
                                                       CUSTOM_DATA_TYPE_PROPERTY,
                                                       "CarlaSkinIsCompacted") == "true")

        if color:
            try:
                color = tuple(int(i) for i in color.split(";",3))
            except Exception as e:
                print("Color value decode failed for", color, "error was:", e)
                color = None
        else:
            color = None

        if useClassicSkin and not skin:
            skin = "minimal-dark"

        self.fOptions = {
            'color'  : color,
            'skin'   : skin,
            'compact': compact,
        }

        self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        #self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled|Qt.ItemIsDragEnabled)

        # ----------------------------------------------------------------------------------------------------
        # Set-up GUI

        self.recreateWidget(firstInit = True)

    # --------------------------------------------------------------------------------------------------------

    def close(self):
        if self.fWidget is None:
            return

        widget = self.fWidget
        self.fWidget = None

        self.fParent.customClearSelection()
        self.fParent.setItemWidget(self, None)

        widget.fEditDialog.close()
        widget.fEditDialog.setParent(None)
        widget.fEditDialog.deleteLater()
        widget.fEditDialog = None

        widget.close()
        widget.setParent(None)
        widget.deleteLater()
        del widget

    def getEditDialog(self):
        if self.fWidget is None:
            return None

        return self.fWidget.fEditDialog

    def getPluginId(self):
        return self.fPluginId

    def getWidget(self):
        return self.fWidget

    def isCompacted(self):
        return self.fOptions['compact']

    def isGuiShown(self):
        if self.fWidget is None or self.fWidget.b_gui is not None:
            return None
        return self.fWidget.b_gui.isChecked()

    # --------------------------------------------------------------------------------------------------------

    def setPluginId(self, pluginId):
        self.fPluginId = pluginId

        if self.fWidget is not None:
            self.fWidget.setPluginId(pluginId)

    def setSelected(self, select):
        if self.fWidget is not None:
            self.fWidget.setSelected(select)

        QListWidgetItem.setSelected(self, select)

    # --------------------------------------------------------------------------------------------------------

    def setCompacted(self, compact):
        self.fOptions['compact'] = compact

    # --------------------------------------------------------------------------------------------------------

    def compact(self):
        if self.fOptions['compact']:
            return
        self.recreateWidget(True)

    def expand(self):
        if not self.fOptions['compact']:
            return
        self.recreateWidget(True)

    def recreateWidget(self, invertCompactOption = False, firstInit = False, newColor = None, newSkin = None):
        if invertCompactOption:
            self.fOptions['compact'] = not self.fOptions['compact']
        if newColor is not None:
            self.fOptions['color'] = newColor
        if newSkin is not None:
            self.fOptions['skin'] = newSkin

        wasGuiShown = None

        if self.fWidget is not None and self.fWidget.b_gui is not None:
            wasGuiShown = self.fWidget.b_gui.isChecked()

        self.close()

        self.fWidget = createPluginSlot(self.fParent, self.host, self.fPluginId, self.fOptions)
        self.fWidget.setFixedHeight(self.fWidget.getFixedHeight())

        if wasGuiShown and self.fWidget.b_gui is not None:
            self.fWidget.b_gui.setChecked(True)

        self.setSizeHint(QSize(self.kMinimumWidth, self.fWidget.getFixedHeight()))

        self.fParent.setItemWidget(self, self.fWidget)

        # Apply rack item color to patchbay canvas node
        try:
            from carla_shared import gCarla
            if hasattr(gCarla, "gui") and getattr(gCarla.gui, "fWithCanvas", False):
                import patchcanvas
                skin_col = getattr(self.fWidget, "fSkinColor", None)
                if skin_col and skin_col not in ((40, 40, 40), (255, 255, 255)):
                    hex_col = f"#{skin_col[0]:02x}{skin_col[1]:02x}{skin_col[2]:02x}"
                else:
                    hex_col = None
                for group in patchcanvas.canvas.group_list:
                    if getattr(group, "plugin_id", -1) == self.fPluginId:
                        for w in getattr(group, "widgets", []):
                            if w is not None:
                                w.setCustomColor(hex_col, notify=False)
                        break
        except Exception:
            pass

        if not firstInit:
            self.host.set_custom_data(self.fPluginId, CUSTOM_DATA_TYPE_PROPERTY,
                                      "CarlaSkinIsCompacted", "true" if self.fOptions['compact'] else "false")

    def recreateWidget2(self, wasCompacted, wasGuiShown):
        self.fOptions['compact'] = wasCompacted

        self.close()

        self.fWidget = createPluginSlot(self.fParent, self.host, self.fPluginId, self.fOptions)
        self.fWidget.setFixedHeight(self.fWidget.getFixedHeight())

        if wasGuiShown and self.fWidget.b_gui is not None:
            self.fWidget.b_gui.setChecked(True)

        self.setSizeHint(QSize(self.kMinimumWidth, self.fWidget.getFixedHeight()))

        self.fParent.setItemWidget(self, self.fWidget)

        self.host.set_custom_data(self.fPluginId, CUSTOM_DATA_TYPE_PROPERTY,
                                  "CarlaSkinIsCompacted", "true" if wasCompacted else "false")

# ------------------------------------------------------------------------------------------------------------
# Rack Widget

class RackListWidget(QListWidget):
    def __init__(self, parent):
        QListWidget.__init__(self, parent)
        self.host = None
        self.fParent = None

        exts = gCarla.utils.get_supported_file_extensions()

        self.fSupportedExtensions = tuple(("." + i) for i in exts)
        self.fLastSelectedItem    = None
        self.fWasLastDragValid    = False

        self.fPixmapL     = QPixmap(":/bitmaps/rack_interior_left.png")
        self.fPixmapR     = QPixmap(":/bitmaps/rack_interior_right.png")
        self.fPixmapWidth = self.fPixmapL.width()

        self.setMinimumWidth(RackListItem.kMinimumWidth)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(False)

        # Smooth scrolling configuration
        scroll_mode = getattr(QAbstractItemView.ScrollMode, "ScrollPerPixel", getattr(QAbstractItemView, "ScrollPerPixel", None))
        if scroll_mode is not None:
            self.setVerticalScrollMode(scroll_mode)

        self._smooth_target_val = None
        self._smooth_timer = QTimer(self)
        self._smooth_timer.setInterval(16)
        self._smooth_timer.timeout.connect(self._on_smooth_scroll_tick)

        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setDropIndicatorShown(True)
        self.setSpacing(4)
        self.viewport().setAcceptDrops(True)

        self._updateStyle()

    # --------------------------------------------------------------------------------------------------------

    def createItem(self, pluginId, useClassicSkin):
        return RackListItem(self, pluginId, useClassicSkin)

    def getPluginCount(self):
        return self.fParent.getPluginCount()

    def setHostAndParent(self, host, parent):
        self.host = host
        self.fParent = parent

    # --------------------------------------------------------------------------------------------------------

    def customClearSelection(self):
        self.setCurrentRow(-1)
        self.clearSelection()
        self.clearFocus()

    def isDragUrlValid(self, filename):
        if not filename:
            return False

        if filename[-1] == '/':
            filename = filename[:-1]

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

    # --------------------------------------------------------------------------------------------------------

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()

        for url in urls:
            if self.isDragUrlValid(url.toLocalFile()):
                self.fWasLastDragValid = True
                event.acceptProposedAction()
                return

        self.fWasLastDragValid = False
        QListWidget.dragEnterEvent(self, event)

    def dragMoveEvent(self, event):
        if not self.fWasLastDragValid:
            QListWidget.dragMoveEvent(self, event)
            return

        event.acceptProposedAction()

        tryItem = self.itemAt(event.pos())

        if tryItem is not None:
            self.setCurrentRow(tryItem.getPluginId())
        else:
            self.setCurrentRow(-1)

    def dragLeaveEvent(self, event):
        if self.fWasLastDragValid:
            self.fWasLastDragValid = False
        QListWidget.dragLeaveEvent(self, event)

    # --------------------------------------------------------------------------------------------------------

    # FIXME: this needs some attention

    # if dropping project file over 1 plugin, load it in rack or patchbay
    # if dropping regular files over 1 plugin, keep replacing plugins

    def dropEvent(self, event):
        event.acceptProposedAction()

        urls = event.mimeData().urls()

        if not urls:
            return

        tryItem = self.itemAt(event.pos())

        if tryItem is not None:
            pluginId = tryItem.getPluginId()
        else:
            pluginId = -1

        for url in urls:
            if pluginId >= 0:
                self.host.replace_plugin(pluginId)
                pluginId += 1

                if pluginId > self.host.get_current_plugin_count():
                    pluginId = -1

            filename = url.toLocalFile()

            if not filename:
                continue

            if filename[-1] == '/':
                filename = filename[:-1]

            if not self.host.load_file(filename):
                CustomMessageBox(self, QMessageBox.Critical, self.tr("Error"),
                                 self.tr("Failed to load file"),
                                 self.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok)
                continue

            if filename.endswith(".carxp") or filename.endswith(".carjp"):
                gCarla.gui.loadCanvasGroupPositionsFromProject(filename)
                gCarla.gui.loadExternalCanvasGroupPositionsIfNeeded(filename)

        if tryItem is not None:
            self.host.replace_plugin(self.host.get_max_plugin_number())
            #tryItem.widget.setActive(True, True, True)

    # --------------------------------------------------------------------------------------------------------

    def mousePressEvent(self, event):
        if self.itemAt(event.pos()) is None and self.currentRow() != -1:
            event.accept()
            self.customClearSelection()
            return

        QListWidget.mousePressEvent(self, event)

    def keyPressEvent(self, event):
        items = self.selectedItems()
        if not items:
            QListWidget.keyPressEvent(self, event)
            return

        item = items[0]
        pluginId = item.getPluginId()

        if event.key() == Qt.Key_Delete:
            pinfo = self.host.get_plugin_info(pluginId) if self.host is not None else {}
            name = pinfo.get("name", self.tr("this plugin")) if isinstance(pinfo, dict) else self.tr("this plugin")
            ask = QMessageBox.question(
                self,
                self.tr("Remove Plugin"),
                self.tr(f"Are you sure you want to remove '{name}'?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ask == QMessageBox.Yes and self.host is not None:
                self.host.remove_plugin(pluginId)
            event.accept()
            return

        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Up:
                gCarla.gui.switchPlugins(pluginId, pluginId - 1)
                event.accept()
                return
            elif event.key() == Qt.Key_Down:
                gCarla.gui.switchPlugins(pluginId, pluginId + 1)
                event.accept()
                return

        QListWidget.keyPressEvent(self, event)

    def wheelEvent(self, event):
        delta = 0
        if hasattr(event, "angleDelta"):
            delta = event.angleDelta().y()
        elif hasattr(event, "delta"):
            delta = event.delta()

        if delta != 0:
            vsb = self.verticalScrollBar()
            if vsb and vsb.maximum() > vsb.minimum():
                curr = vsb.value()
                base_target = self._smooth_target_val if self._smooth_target_val is not None else curr
                # Standard wheel step is 120 units; smooth scroll by ~80px per step
                pixel_step = int((delta / 120.0) * -80)
                new_target = max(vsb.minimum(), min(vsb.maximum(), base_target + pixel_step))
                self._smooth_target_val = new_target
                if not self._smooth_timer.isActive():
                    self._smooth_timer.start()
                event.accept()
                return

        QListWidget.wheelEvent(self, event)

    def _on_smooth_scroll_tick(self):
        vsb = self.verticalScrollBar()
        if not vsb or self._smooth_target_val is None:
            self._smooth_timer.stop()
            self._smooth_target_val = None
            return

        curr = vsb.value()
        diff = self._smooth_target_val - curr

        if abs(diff) <= 1:
            vsb.setValue(self._smooth_target_val)
            self._smooth_timer.stop()
            self._smooth_target_val = None
        else:
            # Ease out smoothly by interpolating 28% of remaining distance per tick
            step = int(diff * 0.28)
            if step == 0:
                step = 1 if diff > 0 else -1
            vsb.setValue(curr + step)

    def scrollToItemSmooth(self, item):
        if item is None:
            return
        rect = self.visualItemRect(item)
        vsb = self.verticalScrollBar()
        if not vsb or vsb.maximum() <= vsb.minimum():
            return

        curr = vsb.value()
        viewport_h = self.viewport().height()

        # If already completely visible inside the viewport, no scroll needed
        if rect.top() >= 0 and rect.bottom() <= viewport_h:
            return

        # Target centering the rack item smoothly in the visible viewport
        target = curr + rect.top() - int((viewport_h - rect.height()) / 2)
        new_target = max(vsb.minimum(), min(vsb.maximum(), target))

        self._smooth_target_val = new_target
        if not self._smooth_timer.isActive():
            self._smooth_timer.start()

    def changeEvent(self, event):
        if event.type() in (QEvent.StyleChange, QEvent.PaletteChange):
            self._updateStyle()
        QListWidget.changeEvent(self, event)

    def paintEvent(self, event):
        painter = QPainter(self.viewport())

        width = self.width()
        height = self.height()
        
        settings = QSafeSettings("falkTX", "Carla2")
        theme_name = settings.value(CARLA_KEY_CANVAS_THEME, CARLA_DEFAULT_CANVAS_THEME, str)
        theme = Theme(theme_name)
        
        bg_col = theme.canvas_bg if hasattr(theme, 'canvas_bg') else QColor("#222222")

        painter.fillRect(0, 0, width, height, bg_col)
        
        if hasattr(theme, 'box_bg_1'):
            painter.setPen(theme.box_bg_1)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.fPixmapWidth, 0, width-self.fPixmapWidth*2, height)

        QListWidget.paintEvent(self, event)

    def selectionChanged(self, selected, deselected):
        for index in deselected.indexes():
            item = self.itemFromIndex(index)
            if item is not None:
                item.setSelected(False)

        for index in selected.indexes():
            item = self.itemFromIndex(index)
            if item is not None:
                item.setSelected(True)

        QListWidget.selectionChanged(self, selected, deselected)

    # --------------------------------------------------------------------------------------------------------

    def _updateStyle(self):
        pass

# ------------------------------------------------------------------------------------------------------------
