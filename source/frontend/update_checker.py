# -*- coding: utf-8 -*-

# Clara Update Checker & Notification Banner
# Non-blocking background updater querying structured releases.json

import json
import urllib.request
from qt_compat import (
    QThread, pyqtSignal, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QDialog, QTextEdit,
    QSettings, QDesktopServices, QUrl
)
from carla_shared import CLARA_VERSION_STRING as VERSION, CARLA_VERSION_STRING

GITHUB_RELEASES_URL = "https://raw.githubusercontent.com/acropolis914/Clara/main/releases.json"
GITHUB_API_LATEST = "https://api.github.com/repos/acropolis914/Clara/releases/latest"

def parse_semver(ver_str):
    """Normalize version string into comparable tuple of ints."""
    clean = ver_str.strip().lstrip("v").split("-")[0]
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)

class UpdateCheckThread(QThread):
    update_available = pyqtSignal(dict)  # emits release dict
    no_update_found = pyqtSignal(str)    # emits current version
    check_failed = pyqtSignal(str)       # emits error message

    def __init__(self, parent=None, is_manual=False):
        super().__init__(parent)
        self.is_manual = is_manual

    def run(self):
        try:
            req = urllib.request.Request(
                GITHUB_RELEASES_URL,
                headers={"User-Agent": f"Clara/{VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    latest_ver = data.get("latest", "")
                    if not latest_ver:
                        if self.is_manual:
                            self.check_failed.emit("Invalid release response received.")
                        return

                    # Check against skipped version in settings (only for background check)
                    if not self.is_manual:
                        settings = QSettings("falkTX", "Carla2")
                        skipped = settings.value("Clara/SkippedUpdateVersion", "")
                        if skipped == latest_ver:
                            return

                    if parse_semver(latest_ver) > parse_semver(VERSION):
                        # Verify that the GitHub release and its built assets actually exist
                        has_built_assets = False
                        try:
                            api_req = urllib.request.Request(
                                GITHUB_API_LATEST,
                                headers={"User-Agent": f"Clara/{VERSION}", "Accept": "application/vnd.github.v3+json"}
                            )
                            with urllib.request.urlopen(api_req, timeout=5) as api_resp:
                                if api_resp.status == 200:
                                    rel_data = json.loads(api_resp.read().decode("utf-8"))
                                    rel_tag = rel_data.get("tag_name", "").lstrip("v")
                                    assets = rel_data.get("assets", [])
                                    # Filter for compiled package assets (.deb, .rpm, .tar.zst)
                                    pkg_assets = [
                                        a for a in assets
                                        if any(a.get("name", "").endswith(ext) for ext in (".deb", ".rpm", ".tar.zst"))
                                    ]
                                    # If the latest release matches and has compiled distro binaries uploaded
                                    if parse_semver(rel_tag) >= parse_semver(latest_ver) and len(pkg_assets) >= 3:
                                        has_built_assets = True
                        except Exception:
                            # If GitHub API fails or is rate-limited, fall through to release info
                            has_built_assets = True


                        if has_built_assets:
                            rel_info = data.get("releases", {}).get(latest_ver, {})
                            rel_info["version"] = latest_ver
                            self.update_available.emit(rel_info)
                        else:
                            # Update was tagged but packaging workflow is still compiling/uploading
                            if self.is_manual:
                                self.check_failed.emit(f"Clara v{latest_ver} is currently being built and packaged on GitHub. Please check back in a few minutes!")
                    else:
                        if self.is_manual:
                            self.no_update_found.emit(VERSION)
                else:
                    if self.is_manual:
                        self.check_failed.emit(f"Server returned status {resp.status}")
        except Exception as e:
            if self.is_manual:
                self.check_failed.emit(str(e))


class UpdateChangelogDialog(QDialog):
    """Changelog & Installation guide viewer dialog."""
    def __init__(self, release_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Clara v{release_info.get('version')} Update Details")
        self.resize(550, 400)
        layout = QVBoxLayout(self)

        title = QLabel(f"<h2>Clara v{release_info.get('version')}</h2>")
        summary = QLabel(f"<b>{release_info.get('summary', '')}</b>")
        summary.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(summary)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        content = "<h3>✨ What's Changed</h3><ul>"
        for change in release_info.get("changes", []):
            content += f"<li>{change}</li>"
        content += "</ul>"

        inst = release_info.get("installation", {})
        if inst:
            content += "<h3>📦 Installation Guide</h3><ul>"
            for distro, cmd in inst.items():
                content += f"<li><b>{distro.title()}</b>: <code>{cmd}</code></li>"
            content += "</ul>"

        text_edit.setHtml(content)
        layout.addWidget(text_edit)

        btn_row = QHBoxLayout()
        download_btn = QPushButton("⬇ Download Packages")
        download_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B; font-weight: bold; padding: 4px 12px;")
        download_btn.clicked.connect(self.open_download_page)
        btn_row.addWidget(download_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def open_download_page(self):
        url = self.release_info.get("url") or f"https://github.com/acropolis914/Clara/releases/tag/v{self.release_info.get('version', '')}"
        QDesktopServices.openUrl(QUrl(url))

class UpdateNotificationBanner(QFrame):
    """Sleek top banner displayed when an update is available."""
    def __init__(self, release_info, parent=None):
        super().__init__(parent)
        self.release_info = release_info
        self.version = release_info.get("version", "")
        self.urgency = release_info.get("urgency", "minor").lower()

        # Urgency color palette
        badge_colors = {
            "critical": ("#F38BA8", "#1E1E2E"),  # Catppuccin Red badge
            "suggested": ("#89B4FA", "#1E1E2E"), # Catppuccin Blue badge
            "minor": ("#A6ADC8", "#1E1E2E")      # Catppuccin Subtext badge
        }
        badge_bg, badge_fg = badge_colors.get(self.urgency, badge_colors["minor"])

        self.setStyleSheet(f"""
            QFrame#UpdateNotificationBanner {{
                background-color: #181825;
                border-bottom: 2px solid {badge_bg};
                padding: 4px 10px;
            }}
            QLabel {{
                color: #CDD6F4;
                font-size: 12px;
            }}
            QPushButton {{
                background-color: #313244;
                color: #CDD6F4;
                border: 1px solid #45475A;
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #45475A;
            }}
            QPushButton#DownloadBtn {{
                background-color: #A6E3A1;
                color: #11111B;
                font-weight: bold;
                border: none;
            }}
            QPushButton#DownloadBtn:hover {{
                background-color: #94E2D5;
            }}
            QPushButton#ChangelogBtn {{
                background-color: #89B4FA;
                color: #11111B;
                font-weight: bold;
            }}
        """)
        self.setObjectName("UpdateNotificationBanner")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Urgency badge
        badge = QLabel(f" {self.urgency.upper()} ")
        badge.setStyleSheet(f"background-color: {badge_bg}; color: {badge_fg}; font-weight: bold; border-radius: 3px; padding: 2px 4px;")
        layout.addWidget(badge)

        msg = QLabel(f"A new version of <b>Clara (v{self.version})</b> is available!")
        layout.addWidget(msg)

        layout.addStretch()

        # Buttons
        download_btn = QPushButton("⬇ Download Now")
        download_btn.setObjectName("DownloadBtn")
        download_btn.setToolTip("Open GitHub Releases page to download packages")
        download_btn.clicked.connect(self.open_download_page)
        layout.addWidget(download_btn)

        changelog_btn = QPushButton("View Notes")
        changelog_btn.setObjectName("ChangelogBtn")
        changelog_btn.clicked.connect(self.show_changelog)
        layout.addWidget(changelog_btn)

        hide_btn = QPushButton("Hide")
        hide_btn.setToolTip("Dismiss banner for this session")
        hide_btn.clicked.connect(self.hide_banner)
        layout.addWidget(hide_btn)

        skip_btn = QPushButton("Skip Version")
        skip_btn.setToolTip("Do not prompt again for this version")
        skip_btn.clicked.connect(self.confirm_skip)
        layout.addWidget(skip_btn)

    def open_download_page(self):
        url = self.release_info.get("url") or f"https://github.com/acropolis914/Clara/releases/tag/v{self.version}"
        QDesktopServices.openUrl(QUrl(url))

    def show_changelog(self):
        dlg = UpdateChangelogDialog(self.release_info, self)
        dlg.exec_()

    def hide_banner(self):
        self.setVisible(False)

    def confirm_skip(self):
        reply = QMessageBox.question(
            self,
            "Skip Version",
            f"Are you sure you want to skip Clara v{self.version}?\nYou won't be notified about this update again.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            settings = QSettings("falkTX", "Carla2")
            settings.setValue("Clara/SkippedUpdateVersion", self.version)
            self.setVisible(False)
