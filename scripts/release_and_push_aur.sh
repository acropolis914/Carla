#!/usr/bin/env bash
set -e

# ==============================================================================
# Clara Release & AUR Publish Helper
# Usage: ./scripts/release_and_push_aur.sh <version>
# Example: ./scripts/release_and_push_aur.sh 0.1.1
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_VERSION="$1"

if [ -z "$RAW_VERSION" ]; then
    echo "❌ Error: Missing version argument."
    echo "Usage: $0 <version> (e.g. 0.1.1)"
    exit 1
fi

# Normalize: strip surrounding whitespace, any leading 'v'/'V' and leading dots,
# so 'v1.0.1', '1.0.1', 'v.1.0.1' and '.1.0.1' all resolve to '1.0.1'.
CLEAN_VER="$(printf '%s' "$RAW_VERSION" | tr -d '[:space:]' | sed -E 's/^[vV]+//; s/^\.+//')"

if ! printf '%s' "$CLEAN_VER" | grep -qE '^[0-9]+(\.[0-9]+)+$'; then
    echo "❌ Error: '$RAW_VERSION' is not a valid version (expected e.g. 1.0.1)."
    exit 1
fi

TAG="v${CLEAN_VER}"

echo "🚀 Preparing release for Clara ${TAG}..."

# 1. Ensure working directory is clean
cd "$ROOT_DIR"
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️ Warning: You have uncommitted changes in your main repository."
    read -p "Proceed anyway? (y/N): " CONFIRM
    if [[ "$CONFIRM" != [yY] && "$CONFIRM" != [yY][eE][sS] ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# 2. Update releases.json if present
if [ -f "$ROOT_DIR/releases.json" ]; then
    echo "📝 Updating releases.json latest field..."
    python3 -c "
import json
with open('$ROOT_DIR/releases.json', 'r') as f:
    d = json.load(f)
d['latest'] = '$CLEAN_VER'
if '$CLEAN_VER' not in d.get('releases', {}):
    d['releases']['$CLEAN_VER'] = {
        'version': '$CLEAN_VER',
        'date': '$(date +%Y-%m-%d)',
        'urgency': 'suggested',
        'summary': 'Release $CLEAN_VER',
        'changes': ['Release $CLEAN_VER']
    }
with open('$ROOT_DIR/releases.json', 'w') as f:
    json.dump(d, f, indent=2)
"
    git add "$ROOT_DIR/releases.json"
fi

# 3. Update aur/clara-bin/PKGBUILD
echo "📦 Updating aur/clara-bin/PKGBUILD to ${CLEAN_VER}..."
sed -i "s/^pkgver=.*/pkgver=${CLEAN_VER}/" "$ROOT_DIR/aur/clara-bin/PKGBUILD"
sed -i "s/^pkgrel=.*/pkgrel=1/" "$ROOT_DIR/aur/clara-bin/PKGBUILD"
git add "$ROOT_DIR/aur/clara-bin/PKGBUILD"

# 4. Commit and push bump if changed
if ! git diff --cached --quiet; then
    echo "💾 Committing version bump to main..."
    git commit -m "chore(release): bump version to ${CLEAN_VER}"
    git push origin main
fi


# 5. Create and push Git tag to GitHub (triggers GitHub Actions release build)
echo "🏷️ Tagging ${TAG} and pushing to GitHub..."
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Tag $TAG already exists locally."
else
    git tag -a "$TAG" -m "Release $TAG"
fi
git push origin "$TAG"

# 6. Publish to AUR (clara-bin)
echo "🚀 Publishing clara-bin to AUR..."
AUR_DIR="$ROOT_DIR/aur/clara-bin"
cd "$AUR_DIR"

# Check if aur/clara-bin is already an AUR git repo or initialize clone
if [ ! -d "$AUR_DIR/.git" ]; then
    echo "Cloning AUR repository into temporary build folder..."
    TEMP_AUR=$(mktemp -d)
    git clone ssh://aur@aur.archlinux.org/clara-bin.git "$TEMP_AUR"
    cp "$AUR_DIR/PKGBUILD" "$TEMP_AUR/"
    cd "$TEMP_AUR"
    makepkg --printsrcinfo > .SRCINFO
    git add PKGBUILD .SRCINFO
    git commit -m "chore: bump to ${CLEAN_VER}" || echo "No changes to commit for AUR."
    git push origin master
    rm -rf "$TEMP_AUR"
else
    makepkg --printsrcinfo > .SRCINFO
    git add PKGBUILD .SRCINFO
    git commit -m "chore: bump to ${CLEAN_VER}" || echo "No changes to commit for AUR."
    git push origin master
fi

# 7. Publish to AUR (clara-git)
echo "🚀 Publishing clara-git to AUR..."
GIT_AUR_DIR="$ROOT_DIR/aur/clara-git"
if [ -d "$GIT_AUR_DIR/.git" ]; then
    cd "$GIT_AUR_DIR"
    makepkg --printsrcinfo > .SRCINFO
    git add PKGBUILD .SRCINFO
    git commit -m "chore: sync to ${CLEAN_VER}" || echo "No changes to commit for AUR clara-git."
    git push origin master
else
    echo "⚠️  Warning: $GIT_AUR_DIR is not a git clone; skipping clara-git AUR publish."
    echo "    Clone it with: git clone ssh://aur@aur.archlinux.org/clara-git.git $GIT_AUR_DIR"
fi

echo "✅ Done! Release ${TAG} pushed to GitHub and published to AUR (clara-bin, clara-git)."
