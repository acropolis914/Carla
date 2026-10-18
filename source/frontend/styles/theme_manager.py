"""Data-driven QSS Theme Manager for Clara.

Dynamically scans theme directories (.qss files), loads user custom themes,
and applies styles live to QApplication without requiring application restart.
Canvasbox theming is handled independently via patchcanvas/themes.json.
"""

import math
import os
import glob

# Global minimal scrollbar QSS applied to all themes
MINIMAL_SCROLLBAR_QSS = """QScrollBar:vertical {
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    /* inherits theme colors */
}
QScrollBar:horizontal {
    border: none;
    background-color: transparent;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    min-width: 24px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    /* inherits theme colors */
}
"""
from qt_compat import QApplication, QColor, QPalette

CARLA_KEY_MAIN_USE_SYSTEM_THEME = "Main/UseSystemTheme"
CARLA_DEFAULT_MAIN_USE_SYSTEM_THEME = False

CARLA_KEY_MAIN_APP_THEME = "Main/AppTheme"
CARLA_DEFAULT_MAIN_APP_THEME = "Catppuccin Macchiato"


def find_closest_system_color(color, palette=None, threshold=0.75) -> QColor:
    """
    Find the closest color in the active system palette to `color`.
    Evaluates perceptual likeliness: (1.0 - delta_c / max_distance).
    If likeliness >= threshold (default 0.75 / 75%), return the closest system color.
    Otherwise, adjust the color towards the system theme tone by blending 25% of the
    closest system color into the target color, preserving its role while harmonizing
    with the platform theme.
    """
    if isinstance(color, str):
        c = color.strip()
        if not c.startswith("#") and not c.startswith("rgb"):
            c = "#" + c
        qcol = QColor(c)
    elif isinstance(color, QColor):
        qcol = color
    elif isinstance(color, (list, tuple)) and len(color) >= 3:
        qcol = QColor(int(color[0]), int(color[1]), int(color[2]))
    else:
        qcol = QColor(color)

    if not qcol.isValid():
        qcol = QColor(0, 0, 0)

    tr, tg, tb = qcol.red(), qcol.green(), qcol.blue()

    if palette is None:
        app = QApplication.instance()
        palette = app.palette() if app else QPalette()

    roles = (
        QPalette.Window,
        QPalette.WindowText,
        QPalette.Base,
        QPalette.AlternateBase,
        QPalette.Text,
        QPalette.Button,
        QPalette.ButtonText,
        QPalette.Highlight,
        QPalette.HighlightedText,
        QPalette.Mid,
        QPalette.Dark,
        QPalette.Light,
    )

    best_sys_col = None
    best_likeliness = -1.0

    for role in roles:
        sys_col = palette.color(role)
        sr, sg, sb = sys_col.red(), sys_col.green(), sys_col.blue()
        # Perceptual Euclidean distance with eye sensitivity weights
        dr = tr - sr
        dg = tg - sg
        db = tb - sb
        dist = math.sqrt(0.299 * (dr ** 2) + 0.587 * (dg ** 2) + 0.114 * (db ** 2))
        likeliness = 1.0 - (dist / 255.0)

        if likeliness > best_likeliness:
            best_likeliness = likeliness
            best_sys_col = sys_col

    if best_sys_col is None:
        return qcol

    if best_likeliness >= threshold:
        return best_sys_col

    # Else adjust it a bit: blend 25% of closest system color and calibrate brightness
    sys_win = palette.color(QPalette.Window)
    is_sys_dark = (0.299 * sys_win.red() + 0.587 * sys_win.green() + 0.114 * sys_win.blue()) < 128

    sr, sg, sb = best_sys_col.red(), best_sys_col.green(), best_sys_col.blue()
    blend_r = int(round(tr * 0.75 + sr * 0.25))
    blend_g = int(round(tg * 0.75 + sg * 0.25))
    blend_b = int(round(tb * 0.75 + sb * 0.25))

    cur_lum = 0.299 * blend_r + 0.587 * blend_g + 0.114 * blend_b
    if not is_sys_dark and cur_lum > 180:
        factor = 0.35
        blend_r = int(blend_r * factor)
        blend_g = int(blend_g * factor)
        blend_b = int(blend_b * factor)
    elif is_sys_dark and cur_lum < 40:
        factor = 1.4
        blend_r = min(255, int(blend_r * factor))
        blend_g = min(255, int(blend_g * factor))
        blend_b = min(255, int(blend_b * factor))

    return QColor(blend_r, blend_g, blend_b)


class ThemeManager:
    _instance = None

    def __init__(self):
        # Base bundled themes directory
        self.bundled_themes_dir = os.path.join(os.path.dirname(__file__), "themes")
        # User customized themes directory (~/.config/clara/themes or ~/.config/carla/themes)
        self.user_themes_dir = os.path.expanduser("~/.config/clara/themes")
        self._current_theme = None
        self._using_system = False
        self._original_style = None
        self._available_themes = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    def is_using_system(self) -> bool:
        return self._using_system

    def get_available_themes(self, refresh: bool = False) -> list[str]:
        """Return a sorted list of unique available theme names discovered from disk."""
        if not refresh and self._available_themes is not None:
            return list(self._available_themes)

        themes = set()

        for search_dir in (self.bundled_themes_dir, self.user_themes_dir):
            if os.path.isdir(search_dir):
                for qss_path in glob.glob(os.path.join(search_dir, "*.qss")):
                    base = os.path.splitext(os.path.basename(qss_path))[0]
                    # Convert filename like 'catppuccin_mocha' to 'Catppuccin Mocha'
                    title = " ".join(word.capitalize() for word in base.replace("-", "_").split("_"))
                    themes.add(title)

        if not themes:
            themes.add("Catppuccin Macchiato")

        # Sort with Catppuccin Macchiato first, then alphabetical
        sorted_themes = sorted(list(themes))
        if "Catppuccin Macchiato" in sorted_themes:
            sorted_themes.remove("Catppuccin Macchiato")
            sorted_themes.insert(0, "Catppuccin Macchiato")
        self._available_themes = sorted_themes
        return list(sorted_themes)

    def _resolve_theme_file(self, theme_name: str) -> str | None:
        """Find the .qss file corresponding to a given human-readable theme name."""
        filename = theme_name.lower().replace(" ", "_") + ".qss"

        # Check user directory first (allows overriding bundled themes)
        user_path = os.path.join(self.user_themes_dir, filename)
        if os.path.isfile(user_path):
            return user_path

        # Check bundled directory
        bundled_path = os.path.join(self.bundled_themes_dir, filename)
        if os.path.isfile(bundled_path):
            return bundled_path

        # Case-insensitive fallback
        for search_dir in (self.user_themes_dir, self.bundled_themes_dir):
            if os.path.isdir(search_dir):
                for path in glob.glob(os.path.join(search_dir, "*.qss")):
                    if os.path.splitext(os.path.basename(path))[0].lower() == theme_name.lower().replace(" ", "_"):
                        return path
        return None

    def _notify_theme_changed(self):
        """Live update patchcanvas, canvasbox, rack list, and banners without application restart."""
        # 1. PatchCanvas & CanvasBoxes
        try:
            from patchcanvas import patchcanvas
            if hasattr(patchcanvas, "canvas") and getattr(patchcanvas.canvas, "initiated", False):
                from patchcanvas.theme import Theme
                from utils import QSafeSettings
                from carla_shared import CARLA_KEY_CANVAS_THEME, CARLA_DEFAULT_CANVAS_THEME
                settings = QSafeSettings("falkTX", "Carla2")
                canvas_theme_name = settings.value(CARLA_KEY_CANVAS_THEME, CARLA_DEFAULT_CANVAS_THEME, str)
                patchcanvas.canvas.theme = Theme(canvas_theme_name)
                if hasattr(patchcanvas.canvas, "scene") and patchcanvas.canvas.scene:
                    patchcanvas.canvas.scene.updateTheme()
                if hasattr(patchcanvas.canvas, "group_list"):
                    for group in patchcanvas.canvas.group_list:
                        if hasattr(group, "updateTheme"):
                            group.updateTheme()
                        if hasattr(group, "port_list"):
                            for port in group.port_list:
                                if hasattr(port, "updateTheme"):
                                    port.updateTheme()
                if hasattr(patchcanvas.canvas, "scene") and patchcanvas.canvas.scene:
                    patchcanvas.canvas.scene.update()
        except Exception as e:
            print(f"[THEME] Error live refreshing canvas: {e}")

        # 2. Main GUI, Rack List Widget & Banners
        try:
            from carla_shared import gCarla
            if hasattr(gCarla, "gui") and gCarla.gui is not None:
                if hasattr(gCarla.gui, "_update_split_tab_views"):
                    gCarla.gui._update_split_tab_views()
                if hasattr(gCarla.gui.ui, "listWidget"):
                    gCarla.gui.ui.listWidget.update()
                if hasattr(gCarla.gui, "fUpdateBanner") and gCarla.gui.fUpdateBanner:
                    if hasattr(gCarla.gui.fUpdateBanner, "update_theme_styling"):
                        gCarla.gui.fUpdateBanner.update_theme_styling()
                if hasattr(gCarla.gui, "fSupportBanner") and gCarla.gui.fSupportBanner:
                    if hasattr(gCarla.gui.fSupportBanner, "update_theme_styling"):
                        gCarla.gui.fSupportBanner.update_theme_styling()
        except Exception as e:
            print(f"[THEME] Error live refreshing GUI views: {e}")

    def apply_theme(self, theme_name: str = CARLA_DEFAULT_MAIN_APP_THEME, use_system: bool = False):
        """Apply the specified theme or revert to native system styling live without restart."""
        app = QApplication.instance()
        if not app:
            return

        self._using_system = use_system
        self._current_theme = theme_name

        if self._original_style is None and hasattr(app, "style"):
            curr_style = app.style()
            if curr_style:
                self._original_style = curr_style.objectName()

        if use_system:
            # Revert to system styling then layer theme + minimal scrollbar QSS on top
            app.setStyleSheet("")
            if self._original_style:
                app.setStyle(self._original_style)
            qss_file = self._resolve_theme_file(theme_name)
            if not qss_file and theme_name != CARLA_DEFAULT_MAIN_APP_THEME:
                qss_file = self._resolve_theme_file(CARLA_DEFAULT_MAIN_APP_THEME)
            theme_qss = ""
            if qss_file and os.path.isfile(qss_file):
                try:
                    with open(qss_file, "r", encoding="utf-8") as f:
                        theme_qss = f.read()
                except Exception:
                    theme_qss = ""
            app.setStyleSheet(theme_qss + "\n" + MINIMAL_SCROLLBAR_QSS)
            self._notify_theme_changed()
            return

        # Ensure a clean consistent baseline Qt widget layout
        app.setStyle("Fusion")

        qss_file = self._resolve_theme_file(theme_name)
        if not qss_file and theme_name != CARLA_DEFAULT_MAIN_APP_THEME:
            # Fallback to default bundled theme
            qss_file = self._resolve_theme_file(CARLA_DEFAULT_MAIN_APP_THEME)

        theme_qss = ""
        if qss_file and os.path.isfile(qss_file):
            try:
                with open(qss_file, "r", encoding="utf-8") as f:
                    theme_qss = f.read()
            except Exception as e:
                print(f"[THEME] Failed to load stylesheet {qss_file}: {e}")

        # Always apply minimal scrollbars on top of theme QSS
        app.setStyleSheet(theme_qss + "\n" + MINIMAL_SCROLLBAR_QSS)
        self._notify_theme_changed()


theme_manager = ThemeManager.instance()
