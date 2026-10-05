# Installation & Build Guide

This guide covers installing **Carla Improved** via AUR / Arch package (`PKGBUILD`) and building directly from source on Linux.

---

## 1. Arch Linux / AUR Installation

### Option A: Using the included PKGBUILD (Recommended)

Clone the repository and build the package locally using `makepkg`:

```bash
git clone https://github.com/acropolis914/Carla.git carla-improved
cd carla-improved

# Build and install package and dependencies via pacman
makepkg -si
```

> **Note:** The package installs as `carla-improved`, conflicts with and cleanly replaces upstream `carla` and `carla-git`, and provides all standard Carla capabilities (`clap-host`, `lv2-host`, `vst-host`, etc.).

### Option B: Using an AUR Helper (e.g. `paru` / `yay`)

If published to AUR as `carla-improved` (or using local PKGBUILD directory):

```bash
# Using yay
yay -S carla-improved

# Using paru
paru -S carla-improved
```

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
