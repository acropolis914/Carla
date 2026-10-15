#!/usr/bin/env bash
# ---------------------------------------------------------------------------------------------------------------------
# Install Clara's git hooks (points core.hooksPath at scripts/git-hooks).
# Run once per clone: scripts/install-git-hooks.sh
# ---------------------------------------------------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

chmod +x scripts/git-hooks/* 2>/dev/null || true
git config core.hooksPath scripts/git-hooks

printf 'Installed git hooks from scripts/git-hooks (core.hooksPath = scripts/git-hooks)\n'
printf 'On a v* tag push this builds the AppImage and Flatpak into dist/.\n'
