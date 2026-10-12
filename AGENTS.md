# Agent Guidelines

## 📝 Change Tracking
- **MANDATORY**: All functional changes, features, bug fixes, and significant UI updates MUST be recorded in [CHANGELOG.md](file:///home/acroarch/Documents/Projects/git-clones/Carla/CHANGELOG.md) BEFORE or alongside each commit. NEVER skip updating CHANGELOG.md.
- Keep entries structured under the latest date / version with datetime timestamps, commit hashes, and clear, concise bullet points following [Keep a Changelog](https://keepachangelog.com/) standards.

## 🚀 Commits
- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, etc.).

## ⚡ Direct Execution (Anti-Exploration Loop)
- Limit codebase reading to targeted single lookups.
- NEVER chain more than 2-3 exploratory reads without immediately modifying files or producing the implementation. Move straight to writing the code.

