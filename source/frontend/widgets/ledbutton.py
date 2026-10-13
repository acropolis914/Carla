#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ---------------------------------------------------------------------------------------------------------------------
# Imports (Global)

from qt_compat import (
    QRectF,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
    QPixmap,
    QSvgWidget,
    QPushButton,
)

# ---------------------------------------------------------------------------------------------------------------------
# Widget Class

class LEDButton(QPushButton):
    # unset
    UNSET  = -1
    # normal
    OFF    = 0
    BLUE   = 1
    GREEN  = 2
    RED    = 3
    YELLOW = 4
    # extra
    CALF   = 5

    def __init__(self, parent):
        QPushButton.__init__(self, parent)

        self.fLastColor = self.UNSET
        self.fColor     = self.UNSET

        self.fImage = QSvgWidget()
        self.fImage.load(":/scalable/led_off.svg")
        self.fRect = QRectF(self.fImage.rect())

        self.setCheckable(True)
        self.setText("")

        self.setColor(self.BLUE)

        self.fCustomSize = False
        self.fMinimalMode = False

    def setMinimalMode(self, enabled):
        self.fMinimalMode = bool(enabled)
        self.update()

    def setFixedSize(self, *args):
        self.fCustomSize = True
        super().setFixedSize(*args)

    def setColor(self, color):
        self.fColor = color

        if color == self.CALF:
            self.fLastColor = self.UNSET

        if self._loadImageNowIfNeeded():
            self.fRect = QRectF(self.fImage.rect())
            if not getattr(self, 'fCustomSize', False):
                super().setFixedSize(self.fImage.size())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        event.accept()

        if getattr(self, 'fMinimalMode', False):
            self._paintMinimalLed(painter)
            return

        self._loadImageNowIfNeeded()

        target_rect = QRectF(self.rect())
        if isinstance(self.fImage, QPixmap):
            painter.drawPixmap(target_rect.toRect(), self.fImage)
        else:
            self.fImage.renderer().render(painter, target_rect)

    def _paintMinimalLed(self, painter):
        w = float(self.width())
        h = float(self.height())
        size = min(w, h)
        if size <= 1.0:
            return

        cx = w / 2.0
        cy = h / 2.0
        r = (size - 2.0) / 2.0

        is_on = self.isChecked()

        # Resolve theme colors for signal types
        # Control (Yellow), MIDI (Red/Coral), Audio In (Green), Audio Out (Cyan/Blue)
        color_map = {
            self.YELLOW: (QColor(249, 226, 175), QColor(250, 204, 21, 60)),   # Amber / Gold
            self.RED:    (QColor(243, 139, 168), QColor(248, 113, 113, 60)),  # Coral / Red
            self.GREEN:  (QColor(166, 227, 161), QColor(74, 222, 128, 60)),   # Emerald / Green
            self.BLUE:   (QColor(137, 220, 235), QColor(56, 189, 248, 60)),   # Sky / Cyan
            self.CALF:   (QColor(166, 227, 161), QColor(74, 222, 128, 60)),
        }
        solid_col, glow_col = color_map.get(self.fColor, (QColor(137, 220, 235), QColor(56, 189, 248, 60)))

        if is_on:
            # Outer diffuse glow
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow_col)
            painter.drawEllipse(QRectF(cx - r - 1.0, cy - r - 1.0, (r + 1.0) * 2.0, (r + 1.0) * 2.0))

            # Vivid solid active core
            painter.setBrush(solid_col)
            painter.setPen(QPen(QColor(255, 255, 255, 180), 0.75))
            painter.drawEllipse(QRectF(cx - r, cy - r, r * 2.0, r * 2.0))

            # Centered light specular highlight
            spec_r = max(0.8, r * 0.4)
            painter.setBrush(QColor(255, 255, 255, 230))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(cx - spec_r * 0.6, cy - spec_r * 0.6, spec_r, spec_r))
        else:
            # Clean dark inactive state: recessed dot with subtle bezel
            bg_col = QColor(255, 255, 255, 14)
            border_col = QColor(255, 255, 255, 38)
            painter.setBrush(bg_col)
            painter.setPen(QPen(border_col, 0.75))
            painter.drawEllipse(QRectF(cx - r, cy - r, r * 2.0, r * 2.0))

            # Subtle inner core tint representing dark dormant diode
            dormant_col = QColor(solid_col.red(), solid_col.green(), solid_col.blue(), 25)
            painter.setPen(Qt.NoPen)
            painter.setBrush(dormant_col)
            inner_r = r * 0.55
            painter.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2.0, inner_r * 2.0))

    def _loadImageNowIfNeeded(self):
        if self.isChecked():
            if self.fLastColor == self.fColor:
                return False
            if self.fColor == self.OFF:
                img = ":/scalable/led_off.svg"
            elif self.fColor == self.BLUE:
                img = ":/scalable/led_blue.svg"
            elif self.fColor == self.GREEN:
                img = ":/scalable/led_green.svg"
            elif self.fColor == self.RED:
                img = ":/scalable/led_red.svg"
            elif self.fColor == self.YELLOW:
                img = ":/scalable/led_yellow.svg"
            elif self.fColor == self.CALF:
                img = ":/bitmaps/led_calf_on.png"
            else:
                return False
            self.fLastColor = self.fColor

        elif self.fLastColor != self.OFF:
            img = ":/bitmaps/led_calf_off.png" if self.fColor == self.CALF else ":/scalable/led_off.svg"
            self.fLastColor = self.OFF

        else:
            return False

        if img.endswith(".png"):
            if not isinstance(self.fImage, QPixmap):
                self.fImage = QPixmap()
        else:
            if not isinstance(self.fImage, QSvgWidget):
                self.fImage = QSvgWidget()

        self.fImage.load(img)
        self.update()

        return True

# ---------------------------------------------------------------------------------------------------------------------
