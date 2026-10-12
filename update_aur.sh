#!/usr/bin/env bash
AUR_DIR="$(dirname "$0")/aur/clara-git"
if [ ! -d "$AUR_DIR" ]; then
  echo "AUR directory not found: $AUR_DIR"
  exit 1
fi
cd "$AUR_DIR"
makepkg --printsrcinfo > .SRCINFO
git add PKGBUILD .SRCINFO
git commit -m "chore: update PKGBUILD and .SRCINFO"
git push origin master
