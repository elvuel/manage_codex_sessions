# manage-codex-sessions-ts

Standalone TypeScript CLI and reusable core for browsing and managing local Codex sessions.

## What it supports

- List active sessions.
- List trashed sessions.
- Summarize sessions by project.
- Export one session to Markdown.
- Rename active or trashed sessions.
- Move active sessions to trash.
- Restore trashed sessions.
- Permanently delete active or trashed sessions.

## Install

```bash
npm install
```

## Build

```bash
npm run compile
```

## Test

```bash
npm test
```

## CLI usage

```bash
node ./out/cli.js --help
node ./out/cli.js query --json --show-files
node ./out/cli.js export --id <session-id> --output ./session.md
node ./out/cli.js delete --id <session-id> --yes
node ./out/cli.js restore --id <session-id> --yes
```

If published to npm, the package exposes the `manage-codex-sessions-ts` executable.

## Library usage

The package also exports the TypeScript core from `out/core.js`.

## Data directory

By default the CLI reads Codex data from `CODEX_HOME` or `~/.codex`.
Use `--codex-home <path>` to point at a different Codex data directory.

## Pack tarball

```bash
npm run pack:tarball
```
