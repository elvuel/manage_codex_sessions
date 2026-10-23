#!/usr/bin/env node
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import {
  CodexSessionsStore,
  SessionSummary,
  formatDeleteSummary,
  formatPurgeSummary,
  formatRestoreSummary,
} from './core';

type CommandName =
  | 'query'
  | 'trash'
  | 'projects'
  | 'export'
  | 'rename'
  | 'delete'
  | 'delete-all'
  | 'restore'
  | 'empty-trash';

interface ParsedArgs {
  command?: CommandName;
  codexHome?: string;
  json: boolean;
  showFiles: boolean;
  ids: string[];
  output?: string;
  name?: string;
  trash: boolean;
  yes: boolean;
  permanent: boolean;
  all: boolean;
  limit?: number;
  help: boolean;
  version: boolean;
}

async function main(argv = process.argv.slice(2)): Promise<number> {
  const args = parseArgs(argv);
  if (args.version) {
    console.log(readPackageVersion());
    return 0;
  }
  if (args.help) {
    printHelp();
    return 0;
  }
  if (!args.command) {
    printHelp();
    return 1;
  }

  const store = new CodexSessionsStore(args.codexHome);

  switch (args.command) {
    case 'query': {
      const sessions = applySelection(await store.buildSessionSummaries(), args);
      if (args.json) {
        printJson(sessions.map((session) => session.toRecord(args.showFiles)));
      } else {
        printSessions(sessions, args.showFiles, false);
      }
      return 0;
    }
    case 'trash': {
      const sessions = applySelection(await store.buildTrashSummaries(), args);
      if (args.json) {
        printJson(sessions.map((session) => session.toRecord(args.showFiles)));
      } else {
        printSessions(sessions, args.showFiles, true);
      }
      return 0;
    }
    case 'projects': {
      const sessions = applySelection(args.trash ? await store.buildTrashSummaries() : await store.buildSessionSummaries(), args);
      const stats = await store.buildProjectStats(sessions);
      if (args.json) {
        printJson(stats.map(([project, sessionCount]) => ({ project, session_count: sessionCount })));
      } else {
        printProjects(stats);
      }
      return 0;
    }
    case 'export': {
      const session = await requireSingleSession(store, args, args.trash ? 'trash' : 'active');
      const outputPath = await store.exportSessionMarkdown(session, args.output);
      console.log(`Exported session ${session.sessionId} to ${outputPath}`);
      return 0;
    }
    case 'rename': {
      if (!args.name) {
        throw new Error('Missing required option: --name');
      }
      const session = await requireSingleSession(store, args, args.trash ? 'trash' : 'active');
      const changed = await store.renameSession(session.sessionId, args.name, args.trash);
      if (!changed) {
        throw new Error(`Session not found: ${session.sessionId}`);
      }
      console.log(`Renamed session ${session.sessionId} to ${args.name}`);
      return 0;
    }
    case 'delete': {
      const sessions = applySelection(await store.buildSessionSummaries(), args);
      if (sessions.length === 0) {
        console.log('No matching active sessions.');
        return 0;
      }
      await confirmIfNeeded(args, args.permanent ? 'permanently delete' : 'move to trash', sessions);
      const result = await store.deleteSessions(sessions, args.permanent);
      console.log(formatDeleteSummary(result, !args.permanent));
      return 0;
    }
    case 'delete-all': {
      const sessions = await store.buildSessionSummaries();
      if (sessions.length === 0) {
        console.log('No active sessions to delete.');
        return 0;
      }
      await confirmIfNeeded(args, args.permanent ? 'permanently delete' : 'move to trash', sessions);
      const result = await store.deleteSessions(sessions, args.permanent);
      console.log(formatDeleteSummary(result, !args.permanent));
      return 0;
    }
    case 'restore': {
      const sessions = args.all ? await store.buildTrashSummaries() : applySelection(await store.buildTrashSummaries(), args);
      if (sessions.length === 0) {
        console.log('No trashed sessions to restore.');
        return 0;
      }
      await confirmIfNeeded(args, 'restore', sessions);
      console.log(formatRestoreSummary(await store.restoreSessionsFromTrash(sessions)));
      return 0;
    }
    case 'empty-trash': {
      const sessions = args.all ? await store.buildTrashSummaries() : applySelection(await store.buildTrashSummaries(), args);
      if (sessions.length === 0) {
        console.log('No trashed sessions to permanently delete.');
        return 0;
      }
      await confirmIfNeeded(args, 'permanently delete from trash', sessions);
      console.log(formatPurgeSummary(await store.purgeTrashedSessions(sessions)));
      return 0;
    }
    default:
      printHelp();
      return 1;
  }
}

function parseArgs(argv: string[]): ParsedArgs {
  const args: ParsedArgs = {
    json: false,
    showFiles: false,
    ids: [],
    trash: false,
    yes: false,
    permanent: false,
    all: false,
    help: false,
    version: false,
  };

  const aliasMap: Record<string, CommandName> = {
    list: 'query',
    query: 'query',
    trash: 'trash',
    'list-trash': 'trash',
    projects: 'projects',
    export: 'export',
    rename: 'rename',
    delete: 'delete',
    'delete-all': 'delete-all',
    delete_all: 'delete-all',
    restore: 'restore',
    'empty-trash': 'empty-trash',
  };

  let index = 0;
  while (index < argv.length) {
    const token = argv[index];
    if (!args.command && !token.startsWith('-') && aliasMap[token]) {
      args.command = aliasMap[token];
      index += 1;
      continue;
    }

    switch (token) {
      case '--help':
      case '-h':
        args.help = true;
        break;
      case '--version':
        args.version = true;
        break;
      case '--codex-home':
        args.codexHome = requireValue(argv, ++index, token);
        break;
      case '--json':
        args.json = true;
        break;
      case '--show-files':
        args.showFiles = true;
        break;
      case '--id':
        args.ids.push(requireValue(argv, ++index, token));
        break;
      case '--output':
        args.output = requireValue(argv, ++index, token);
        break;
      case '--name':
        args.name = requireValue(argv, ++index, token);
        break;
      case '--trash':
        args.trash = true;
        break;
      case '--yes':
        args.yes = true;
        break;
      case '--permanent':
        args.permanent = true;
        break;
      case '--all':
        args.all = true;
        break;
      case '--limit':
        args.limit = Number(requireValue(argv, ++index, token));
        if (!Number.isFinite(args.limit)) {
          throw new Error('Invalid value for --limit');
        }
        break;
      default:
        throw new Error(`Unknown argument: ${token}`);
    }
    index += 1;
  }

  return args;
}

async function requireSingleSession(
  store: CodexSessionsStore,
  args: ParsedArgs,
  location: 'active' | 'trash',
): Promise<SessionSummary> {
  if (args.ids.length !== 1) {
    throw new Error('This command requires exactly one --id value.');
  }
  const sessions = location === 'active' ? await store.buildSessionSummaries() : await store.buildTrashSummaries();
  const session = sessions.find((item) => item.sessionId === args.ids[0]);
  if (!session) {
    throw new Error(`Session not found: ${args.ids[0]}`);
  }
  return session;
}

function applySelection(sessions: SessionSummary[], args: ParsedArgs): SessionSummary[] {
  let filtered = sessions;
  if (args.ids.length > 0) {
    const allowedIds = new Set(args.ids);
    filtered = filtered.filter((session) => allowedIds.has(session.sessionId));
  }
  if (typeof args.limit === 'number' && args.limit >= 0) {
    filtered = filtered.slice(0, args.limit);
  }
  return filtered;
}

async function confirmIfNeeded(args: ParsedArgs, action: string, sessions: SessionSummary[]): Promise<void> {
  if (args.yes) {
    return;
  }
  const rl = readline.createInterface({ input, output });
  try {
    console.log(`Will ${action}:`);
    for (const session of sessions.slice(0, 10)) {
      console.log(`- ${session.sessionId} | ${session.threadName || '-'}`);
    }
    if (sessions.length > 10) {
      console.log(`...and ${sessions.length - 10} more session(s).`);
    }
    const answer = (await rl.question('Type yes to continue: ')).trim();
    if (answer !== 'yes') {
      throw new Error('Cancelled.');
    }
  } finally {
    rl.close();
  }
}

function printSessions(sessions: SessionSummary[], showFiles: boolean, includeDeletedAt: boolean): void {
  if (sessions.length === 0) {
    console.log('No matching sessions.');
    return;
  }

  const rows = sessions.map((session) => {
    const base = [
      session.primaryProject,
      formatDate(session.updatedAt),
      String(session.fileCount),
      formatSize(session.totalSize),
      session.primarySource,
      session.sessionId,
      session.threadName || '-',
    ];
    if (includeDeletedAt) {
      base.splice(2, 0, formatDate(session.deletedAt));
    }
    return base;
  });

  const headers = includeDeletedAt
    ? ['Project', 'Updated', 'Deleted', 'Files', 'Size', 'Source', 'Session ID', 'Thread']
    : ['Project', 'Updated', 'Files', 'Size', 'Source', 'Session ID', 'Thread'];
  const widths = headers.map((header, column) => Math.max(header.length, ...rows.map((row) => row[column]?.length ?? 0)));

  console.log(headers.map((header, column) => header.padEnd(widths[column])).join('  '));
  console.log(widths.map((width) => '-'.repeat(width)).join('  '));
  rows.forEach((row, rowIndex) => {
    console.log(row.map((value, column) => truncate(value, widths[column]).padEnd(widths[column])).join('  '));
    console.log(`    CWD: ${sessions[rowIndex].primaryCwd}`);
    if (showFiles) {
      for (const rolloutPath of [...sessions[rowIndex].rolloutPaths].sort()) {
        console.log(`    File: ${rolloutPath}`);
      }
    }
  });
}

function printProjects(stats: Array<[string, number]>): void {
  if (stats.length === 0) {
    console.log('No projects to display.');
    return;
  }
  const projectWidth = Math.max('Project'.length, ...stats.map(([project]) => project.length));
  const countWidth = Math.max('Sessions'.length, ...stats.map(([, count]) => String(count).length));
  console.log(`Project`.padEnd(projectWidth) + '  ' + `Sessions`.padEnd(countWidth));
  console.log('-'.repeat(projectWidth) + '  ' + '-'.repeat(countWidth));
  for (const [project, count] of stats) {
    console.log(`${truncate(project, projectWidth).padEnd(projectWidth)}  ${String(count).padEnd(countWidth)}`);
  }
}

function printJson(value: unknown): void {
  console.log(JSON.stringify(value, null, 2));
}

function printHelp(): void {
  console.log(`manage-codex-sessions-ts\n\nCommands:\n  query [--json] [--show-files] [--id <session-id>] [--limit <n>]\n  trash [--json] [--show-files] [--id <session-id>] [--limit <n>]\n  projects [--json] [--trash] [--id <session-id>] [--limit <n>]\n  export --id <session-id> [--output <path>] [--trash]\n  rename --id <session-id> --name <new-name> [--trash]\n  delete --id <session-id> [--yes] [--permanent]\n  delete-all [--yes] [--permanent]\n  restore (--all | --id <session-id>) [--yes]\n  empty-trash (--all | --id <session-id>) [--yes]\n\nGlobal options:\n  --codex-home <path>\n  --help\n  --version`);
}

function requireValue(argv: string[], index: number, option: string): string {
  const value = argv[index];
  if (!value || value.startsWith('-')) {
    throw new Error(`Missing value for ${option}`);
  }
  return value;
}

function readPackageVersion(): string {
  const packageJsonPath = path.resolve(__dirname, '..', 'package.json');
  const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8')) as { version?: string };
  return packageJson.version || '0.0.0';
}

function formatDate(value: Date | null): string {
  return value ? value.toISOString() : '-';
}

function formatSize(value: number): string {
  if (value < 1024) {
    return `${value}B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)}KB`;
  }
  return `${(value / 1024 / 1024).toFixed(1)}MB`;
}

function truncate(value: string, width: number): string {
  return value.length <= width ? value : `${value.slice(0, Math.max(0, width - 1))}…`;
}

main().then(
  (code) => {
    process.exitCode = code;
  },
  (error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  },
);
