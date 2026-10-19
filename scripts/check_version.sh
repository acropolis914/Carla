#!/usr/bin/env bash
# ---------------------------------------------------------------------------------------------------------------------
# Clara version consistency guard.
#
# Ensures the version baked into the source tree matches the release tag being
# pushed, so a tag like v1.2.3 can never ship a build that self-reports a
# different version (which is what made the in-app updater re-offer releases).
#
# Checks:
#   - source/frontend/carla_shared.py   base_version           (hard error)
#   - releases.json                     latest + <version> key (hard error)
#   - aur/clara-bin/PKGBUILD            pkgver                 (warn, unless CLARA_STRICT_AUR=1)
#
# Usage:
#   scripts/check_version.sh [vX.Y.Z]
# If no tag is given, the tag at HEAD (git describe --exact-match) is used.
#
# Escape hatch:
#   CLARA_SKIP_VERSION_CHECK=1   (honoured by the pre-push hook, not by this script)
# ---------------------------------------------------------------------------------------------------------------------
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

RAW_TAG="${1:-}"
if [ -z "$RAW_TAG" ]; then
    RAW_TAG="$(git describe --tags --exact-match 2>/dev/null || true)"
fi
if [ -z "$RAW_TAG" ]; then
    echo "check_version: no tag supplied and HEAD is not on an exact tag - nothing to check."
    exit 0
fi

VERSION="$(printf '%s' "$RAW_TAG" | tr -d '[:space:]' | sed -E 's/^[vV]+//; s/^\.+//')"
if ! printf '%s' "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then
    echo "check_version: '$RAW_TAG' does not look like a vX.Y.Z tag." >&2
    exit 1
fi

echo "==> Checking Clara version consistency against tag v${VERSION}"

errors=0
warnings=0

# --- 1. carla_shared.py base_version ---------------------------------------------------------------------------------
SHARED="source/frontend/carla_shared.py"
BASE_VERSION="$(sed -n 's/^[[:space:]]*base_version[[:space:]]*=[[:space:]]*"\(.*\)"/\1/p' "$SHARED" 2>/dev/null | head -n1)"
if [ "$BASE_VERSION" = "$VERSION" ]; then
    echo "  [ok]   carla_shared.py base_version = ${BASE_VERSION}"
else
    echo "  [FAIL] carla_shared.py base_version = '${BASE_VERSION}' (expected ${VERSION})" >&2
    errors=$((errors + 1))
fi

# 2. releases.json latest + entry
if [ -f releases.json ]; then
    LATEST="$(python3 -c 'import json;print(json.load(open("releases.json")).get("latest",""))' 2>/dev/null || true)"
    HAS_ENTRY="$(CLARA_VER="$VERSION" python3 -c 'import json,os;d=json.load(open("releases.json"));print("yes" if os.environ["CLARA_VER"] in d.get("releases",{}) else "no")' 2>/dev/null || true)"
    if [ "$LATEST" = "$VERSION" ]; then
        echo "  [ok]   releases.json latest = ${LATEST}"
    else
        echo "  [FAIL] releases.json latest = '${LATEST}' (expected ${VERSION})" >&2
        errors=$((errors + 1))
    fi
    if [ "$HAS_ENTRY" = "yes" ]; then
        echo "  [ok]   releases.json has an entry for ${VERSION}"
    else
        echo "  [FAIL] releases.json has no entry for ${VERSION}" >&2
        errors=$((errors + 1))
    fi
else
    echo "  [warn] releases.json not found" >&2
    warnings=$((warnings + 1))
fi

PKGVER="$(sed -n 's/^pkgver=\(.*\)/\1/p' aur/clara-bin/PKGBUILD 2>/dev/null | head -n1)"
if [ "$PKGVER" = "$VERSION" ]; then
    echo "  [ok]   aur/clara-bin pkgver = ${PKGVER}"
elif [ "${CLARA_STRICT_AUR:-0}" = "1" ]; then
    echo "  [FAIL] aur/clara-bin pkgver = '${PKGVER}' (expected ${VERSION})" >&2
    errors=$((errors + 1))
else
    echo "  [warn] aur/clara-bin pkgver = '${PKGVER}' (expected ${VERSION}; the release workflow bumps this)"
    warnings=$((warnings + 1))
fi

if [ "$errors" -gt 0 ]; then
    echo "check_version: ${errors} mismatch(es) - tag v${VERSION} is inconsistent with the tree." >&2
    exit 1
fi

echo "check_version: v${VERSION} is consistent (${warnings} warning(s))."
exit 0
