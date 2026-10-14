#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara Contributors
# SPDX-License-Identifier: GPL-2.0-or-later

"""Ground-up floating minimap for the Clara patchbay."""


from qt_compat import (
    Qt,
    QEvent,
    QObject,
    QRectF,
    QPoint,
    QPointF,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QPixmap,
    QFrame,
    QSizePolicy,
    pyqtSignal,
)

from patchcanvas import patchcanvas


class _ViewportEventFilter(QObject):
    def __init__(self, minimap):
        super().__init__(minimap)
        self.minimap = minimap

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Resize, QEvent.Move, QEvent.Show, QEvent.Hide):
            self.minimap.update()
        return False


class CanvasMinimapFrame(QFrame):
    miniCanvasMoved = pyqtSignal(float, float)

    def __init__(self, parent, graphics_view, scene, host=None, width=250, height=170):
        super().__init__(parent)
        self.graphics_view = graphics_view
        self.fScene = scene
        self.host = host
        self._width = width
        self._height = height
        self._grabbed = False
        self._event_filter = _ViewportEventFilter(self)
        if graphics_view is not None:
            try:
                graphics_view.viewport().installEventFilter(self._event_filter)
            except Exception:
                pass

        self.fViewBg = QColor(0, 0, 0)
        self.fViewBrush = QBrush(QColor(75, 75, 255, 30))
        self.fViewPen = QPen(Qt.blue, 1.0)

        self._cache = None
        self._cache_bounds = None
        self._cache_size = None

        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)
        self.setFixedSize(width, height)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFrameShape(QFrame.StyledPanel)

        try:
            if scene is not None and hasattr(scene, "changed"):
                scene.changed.connect(lambda *args: self.update())
        except Exception:
            pass

        for signal_name in ("horizontalScrollBar", "verticalScrollBar"):
            try:
                attr = getattr(graphics_view, signal_name)
                bar = attr()
                bar.valueChanged.connect(lambda *args: self.update())
            except Exception:
                pass

        try:
            if hasattr(graphics_view, "transformed"):
                graphics_view.transformed.connect(lambda *args: self.update())
        except Exception:
            pass
        try:
            if hasattr(scene, "scaleChanged"):
                scene.scaleChanged.connect(lambda *args: self.update())
        except Exception:
            pass

    # ---------------------------------------------------------------- API

    def setRealParent(self, parent):
        # compatibility no-op
        pass

    def setViewTheme(self, bg_color, brush_color, pen_color):
        try:
            self.fViewBg = QColor(bg_color)
            self.fViewBrush = QBrush(QColor(brush_color))
            pen = QPen(QColor(pen_color))
            pen.setWidthF(1.0)
            self.fViewPen = pen
        except Exception:
            pass
        self.update()

    def init(self, scene, real_width=0.0, real_height=0.0, use_custom_paint=False):
        self.fScene = scene
        self._scene_cache_invalidate()
        self.update()

    def _scene_cache_invalidate(self):
        self._cache = None
        self._cache_bounds = None
        self._cache_size = None

    def setViewPosX(self, xp):
        pass

    def setViewPosY(self, yp):
        pass

    def setViewScale(self, scale):
        pass

    def setViewSize(self, width, height):
        pass

    # ---------------------------------------------------------------- scene

    def _scene_bounds(self):
        try:
            bounds = self.fScene.sceneRect()
        except Exception:
            bounds = QRectF()
        if bounds is None or bounds.isNull() or bounds.width() <= 0 or bounds.height() <= 0:
            bounds = QRectF()
        try:
            for item in list(self.fScene.items()):
                if hasattr(item, "m_group_id"):
                    r = item.sceneBoundingRect()
                    if bounds.isNull():
                        bounds = QRectF(r)
                    else:
                        bounds = bounds.united(r)
        except Exception:
            pass
        if bounds.isNull() or bounds.width() <= 0 or bounds.height() <= 0:
            bounds = QRectF(0.0, 0.0, 1000.0, 1000.0)
        try:
            bounds.adjust(-48.0, -48.0, 48.0, 48.0)
        except Exception:
            pass
        return bounds

    def _fit(self, bounds):
        bw = max(1.0, bounds.width())
        bh = max(1.0, bounds.height())
        w = max(1.0, float(self.width()))
        h = max(1.0, float(self.height()))
        scale = min(w / bw, h / bh)
        ox = (w - bw * scale) * 0.5
        oy = (h - bh * scale) * 0.5
        return scale, ox, oy

    def _ensure_cache(self):
        bounds = self._scene_bounds()
        size = (self.width(), self.height())
        if (self._cache is not None and self._cache_bounds == bounds and
                self._cache_size == size):
            return bounds, self._fit(bounds)
        pix = QPixmap(self.width(), self.height())
        pix.fill(self.fViewBg if self.fViewBg is not None else QColor(24, 24, 37))
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, False)
        scale, ox, oy = self._fit(bounds)
        bw = bounds.width()
        bh = bounds.height()
        try:
            bg_color = self.fViewBg if self.fViewBg is not None else QColor(30, 30, 46)
            painter.fillRect(0, 0, self.width(), self.height(), bg_color)
        except Exception:
            pass
        try:
            for item in list(self.fScene.items()):
                if not hasattr(item, "m_group_id"):
                    continue
                r = item.sceneBoundingRect()
                x = ox + (r.left() - bounds.left()) * scale
                y = oy + (r.top() - bounds.top()) * scale
                rw = max(1.0, r.width() * scale)
                rh = max(1.0, r.height() * scale)
                color = None
                try:
                    color = item.getCustomColor()
                except Exception:
                    color = None
                if not color:
                    try:
                        color = patchcanvas.canvas.theme.box_bg_1
                    except Exception:
                        color = QColor(60, 60, 75)
                painter.setBrush(QBrush(QColor(color)))
                pen = QPen(QColor(color).darker(135))
                pen.setWidthF(1.0)
                painter.setPen(pen)
                painter.drawRect(int(x), int(y), int(rw), int(rh))
        except Exception:
            pass
        painter.end()
        self._cache = pix
        self._cache_bounds = bounds
        self._cache_size = size
        return bounds, (scale, ox, oy)

    def _viewport_scene_rect(self):
        try:
            return self.graphics_view.mapToScene(self.graphics_view.viewport().rect()).boundingRect()
        except Exception:
            return QRectF()

    # ---------------------------------------------------------------- paint

    def paintEvent(self, event):
        if self.fScene is None:
            super().paintEvent(event)
            return
        try:
            bounds, fit = self._ensure_cache()
        except Exception:
            super().paintEvent(event)
            return
        scale, ox, oy = fit
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, bool(self.width() > 0))
        if self._cache is not None:
            painter.drawPixmap(0, 0, self._cache)
        try:
            vp = self._viewport_scene_rect()
            x = ox + (vp.left() - bounds.left()) * scale
            y = oy + (vp.top() - bounds.top()) * scale
            w = max(1.0, vp.width() * scale)
            h = max(1.0, vp.height() * scale)
            painter.setBrush(self.fViewBrush)
            painter.setPen(Qt.NoPen)
            painter.drawRect(int(x), int(y), int(w), int(h))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(self.fViewPen)
            painter.drawRect(int(x), int(y), max(1, int(w)), max(1, int(h)))
        except Exception:
            pass
        painter.end()

    # ---------------------------------------------------------------- mouse

    def _map_to_scene(self, pos):
        bounds, fit = self._ensure_cache()
        scale, ox, oy = fit
        sx = bounds.left() + (pos.x() - ox) / max(0.0001, scale)
        sy = bounds.top() + (pos.y() - oy) / max(0.0001, scale)
        return sx, sy, bounds

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._grabbed = True
            self._pan_to(event.pos())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._grabbed:
            self._pan_to(event.pos())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._grabbed = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _pan_to(self, pos):
        try:
            sx, sy, bounds = self._map_to_scene(pos)
            self.graphics_view.centerOn(sx, sy)
            if bounds.width() > 0 and bounds.height() > 0:
                xp = (sx - bounds.left()) / bounds.width()
                yp = (sy - bounds.top()) / bounds.height()
                self.miniCanvasMoved.emit(float(xp), float(yp))
        except Exception:
            pass
