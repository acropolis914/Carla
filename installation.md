# Installation & Build Guide

This guide covers installing **Clara** (*Carla Improved*) via Arch Linux / AUR packages (`clara-bin`, `clara-git`) and building directly from source on Linux.

---

## 1. Arch Linux / AUR Installation

Clara provides two AUR packaging options in the `aur/` directory:

### Option A: Binary Package (`clara-bin`) — Fastest (No compilation required)

Downloads and installs the official pre-compiled multi-distro release archive for Arch Linux:

```bash
# Using an AUR helper (paru or yay)
paru -S clara-bin
# or
yay -S clara-bin

# Or build manually using makepkg
cd aur/clara-bin
makepkg -si
```

### Option B: Source Package (`clara-git`) — Compile from latest git main

Clones and compiles the latest source directly against Qt6:

```bash
# Using an AUR helper
paru -S clara-git
# or
yay -S clara-git

# Or build manually using makepkg
cd aur/clara-git
makepkg -si
```

> **Note:** Both packages provide and conflict with `carla`, `carla-git`, and provide all standard host capabilities (`clap-host`, `lv2-host`, `vst-host`, `vst3-host`, etc.).

---


## 2. Building From Source

### Dependencies

#### Arch Linux / Manjaro
```bash
sudo pacman -S --needed \
  base-devel git pkgconf python python-pyqt6 qt6-base qt6-svg \
  alsa-lib fluidsynth liblo libsndfile file sdl2 libglvnd libx11 libxcursor libxrandr
```

*Optional packages:*
```bash
# JACK support and Python OSC / RDF extensions
sudo pacman -S --needed jack python-pyliblo python-rdflib
```

#### Debian / Ubuntu (22.04+ / 24.04+)
```bash
sudo apt install \
  build-essential git pkg-config python3 python3-pyqt6 qt6-base-dev \
  libasound2-dev libfluidsynth-dev liblo-dev libsndfile1-dev libmagic-dev \
  libsdl2-dev libgl1-mesa-dev libx11-dev libxcursor-dev libxrandr-dev
```

---

### Build with `build.sh` (Convenient Script)

Carla Improved includes a helper script `build.sh`:

```bash
# Build with Qt6 (default) and run immediately
./build.sh run

# Clean build and run
./build.sh clean run

# Build and install to system (/usr/local)
./build.sh install
```

---

### Manual Make Build

Alternatively, compile using `make`:

```bash
# 1. Clone repository
git clone https://github.com/acropolis914/Carla.git
cd Carla

# 2. Compile with Qt6 (use -j$(nproc) for parallel jobs)
make DEFAULT_QT=6 -j$(nproc)

# 3. (Optional) Run directly from source without installing
./source/frontend/carla

# 4. Install system-wide
sudo make PREFIX=/usr install
```

To build against Qt5 instead:
```bash
make DEFAULT_QT=5 -j$(nproc)
```

---

## 3. Launching & CLI Options

Once installed:
```bash
# Launch Carla Improved UI
carla

# Autoload the most recent project automatically on launch without prompts
carla --autoload-lastsave

# Search canvas nodes while in Patchbay view
# Press Ctrl+F on the canvas to open the fuzzy search bar.
```
