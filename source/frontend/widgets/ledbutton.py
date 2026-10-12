#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ---------------------------------------------------------------------------------------------------------------------
# Imports (Global)

from qt_compat import (
    QRectF,
    QPainter,
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

        self._loadImageNowIfNeeded()

        target_rect = QRectF(self.rect())
        if isinstance(self.fImage, QPixmap):
            painter.drawPixmap(target_rect.toRect(), self.fImage)
        else:
            self.fImage.renderer().render(painter, target_rect)

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
