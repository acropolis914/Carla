#!/usr/bin/env bash
# Clara One-Click Interactive Terminal Updater
# SPDX-License-Identifier: GPL-2.0-or-later

set -e

# ANSI styling
BOLD="\033[1m"
GREEN="\033[1;32m"
BLUE="\033[1;34m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
MAGENTA="\033[1;35m"
RESET="\033[0m"

TARGET_VERSION="${1:-}"

clear
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}║             ${BOLD}✨ CLARA INTERACTIVE UPDATER ✨${RESET}${CYAN}            ║${RESET}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""

# 1. Fetch release metadata if version is not explicitly passed
RELEASES_URL="https://raw.githubusercontent.com/acropolis914/Clara/main/releases.json"

if [ -z "$TARGET_VERSION" ]; then
    echo -e "${BLUE}ℹ Fetching latest release information...${RESET}"
    if command -v curl >/dev/null 2>&1; then
        LATEST_INFO=$(curl -sSL "$RELEASES_URL" || true)
    elif command -v wget >/dev/null 2>&1; then
        LATEST_INFO=$(wget -qO- "$RELEASES_URL" || true)
    fi
    TARGET_VERSION=$(echo "$LATEST_INFO" | grep -o '"latest": *"[^"]*"' | head -n1 | cut -d'"' -f4)
fi

[ -z "$TARGET_VERSION" ] && TARGET_VERSION="latest"

echo -e "${BLUE}Target version:${RESET} ${GREEN}v${TARGET_VERSION}${RESET}"
echo ""

# 2. Detect Distribution Family
DISTRO_FAMILY=""

if [ -f /etc/os-release ]; then
    . /etc/os-release
    ID_LIKE_LOWER=$(echo "${ID_LIKE:-}" | tr '[:upper:]' '[:lower:]')
    ID_LOWER=$(echo "${ID:-}" | tr '[:upper:]' '[:lower:]')

    if [[ "$ID_LOWER" =~ (arch|manjaro|endeavouros|garuda|cachyos|artix) ]] || [[ "$ID_LIKE_LOWER" =~ arch ]]; then
        DISTRO_FAMILY="arch"
    elif [[ "$ID_LOWER" =~ (ubuntu|debian|pop|mint|elementary|kali|zorin) ]] || [[ "$ID_LIKE_LOWER" =~ (debian|ubuntu) ]]; then
        DISTRO_FAMILY="ubuntu"
    elif [[ "$ID_LOWER" =~ (fedora|rhel|centos|rocky|almalinux|nobara) ]] || [[ "$ID_LIKE_LOWER" =~ (fedora|rhel) ]]; then
        DISTRO_FAMILY="fedora"
    elif [[ "$ID_LOWER" =~ void ]]; then
        DISTRO_FAMILY="void"
    elif [[ "$ID_LOWER" =~ alpine ]]; then
        DISTRO_FAMILY="alpine"
    elif [[ "$ID_LOWER" =~ nixos ]] || [ -d "/nix" ]; then
        DISTRO_FAMILY="nix"
    fi
fi

# 3. Interactive fallback picker if detection fails or user wants to override
prompt_picker() {
    echo -e "${YELLOW}Could not automatically determine package manager family.${RESET}"
    echo -e "Please select your target distribution type:"
    echo -e "  ${BOLD}1)${RESET} Arch Linux / AUR (paru / yay / pacman)"
    echo -e "  ${BOLD}2)${RESET} Ubuntu / Debian (.deb)"
    echo -e "  ${BOLD}3)${RESET} Fedora / RHEL (.rpm)"
    echo -e "  ${BOLD}4)${RESET} Void Linux (tarball / xbps)"
    echo -e "  ${BOLD}5)${RESET} Alpine Linux (tarball / apk)"
    echo -e "  ${BOLD}6)${RESET} Nix / NixOS"
    read -rp "Enter choice [1-6]: " choice
    case "$choice" in
        1) DISTRO_FAMILY="arch" ;;
        2) DISTRO_FAMILY="ubuntu" ;;
        3) DISTRO_FAMILY="fedora" ;;
        4) DISTRO_FAMILY="void" ;;
        5) DISTRO_FAMILY="alpine" ;;
        6) DISTRO_FAMILY="nix" ;;
        *) echo -e "${RED}Invalid selection. Aborting.${RESET}"; exit 1 ;;
    esac
}

[ -z "$DISTRO_FAMILY" ] && prompt_picker

echo -e "${BLUE}Detected package ecosystem:${RESET} ${MAGENTA}${DISTRO_FAMILY}${RESET}"
echo ""

# Helper to execute privileged command via pkexec or sudo
run_privileged() {
    if [ "$EUID" -eq 0 ]; then
        "$@"
    elif command -v pkexec >/dev/null 2>&1; then
        pkexec "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        echo -e "${RED}Error: Neither pkexec nor sudo is available to execute root operations.${RESET}"
        exit 1
    fi
}

TMP_DIR=$(mktemp -d /tmp/clara-update-XXXXXX)
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# 4. Perform package installation per distro
case "$DISTRO_FAMILY" in
    arch)
        echo -e "${CYAN}→ Installing via Arch AUR / PKGBUILD...${RESET}"
        if command -v paru >/dev/null 2>&1; then
            paru -S --noconfirm clara-git || paru -S --noconfirm clara-bin
        elif command -v yay >/dev/null 2>&1; then
            yay -S --noconfirm clara-git || yay -S --noconfirm clara-bin
        else
            echo -e "${YELLOW}AUR helper not found. Downloading direct release package from GitHub...${RESET}"
            DOWNLOAD_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/clara-archlinux-x86_64.tar.zst"
            curl -sSL "$DOWNLOAD_URL" -o "$TMP_DIR/clara.tar.zst" || wget -qO "$TMP_DIR/clara.tar.zst" "$DOWNLOAD_URL"
            run_privileged tar --zstd -xvf "$TMP_DIR/clara.tar.zst" -C /
        fi
        ;;

    ubuntu)
        echo -e "${CYAN}→ Downloading Debian/Ubuntu .deb package...${RESET}"
        DEB_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/clara-ubuntu-x86_64.deb"
        curl -sSL "$DEB_URL" -o "$TMP_DIR/clara.deb" || wget -qO "$TMP_DIR/clara.deb" "$DEB_URL"
        echo -e "${CYAN}→ Installing package...${RESET}"
        run_privileged dpkg -i "$TMP_DIR/clara.deb" || run_privileged apt-get install -f -y
        ;;

    fedora)
        echo -e "${CYAN}→ Downloading Fedora/RHEL .rpm package...${RESET}"
        RPM_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/clara-fedora-x86_64.rpm"
        curl -sSL "$RPM_URL" -o "$TMP_DIR/clara.rpm" || wget -qO "$TMP_DIR/clara.rpm" "$RPM_URL"
        echo -e "${CYAN}→ Installing package via dnf...${RESET}"
        run_privileged dnf install -y "$TMP_DIR/clara.rpm"
        ;;

    void)
        echo -e "${CYAN}→ Downloading Void Linux tarball...${RESET}"
        VOID_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/clara-void-x86_64.tar.zst"
        curl -sSL "$VOID_URL" -o "$TMP_DIR/clara.tar.zst" || wget -qO "$TMP_DIR/clara.tar.zst" "$VOID_URL"
        echo -e "${CYAN}→ Extracting package to system root...${RESET}"
        run_privileged tar --zstd -xvf "$TMP_DIR/clara.tar.zst" -C /
        ;;

    alpine)
        echo -e "${CYAN}→ Downloading Alpine Linux tarball...${RESET}"
        ALPINE_URL="https://github.com/acropolis914/Clara/releases/download/v${TARGET_VERSION}/clara-alpine-x86_64.tar.zst"
        curl -sSL "$ALPINE_URL" -o "$TMP_DIR/clara.tar.zst" || wget -qO "$TMP_DIR/clara.tar.zst" "$ALPINE_URL"
        echo -e "${CYAN}→ Extracting package to system root...${RESET}"
        run_privileged tar --zstd -xvf "$TMP_DIR/clara.tar.zst" -C /
        ;;

    nix)
        echo -e "${CYAN}→ Updating Nix profile flake...${RESET}"
        nix profile install --upgrade "github:acropolis914/Clara/v${TARGET_VERSION}" || nix profile install --upgrade github:acropolis914/Clara
        ;;
esac

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${RESET}"
echo -e "${GREEN}✓ Installed. Press enter to exit, please restart Clara${RESET}"
echo -e "${GREEN}════════════════════════════════════════════════════════${RESET}"
read -r
