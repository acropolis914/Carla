"""Data-driven QSS Theme Manager for Clara.

Dynamically scans theme directories (.qss files), loads user custom themes,
and applies styles live to QApplication without requiring application restart.
Canvasbox theming is handled independently via patchcanvas/themes.json.
"""

import os
import glob
from qt_compat import QApplication

CARLA_KEY_MAIN_USE_SYSTEM_THEME = "Main/UseSystemTheme"
CARLA_DEFAULT_MAIN_USE_SYSTEM_THEME = False

CARLA_KEY_MAIN_APP_THEME = "Main/AppTheme"
CARLA_DEFAULT_MAIN_APP_THEME = "Catppuccin Mocha"


class ThemeManager:
    _instance = None

    def __init__(self):
        # Base bundled themes directory
        self.bundled_themes_dir = os.path.join(os.path.dirname(__file__), "themes")
        # User customized themes directory (~/.config/clara/themes or ~/.config/carla/themes)
        self.user_themes_dir = os.path.expanduser("~/.config/clara/themes")
        self._current_theme = None
        self._using_system = False

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    def get_available_themes(self) -> list[str]:
        """Return a sorted list of unique available theme names discovered from disk."""
        themes = set()

        for search_dir in (self.bundled_themes_dir, self.user_themes_dir):
            if os.path.isdir(search_dir):
                for qss_path in glob.glob(os.path.join(search_dir, "*.qss")):
                    base = os.path.splitext(os.path.basename(qss_path))[0]
                    # Convert filename like 'catppuccin_mocha' to 'Catppuccin Mocha'
                    title = " ".join(word.capitalize() for word in base.replace("-", "_").split("_"))
                    themes.add(title)

        if not themes:
            themes.add("Catppuccin Mocha")

        # Sort with Catppuccin Mocha first, then alphabetical
        sorted_themes = sorted(list(themes))
        if "Catppuccin Mocha" in sorted_themes:
            sorted_themes.remove("Catppuccin Mocha")
            sorted_themes.insert(0, "Catppuccin Mocha")
        return sorted_themes

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

    def apply_theme(self, theme_name: str = CARLA_DEFAULT_MAIN_APP_THEME, use_system: bool = False):
        """Apply the specified theme or revert to native system styling live."""
        app = QApplication.instance()
        if not app:
            return

        self._using_system = use_system
        self._current_theme = theme_name

        if use_system:
            # Revert to system styling: clear injected QSS stylesheet
            app.setStyleSheet("")
            return

        # Ensure a clean consistent baseline Qt widget layout
        app.setStyle("Fusion")

        qss_file = self._resolve_theme_file(theme_name)
        if not qss_file and theme_name != CARLA_DEFAULT_MAIN_APP_THEME:
            # Fallback to default bundled theme
            qss_file = self._resolve_theme_file(CARLA_DEFAULT_MAIN_APP_THEME)

        if qss_file and os.path.isfile(qss_file):
            try:
                with open(qss_file, "r", encoding="utf-8") as f:
                    qss_content = f.read()
                app.setStyleSheet(qss_content)
            except Exception as e:
                print(f"[THEME] Failed to load stylesheet {qss_file}: {e}")
                app.setStyleSheet("")
        else:
            app.setStyleSheet("")


theme_manager = ThemeManager.instance()
