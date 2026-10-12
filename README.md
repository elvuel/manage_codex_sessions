# manage_codex_sessions

[![Python](https://img.shields.io/badge/python-3.14%2B-blue.svg)](./README.md)
[![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-2ea44f.svg)](./README.md)
[![GUI](https://img.shields.io/badge/GUI-PySide6-41CD52.svg)](./README.md)
[![Build](https://img.shields.io/badge/build-PyInstaller-f97316.svg)](./README.md)
[![Release](https://github.com/elvuel/manage_codex_sessions/actions/workflows/tag-release.yml/badge.svg)](https://github.com/elvuel/manage_codex_sessions/actions/workflows/tag-release.yml)

English | [简体中文](./README.zh-CN.md)

`manage_codex_sessions` is a standalone utility for browsing and managing local Codex sessions.
It ships with both a CLI and a Qt GUI for listing active sessions, exploring trash, renaming threads,
deleting safely to trash, restoring deleted sessions, and packaging the GUI as a distributable app.

## Highlights

- Inspect active sessions and trashed sessions from one tool.
- Rename sessions from the CLI or by double-clicking the `Thread` column in the GUI.
- Delete to trash by default, then restore or permanently purge later.
- Filter sessions by project, working directory, title, source, and more.
- Summarize sessions per project for quick cleanup.
- Use the CLI in English or Simplified Chinese with `--lang` or `CODEX_LANG`.
- Use a bilingual GUI with automatic system-language detection and manual override.
- Build a GUI binary for Windows, macOS, or Linux with the included PyInstaller script.

## Project Layout

- `manage_codex_sessions.py` — main CLI entry point plus shared GUI logic.
- `manage_codex_sessions_gui.py` — minimal GUI launcher, ideal for packaging.
- `build_manage_codex_sessions_gui.py` — cross-platform build script for PyInstaller.
- `build_manage_codex_sessions_gui.ps1` — PowerShell wrapper for Windows users.
- `pyproject.toml` — project metadata, editable install config, and test settings.
- `tests/` — automated regression coverage for the core session flows.
- `CHANGELOG.md` — release history and milestone summary.
- `requirements-build.txt` — build-time dependencies.

## Requirements

- Python `3.14+`
- Windows, macOS, or Linux

Optional dependencies:

- `PySide6` for the GUI
- `PyInstaller` for packaging

## Install

Install only the GUI runtime:

```bash
python -m pip install PySide6
```

Install packaging dependencies too:

```bash
python -m pip install -r requirements-build.txt
```

Install the project in editable mode with development tools:

```bash
python -m pip install -e ".[dev]"
```

## Development

Run the automated test suite:

```bash
python -m pytest
```

Show the current CLI or GUI launcher version:

```bash
python manage_codex_sessions.py --version
python manage_codex_sessions_gui.py --version
```

Track release notes and milestone history in `CHANGELOG.md`.

## CLI Quick Start

List active sessions:

```bash
python manage_codex_sessions.py query
```

Force CLI language:

```bash
python manage_codex_sessions.py query --lang en
python manage_codex_sessions.py query --lang zh-CN
```

List trashed sessions:

```bash
python manage_codex_sessions.py trash
```

Summarize sessions by project:

```bash
python manage_codex_sessions.py projects
```

Rename a session:

```bash
python manage_codex_sessions.py rename --id <session-id> --name "New session name"
```

Move a session to trash:

```bash
python manage_codex_sessions.py delete --id <session-id> --yes
```

Delete all active sessions permanently:

```bash
python manage_codex_sessions.py delete-all --yes --permanent
```

Restore a session from trash:

```bash
python manage_codex_sessions.py restore --id <session-id> --yes
```

Empty the entire trash:

```bash
python manage_codex_sessions.py empty-trash --all --yes
```

Launch the GUI:

```bash
python manage_codex_sessions.py gui
```

Force the GUI language:

```bash
python manage_codex_sessions.py gui --lang en
python manage_codex_sessions.py gui --lang zh-CN
```

Or run the dedicated GUI entry point:

```bash
python manage_codex_sessions_gui.py
```

You can also set `CODEX_LANG=en` or `CODEX_LANG=zh-CN` for CLI and GUI.
For GUI-only override, set `CODEX_UI_LANG=en` or `CODEX_UI_LANG=zh-CN` before launching.

## GUI Features

- Separate tabs for active sessions and trash.
- Single-select, multi-select, and select-all workflows.
- Project filter and free-text search.
- In-place rename flow by double-clicking the `Thread` column.
- Restore, purge, and bulk delete actions.
- English and Simplified Chinese CLI support.
- English and Simplified Chinese UI support.
- Single-instance lock to prevent duplicate GUI windows.

## Cross-Platform Build

Build a single-file GUI artifact:

```bash
python build_manage_codex_sessions_gui.py
```

Skip dependency installation:

```bash
python build_manage_codex_sessions_gui.py --skip-dependency-install
```

Build a directory bundle instead:

```bash
python build_manage_codex_sessions_gui.py --onedir --skip-dependency-install
```

Pass extra flags through to PyInstaller:

```bash
python build_manage_codex_sessions_gui.py -- --icon app.ico
```

## Release Automation

Pushing a new `v*` Git tag automatically builds Windows, macOS, and Linux release artifacts and publishes them to a GitHub Release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow packages Windows builds as `.zip`, Linux/macOS builds as `.tar.gz`, and publishes a matching `.sha256` file for each asset.

You can also rerun a release manually from the Actions tab with `workflow_dispatch` by providing an existing `v*` tag. Existing assets with the same name are replaced.

## Windows PowerShell Shortcut

Single-file build:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_manage_codex_sessions_gui.ps1
```

Skip dependency installation:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_manage_codex_sessions_gui.ps1 -SkipDependencyInstall
```

Directory build:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_manage_codex_sessions_gui.ps1 -OneDir -SkipDependencyInstall
```

Typical outputs:

- Windows: `dist\manage_codex_sessions_gui.exe` or `dist\manage_codex_sessions_gui\`
- Linux: `dist/manage_codex_sessions_gui` or `dist/manage_codex_sessions_gui/`
- macOS: `dist/manage_codex_sessions_gui` or `dist/manage_codex_sessions_gui.app`

## Data Locations

By default, the tool reads from the current user's Codex data directory:

- `~/.codex/session_index.jsonl`
- `~/.codex/sessions/`
- `~/.codex/session_trash/`

Use `--codex-home` to point at a different Codex data directory.
