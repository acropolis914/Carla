#!/usr/bin/env bash
# ---------------------------------------------------------------------------------------------------------------------
# Clara - portable AppImage builder
#
# Builds a self-contained .AppImage into dist/. The image bundles:
#   * a relocatable CPython (python-build-standalone)
#   * PyQt6 - whose "PyQt6-Qt6" wheel already ships the matching Qt6 libraries
#     and platform plugins, so the AppImage does not depend on the system Qt
#   * the Clara native libs + Python frontend (make install)
#   * remaining non-Qt system libs gathered with linuxdeploy
#
# Only x86_64 is produced for now (see TODO for aarch64 / cross-compilation).
#
# Everything the script needs that is not already installed is downloaded into
# build/appimage-tools. Network access is required on the first run.
# ---------------------------------------------------------------------------------------------------------------------
set -euo pipefail

# Run the AppImage-format build tools without requiring FUSE (fuse2).
export APPIMAGE_EXTRACT_AND_RUN=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------------------------------------------------
# configuration / arguments

ARCH="${ARCH:-x86_64}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
PYTHON_PBS_VERSION="${PYTHON_PBS_VERSION:-3.12.4}"   # full version of the python-build-standalone asset
PYTHON_PBS_TAG="${PYTHON_PBS_TAG:-20240726}"
PYQT6_VERSION="${PYQT6_VERSION:-6.7.1}"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 4)}"
NO_BUILD=0
CLEAN=0

for arg in "$@"; do
    case "$arg" in
        --arch=*)   ARCH="${arg#*=}" ;;
        --no-build) NO_BUILD=1 ;;
        --clean)    CLEAN=1 ;;
        -h|--help)
            printf 'Usage: %s [--arch=x86_64] [--no-build] [--clean]\n' "$0"
            exit 0
        ;;
        *) printf 'Unknown argument: %s\n' "$arg" >&2; exit 2 ;;
    esac
done

if [ "$ARCH" != "x86_64" ]; then
    printf 'ERROR: only --arch=x86_64 is supported for now (aarch64 needs qemu cross-compilation).\n' >&2
    exit 1
fi

VERSION="$(sed -n 's/^VERSION[[:space:]]*:=[[:space:]]*//p' Makefile | head -n1)"
[ -n "$VERSION" ] || VERSION="0.0.0"

OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/dist}"
BUILD_DIR="${BUILD_DIR:-$REPO_ROOT/build/appimage}"
TOOLS_DIR="${TOOLS_DIR:-$REPO_ROOT/build/appimage-tools}"
APPDIR="$BUILD_DIR/Clara.AppDir"
OUTPUT_NAME="Clara-${VERSION}-${ARCH}.AppImage"

mkdir -p "$OUTPUT_DIR" "$TOOLS_DIR"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------------------------------------------------
# tool acquisition

download() {
    local url="$1" dest="$2"
    [ -f "$dest" ] && return 0
    log "Downloading $(basename "$dest")"
    if command -v curl >/dev/null 2>&1; then
        curl -fL --retry 3 -o "$dest.part" "$url" && mv "$dest.part" "$dest"
    elif command -v wget >/dev/null 2>&1; then
        wget -O "$dest.part" "$url" && mv "$dest.part" "$dest"
    else
        die "curl or wget is required to download build tools"
    fi
}

LINUXDEPLOY_BIN=""
APPIMAGETOOL_BIN=""

ensure_linuxdeploy() {
    LINUXDEPLOY_BIN="$TOOLS_DIR/linuxdeploy-${ARCH}.AppImage"
    download "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-${ARCH}.AppImage" "$LINUXDEPLOY_BIN"
    chmod +x "$LINUXDEPLOY_BIN"
}

ensure_appimagetool() {
    if command -v appimagetool >/dev/null 2>&1; then
        APPIMAGETOOL_BIN="$(command -v appimagetool)"
    else
        APPIMAGETOOL_BIN="$TOOLS_DIR/appimagetool-${ARCH}.AppImage"
        download "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage" "$APPIMAGETOOL_BIN"
        chmod +x "$APPIMAGETOOL_BIN"
    fi
}

PYTHON_DIR=""
ensure_python() {
    PYTHON_DIR="$TOOLS_DIR/cpython-${PYTHON_PBS_VERSION}"
    if [ -x "$PYTHON_DIR/bin/python3" ]; then
        return 0
    fi
    local tarball="$TOOLS_DIR/cpython-${PYTHON_PBS_VERSION}.tar.gz"
    download "https://github.com/astral-sh/python-build-standalone/releases/download/${PYTHON_PBS_TAG}/cpython-${PYTHON_PBS_VERSION}+${PYTHON_PBS_TAG}-x86_64-unknown-linux-gnu-install_only.tar.gz" "$tarball"
    log "Extracting relocatable CPython ${PYTHON_PBS_VERSION}"
    mkdir -p "$PYTHON_DIR"
    tar -xzf "$tarball" -C "$PYTHON_DIR" --strip-components=1
}

# ---------------------------------------------------------------------------------------------------------------------
# build the project

if [ "$CLEAN" = "1" ]; then
    log "Cleaning previous build tree"
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
fi

if [ "$NO_BUILD" != "1" ]; then
    log "Building Clara (DEFAULT_QT=6)"
    make -j"$JOBS" DEFAULT_QT=6
else
    log "Skipping build (--no-build)"
fi

# ---------------------------------------------------------------------------------------------------------------------
# assemble AppDir

log "Assembling AppDir at $APPDIR"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share"

# 1) native libs + frontend + resources via the project's installer
make install DESTDIR="$APPDIR" PREFIX=/usr DEFAULT_QT=6

# 2) relocatable python + PyQt6 (bundles Qt6)
ensure_python
log "Copying CPython into AppDir"
cp -a "$PYTHON_DIR/." "$APPDIR/usr/python/"
BUNDLED_PY="$APPDIR/usr/python/bin/python3"
"$BUNDLED_PY" -m pip install --no-warn-script-location --upgrade pip >/dev/null
log "Installing PyQt6 ${PYQT6_VERSION}"
"$BUNDLED_PY" -m pip install --no-warn-script-location "PyQt6==${PYQT6_VERSION}"

PYQT6_DIR="$("$BUNDLED_PY" -c 'import PyQt6, os; print(os.path.dirname(PyQt6.__file__))')"
QT6_DIR="$PYQT6_DIR/Qt6"

# 3) desktop entry + icons (AppDir root; linuxdeploy/appimagetool want them here)
install -m 644 data/desktop/clara.desktop "$APPDIR/clara.desktop"

ICON_ROOT="$APPDIR/usr/share/icons/hicolor"
for size in 16 32 48 128 256; do
    if [ -f "resources/${size}x${size}/carla.png" ]; then
        mkdir -p "$ICON_ROOT/${size}x${size}/apps"
        install -m 644 "resources/${size}x${size}/carla.png" "$ICON_ROOT/${size}x${size}/apps/carla.png"
    fi
done
if [ -f resources/scalable/carla.svg ]; then
    mkdir -p "$ICON_ROOT/scalable/apps"
    install -m 644 resources/scalable/carla.svg "$ICON_ROOT/scalable/apps/carla.svg"
fi
install -m 644 resources/256x256/carla.png "$APPDIR/carla.png" 2>/dev/null \
    || install -m 644 resources/scalable/carla.svg "$APPDIR/carla.svg"

# ---------------------------------------------------------------------------------------------------------------------
# AppRun

log "Writing AppRun"
cat > "$APPDIR/AppRun" <<APPRUN
#!/bin/sh
# Clara AppRun - runs the bundled CPython against the Clara frontend using the
# AppImage-local prefix, and points Qt at the PyQt6-bundled Qt6 plugins/libs.
HERE="\$(dirname "\$(readlink -f "\$0")")"
export PATH="\$HERE/usr/python/bin:\$HERE/usr/bin:\$PATH"
export LD_LIBRARY_PATH="\$HERE/usr/lib/carla:\$HERE/usr/lib:$QT6_DIR/lib:\$LD_LIBRARY_PATH"
export QT_PLUGIN_PATH="$QT6_DIR/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="$QT6_DIR/plugins/platforms"

exec "\$HERE/usr/python/bin/python3" "\$HERE/usr/share/carla/carla" \
    --with-appname="\$HERE/usr/bin/clara" \
    --with-libprefix="\$HERE/usr" \
    "\$@"
APPRUN
chmod +x "$APPDIR/AppRun"
printf '#!/bin/sh\nexec "%s/AppRun" "$@"\n' "$APPDIR" > "$APPDIR/usr/bin/clara"
chmod +x "$APPDIR/usr/bin/clara"

# ---------------------------------------------------------------------------------------------------------------------
# gather remaining non-Qt dependencies (native libs, jack, sndfile, ...)

ensure_linuxdeploy
ensure_appimagetool

log "Deploying shared-library dependencies"
# Point linuxdeploy at the bundled python and the Carla native libs. Qt is
# intentionally not handled by linuxdeploy-plugin-qt: PyQt6 already ships it.
export LINUXDEPLOY_OUTPUT_VERSION="$VERSION"
"$LINUXDEPLOY_BIN" --appdir "$APPDIR" \
    --executable "$APPDIR/usr/python/bin/python3" \
    --desktop-file "$APPDIR/clara.desktop" \
    --icon-file "$APPDIR/carla.png" \
    2>&1 | sed 's/^/    /' || log "linuxdeploy reported issues; continuing"

# ---------------------------------------------------------------------------------------------------------------------
# build the AppImage

log "Building $OUTPUT_NAME"
export ARCH VERSION
"$APPIMAGETOOL_BIN" "$APPDIR" "$OUTPUT_DIR/$OUTPUT_NAME"

log "Done: $OUTPUT_DIR/$OUTPUT_NAME"
