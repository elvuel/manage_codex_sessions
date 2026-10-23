# Changelog

All notable changes to this project are documented in this file.

## [1.3.1] - 2026-10-23

### Fixed

- Created the VS Code extension dist/ output directory before packaging the .vsix in CI and local release flows.
- Corrected the standalone TypeScript CLI --help exit code so CI smoke tests pass.
## [1.3.0] - 2026-10-23

### Added

- Standalone TypeScript CLI packaging under manage-codex-sessions-ts/.
- Native VS Code extension support for browsing active sessions, trash, projects, Markdown previews, export, rename, restore, and delete flows.
- GitHub Actions support for packaging and optionally publishing the VS Code extension to the Marketplace.

### Changed

- Unified the Python app, standalone TypeScript CLI, and VS Code extension under the shared 1.3.0 release version.
- Switched the project licensing metadata and bundled license texts to MIT.
## [1.2.0] - 2026-10-15

### Added

- GUI support for copying one or many `session_id` values via toolbar button, `Ctrl+C`, and the context menu.
- CLI and GUI support for exporting a session transcript to Markdown.
- GUI Markdown preview with split raw/preview panes, per-pane search, and raw Markdown copy.

### Changed

- Double-clicking a session row now opens the Markdown preview.
- Session rename is now available from the GUI right-click menu.

## [1.1.1] - 2026-10-12

### Fixed

- Avoided passing the Windows `.ico` file to PyInstaller on macOS while still bundling it for the runtime GUI window icon.
- Restored cross-platform tagged release compatibility for Windows, Linux, and macOS.

## [1.1.0] - 2026-10-12

### Added

- In-window GUI language switcher for Simplified Chinese and English.
- Bundled application icon asset for the GUI window and PyInstaller builds.

### Changed

- GUI now defaults to Simplified Chinese when no explicit GUI language override is provided.
- PyInstaller builds now embed the checked-in application icon and bundle it for runtime use.

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
