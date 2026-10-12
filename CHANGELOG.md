# Changelog

All notable changes to this project are documented in this file.

## [1.0.0] - 2026-10-12

### Added

- Stable `1.0.0` release for the bilingual Codex session manager CLI and Qt GUI.
- Cross-platform automated testing on Windows, Linux, and macOS.
- Standard project metadata and editable install support via `pyproject.toml`.

### Changed

- Promoted the project from release candidate to the first stable production release.
- GitHub Releases now automatically mark `-rc`, `-beta`, and `-alpha` tags as prereleases.

## [1.0.0-rc1] - 2026-10-12

### Added

- Bilingual CLI support with `--lang`, `CODEX_LANG`, and localized command help.
- Bilingual Qt GUI with automatic language detection and manual override.
- Cross-platform PyInstaller build scripts for Windows, macOS, and Linux.
- Tag-driven GitHub Actions release workflow with optional manual rebuilds for existing `v*` tags.
- Basic automated test coverage for session listing, trash, restore, rename, and CLI JSON output.
- Standard `pyproject.toml` metadata with console entry points and development extras.

### Changed

- English is the default README, with a dedicated Simplified Chinese companion document.
- Release assets now publish platform archives together with matching SHA-256 checksum files.
