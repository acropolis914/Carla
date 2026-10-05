#!/usr/bin/env bash

set -euo pipefail

clean=false
qt=6
run=false
install=false

for arg in "$@"; do
    case "$arg" in
        clean)
            clean=true
        ;;
        qt5)
            qt=5
        ;;
        qt6)
            qt=6
        ;;
        run)
            run=true
        ;;
        install)
            install=true
        ;;
        *)
            printf 'Usage: %s [clean] [qt5|qt6] [run] [install]\n' "$0" >&2
            exit 2
        ;;
    esac
done

# Pick the requested Qt toolchain, falling back if unavailable.
if [[ "$qt" == 6 ]]; then
    if command -v pyuic6 >/dev/null 2>&1; then
        pyuic=pyuic6
        elif command -v pyuic5 >/dev/null 2>&1; then
        printf 'Qt6 Python tools unavailable, falling back to Qt5.\n'
        qt=5
        pyuic=pyuic5
    else
        printf 'Error: neither pyuic6 nor pyuic5 is available.\n' >&2
        exit 1
    fi
else
    if command -v pyuic5 >/dev/null 2>&1; then
        pyuic=pyuic5
        elif command -v pyuic6 >/dev/null 2>&1; then
        printf 'Qt5 Python tools unavailable, falling back to Qt6.\n'
        qt=6
        pyuic=pyuic6
    else
        printf 'Error: neither pyuic5 nor pyuic6 is available.\n' >&2
        exit 1
    fi
fi

printf 'Using Qt%d (%s)\n' "$qt" "$pyuic"

if "$clean"; then
    make clean
fi

make_args=(
    -j"${JOBS:-$(nproc)}"
    FRONTEND_TYPE="$qt"
)

make "${make_args[@]}"

if "$install"; then
    sudo make install
fi

if "$run"; then
    if [[ "$qt" == 6 ]]; then
        theme=qt6ct
    else
        theme=qt5ct
    fi
    
    exec env QT_QPA_PLATFORMTHEME="$theme" ./source/frontend/carla
fi