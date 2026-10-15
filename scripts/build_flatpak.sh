#!/usr/bin/env bash
# ---------------------------------------------------------------------------------------------------------------------
# Clara - Flatpak builder
#
# Builds a Flatpak bundle into dist/ using flatpak-builder against the KDE
# runtime (org.kde.Platform//6.8), then exports a single-file .flatpak.
#
# The app tree (native libs + Python frontend) is built inside the sandbox by
# the manifest's "clara" module; PyQt6 is pulled in by the "python3-pyqt6"
# module. Qt6 comes from the KDE runtime.
#
# Prerequisites:
#   sudo pacman -S flatpak flatpak-builder ostree
#   flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
#   flatpak install flathub org.kde.Platform//6.8 org.kde.Sdk//6.8
# ---------------------------------------------------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

APP_ID="com.github.acropolis914.Clara"
MANIFEST="data/flatpak/${APP_ID}.json"
BUILD_DIR="${BUILD_DIR:-$REPO_ROOT/build/flatpak}"
REPO_DIR="${REPO_DIR:-$REPO_ROOT/build/flatpak-repo}"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/dist}"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

command -v flatpak-builder >/dev/null 2>&1 || die "flatpak-builder not found (sudo pacman -S flatpak-builder)"
[ -f "$MANIFEST" ] || die "manifest not found: $MANIFEST"

VERSION="$(sed -n 's/^CLARA_VERSION_STRING[[:space:]]*=[[:space:]]*"\(.*\)"/\1/p' source/frontend/carla_shared.py | head -n1)"
[ -n "$VERSION" ] || VERSION="0.0.0"

mkdir -p "$OUTPUT_DIR"

log "Building Flatpak ${APP_ID} ${VERSION}"
flatpak-builder --force-clean --repo="$REPO_DIR" "$BUILD_DIR" "$MANIFEST"

OUTPUT="$OUTPUT_DIR/Clara-${VERSION}-x86_64.flatpak"
log "Exporting single-file bundle: $OUTPUT"
flatpak build-bundle "$REPO_DIR" "$OUTPUT" "$APP_ID"

log "Done: $OUTPUT"
log "Install with: flatpak install --user $OUTPUT"
