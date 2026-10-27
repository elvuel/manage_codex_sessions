# Changelog

## 1.3.2

- Fixed stale project child nodes after moving active sessions to trash.
- Updated the extension TypeScript compiler settings for TypeScript 7 compatibility.

## 1.3.1

- Fixed .vsix packaging by creating the dist/ directory before calling sce package.

## 1.3.0

- Aligned the extension version with the repository-wide 1.3.0 release.
- Added Marketplace publish automation, release validation, and updated extension packaging metadata.
- Switched bundled licensing metadata to MIT.

## 0.1.0

- Initial VS Code extension MVP.
- Added active sessions, trash, and project views.
- Added Markdown preview, export, rename, delete, restore, and purge commands.
- Added automatic `CODEX_HOME` file watching with debounced refresh.
- Added local and CI `.vsix` packaging flow.
