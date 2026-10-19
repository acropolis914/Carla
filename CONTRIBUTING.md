# Contributing to Clara

Thank you for your interest in contributing to **Clara** (*Carla Improved*)! We are actively looking for developers, sound designers, UI/UX contributors, and co-maintainers.

---

## 🤖 AI-Assisted Development Policy

Clara embraces modern agentic AI tooling while maintaining strict standards for code health and stability:

1. **AI Usage is Permitted**: You are allowed to use AI tools (Google Antigravity, Gemini, Claude, Copilot, etc.) to brainstorm, scaffold, write boilerplate, and draft code.
2. **Mandatory Explicit Disclosure**: Whenever AI tools are utilized in formulating a pull request, you **must explicitly declare it in the PR description** (e.g., specifying the AI model/agent used and the scope of assistance).

3. **Extensive Quality Review**:
   - AI-assisted code is **scrutinized just as strictly as human-written code**, with deep checks for memory leaks, Qt signal/slot race conditions, performance overheads, and design coherence.
   - Do not submit unreviewed raw AI output or speculative "hallucinated" API calls.
   - You are personally responsible for testing, verifying, and maintaining the code you submit.

---

## 🛠️ Getting Started

### 1. Fork & Clone
```bash
git clone https://github.com/<your-username>/Carla.git
cd Carla
```

### 2. Build & Test Locally
```bash
# Build backend and resources
./build.sh

# Or compile manually with make
make -j$(nproc)

# Run Clara
./bin/carla
```

---

## 📋 Pull Request Guidelines

1. **Target Branch**: Open all PRs against the primary branch (`main` or `master`).
2. **Conventional Commits**: Format commit messages according to the [Conventional Commits](https://www.conventionalcommits.org/) specification:
   - `feat(...)`: new functionality or significant UI addition
   - `fix(...)`: bug fix or regression repair
   - `perf(...)`: rendering or DSP performance improvement
   - `docs(...)`: documentation or changelog update
   - `refactor(...)`: non-functional code reorganization
3. **MANDATORY: CHANGELOG.md Updates**:
   - Every functional change, feature, or bug fix **MUST include a corresponding entry in [CHANGELOG.md](CHANGELOG.md)**.
4. **Qt5 / Qt6 Compatibility**:
   - Always route Qt imports through `source/frontend/qt_compat.py` to ensure seamless execution across both PyQt5 and PyQt6 runtime environments.
5. **Testing Verification**:
   - Always run the application locally and test edge cases (e.g. creating/deleting nodes, loading/saving `.carxp` sessions, drag connections) before opening a PR.

---

## 🐛 Reporting Bugs & Issues

If you encounter bugs, visual glitches, or unexpected behavior:
1. Search [Existing Issues](https://github.com/acropolis914/Clara/issues) to avoid duplicate reports.
2. Provide your Linux distribution, desktop environment (X11 / Wayland), Qt version (`qmake -v`), and relevant console logs.
3. Use the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md).

---

## 🚀 Release Process

Releases are cut by pushing an annotated `vX.Y.Z` tag, which triggers the **Multi-distro packaging** workflow (builds every distro, creates the GitHub release from `releases.json`, and publishes `clara-bin` to the AUR).

The version has to agree in three places before tagging:
- `base_version` in `source/frontend/carla_shared.py` (drives `CLARA_VERSION_STRING`)
- `latest` plus a matching `releases[<version>]` entry in `releases.json`
- `pkgver` in `aur/clara-bin/PKGBUILD`

Use the helper script, which updates all of the above, commits, and pushes the tag:
```bash
./scripts/release_and_push_aur.sh 1.2.3
```

To check consistency without releasing (exits non-zero on any mismatch):
```bash
./scripts/check_version.sh v1.2.3
```

The same check runs in CI (the `version-check` job) and, when installed via `./scripts/install-git-hooks.sh`, in the local `pre-push` hook — so a tag whose version disagrees with the tree is blocked before it can publish.
