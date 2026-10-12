#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

from qt_compat import QGraphicsDropShadowEffect

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import (
    canvas,
    PORT_TYPE_AUDIO_JACK,
    PORT_TYPE_MIDI_ALSA,
    PORT_TYPE_MIDI_JACK,
    PORT_TYPE_PARAMETER,
)

# ------------------------------------------------------------------------------------------------------------

class CanvasPortGlow(QGraphicsDropShadowEffect):
    def __init__(self, port_type, parent):
        QGraphicsDropShadowEffect.__init__(self, parent)

        self.setBlurRadius(12)
        self.setOffset(0, 0)

        if port_type == PORT_TYPE_AUDIO_JACK:
            self.setColor(canvas.theme.line_audio_jack_glow)
        elif port_type == PORT_TYPE_MIDI_JACK:
            self.setColor(canvas.theme.line_midi_jack_glow)
        elif port_type == PORT_TYPE_MIDI_ALSA:
            self.setColor(canvas.theme.line_midi_alsa_glow)
        elif port_type == PORT_TYPE_PARAMETER:
            self.setColor(canvas.theme.line_parameter_glow)

# ------------------------------------------------------------------------------------------------------------
