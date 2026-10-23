# manage_codex_sessions VS Code extension prototype

This folder contains a VS Code extension MVP for browsing and managing local Codex sessions from the editor.

## What the MVP supports

- List active sessions in a dedicated activity bar view.
- List trashed sessions in a separate view.
- Group active sessions by project.
- Auto-refresh the views when files under the current `CODEX_HOME` change on disk.
- Preview session Markdown side-by-side in VS Code.
- Export one session to Markdown.
- Rename active or trashed sessions.
- Move active sessions to trash.
- Restore trashed sessions.
- Permanently delete trashed sessions.
- Copy a session ID from the tree item context menu.

## Core architecture

The extension now uses a native TypeScript session core in `src/core.ts`.
It reads and writes the Codex session files directly, so the packaged `.vsix` no longer depends on Python or the repository layout.

## Requirements

- VS Code
- Local Codex session data under `CODEX_HOME` or `~/.codex`

## Settings

- `manageCodexSessions.codexHome` — optional `CODEX_HOME` override
- `manageCodexSessions.autoRefresh` — enable or disable file watching refresh

## After installation

- The Activity Bar shows a `Codex Sessions` icon on the left side.
- The container includes 3 views:
  - `Active Sessions`
  - `Trash`
  - `Projects`
- Select a session row to inspect it in the tree.
- Use the inline buttons on a session row to:
  - preview session Markdown
  - copy the session ID
- Right-click a session to open the context menu. Depending on whether the session is active or in trash, you can:
  - preview session Markdown
  - export session Markdown
  - rename the session
  - copy the session ID
  - move the session to trash
  - restore the session
  - permanently delete the session
- Use the title-bar actions to refresh the views or change the `CODEX_HOME` override.

## Development

```bash
cd vscode-extension
npm install
npm test
```

Then open the `vscode-extension` folder in VS Code and press `F5` to launch an Extension Development Host.

## Standalone TypeScript CLI

Use the separate package under `../manage-codex-sessions-ts/` for the standalone Node.js CLI.

## Build a `.vsix`

```bash
cd vscode-extension
npm install
npm run package:vsix
```

The packaged file is written to `vscode-extension/dist/manage-codex-sessions-vscode.vsix`.

## CI and release flow

- Pull requests and pushes compile and test the extension in GitHub Actions.
- Tagged releases package a `.vsix` artifact, test the extension, optionally publish it to the VS Code Marketplace when `VSCODE_MARKETPLACE_ENABLED=true` and `VSCE_PAT` are configured, and upload release assets to GitHub Releases.
- The manual workflow `.github/workflows/publish-vscode-marketplace.yml` can publish any branch, tag, or commit to the VS Code Marketplace.

## Publish to the Marketplace

1. Create a VS Code Marketplace publisher.
2. Replace the placeholder `publisher` value in `package.json` with your real publisher ID.
3. Add a GitHub Actions secret named `VSCE_PAT` with a Marketplace publishing token.
4. Add a GitHub Actions repository variable named `VSCODE_MARKETPLACE_ENABLED` and set it to `true` to enable Marketplace publishing from the tagged-release workflow.
5. Ensure the Git tag exactly matches `vscode-extension/package.json` version, for example `v1.3.1` for `"version": "1.3.1"`.
6. Choose one of these publish paths:
   - Manual GitHub Actions publish: run `Publish VS Code extension to Marketplace` and set `ref` to the branch, tag, or commit to publish.
   - Tagged release publish: push a `v*` tag or run the tagged release workflow manually with an existing `v*` tag.
7. For local publishing, run `npm run publish:marketplace` inside `vscode-extension/` after setting `VSCE_PAT` in your shell.
## Before publishing to the Marketplace

- `npm run check:marketplace` fails if `publisher` is still `local-dev` or the Marketplace icon is not a PNG.
- The top-level extension icon now uses `media/manage_codex_sessions.png` for Marketplace compatibility.
