#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Backward Compatibility Alias
#
# Drag previews are now a single registry-driven class (CanvasLineMov) that renders
# whichever line algorithm is active. This module is kept so existing imports keep working.

from .canvaslinemov import CanvasLineMov

CanvasBezierLineMov = CanvasLineMov

__all__ = ["CanvasLineMov", "CanvasBezierLineMov"]

# ------------------------------------------------------------------------------------------------------------
