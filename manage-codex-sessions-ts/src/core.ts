
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

export interface SessionIndexEntry {
  sessionId: string;
  threadName: string;
  updatedAt: Date | null;
  raw: Record<string, unknown>;
}

export interface SessionRollout {
  path: string;
  bytesSize: number;
  timestamp: Date | null;
  cwd: string | null;
  source: string | null;
  cliVersion: string | null;
  workspaceRoots: string[];
}

export interface DeleteResult {
  sessionCount: number;
  deletedFileCount: number;
  removedIndexEntryCount: number;
}

export interface RestoreResult {
  restoredSessionCount: number;
  restoredFileCount: number;
  restoredIndexEntryCount: number;
  skippedSessionIds: string[];
}

export interface PurgeResult {
  sessionCount: number;
  deletedFileCount: number;
}

export interface TranscriptMessage {
  messageId: string;
  role: string;
  timestampText: string;
  timestamp: Date | null;
  ordinal: number;
  text: string;
}

export class SessionSummary {
  public threadName: string | null = null;
  public updatedAt: Date | null = null;
  public fileCount = 0;
  public totalSize = 0;
  public readonly cwdValues = new Set<string>();
  public readonly sourceValues = new Set<string>();
  public readonly cliVersions = new Set<string>();
  public readonly workspaceRootsValues = new Set<string>();
  public readonly projectValues = new Set<string>();
  public rolloutPaths: string[] = [];
  public indexEntriesRaw: Array<Record<string, unknown>> = [];
  public firstRolloutAt: Date | null = null;
  public lastRolloutAt: Date | null = null;
  public deletedAt: Date | null = null;

  public constructor(public sessionId: string) {}

  public addIndexEntry(entry: SessionIndexEntry): void {
    this.indexEntriesRaw.push({ ...entry.raw });
    if (entry.threadName && !this.threadName) {
      this.threadName = entry.threadName;
    }
    if (entry.updatedAt && (!this.updatedAt || entry.updatedAt > this.updatedAt)) {
      this.updatedAt = entry.updatedAt;
    }
  }

  public addRollout(rollout: SessionRollout): void {
    this.fileCount += 1;
    this.totalSize += rollout.bytesSize;
    this.rolloutPaths.push(rollout.path);
    if (rollout.cwd) {
      this.cwdValues.add(rollout.cwd);
    }
    if (rollout.source) {
      this.sourceValues.add(rollout.source);
    }
    if (rollout.cliVersion) {
      this.cliVersions.add(rollout.cliVersion);
    }
    if (rollout.workspaceRoots.length > 0) {
      for (const workspaceRoot of rollout.workspaceRoots) {
        this.workspaceRootsValues.add(workspaceRoot);
        this.projectValues.add(workspaceRoot);
      }
    } else if (rollout.cwd) {
      this.projectValues.add(rollout.cwd);
    }
    if (!rollout.timestamp) {
      return;
    }
    if (!this.firstRolloutAt || rollout.timestamp < this.firstRolloutAt) {
      this.firstRolloutAt = rollout.timestamp;
    }
    if (!this.lastRolloutAt || rollout.timestamp > this.lastRolloutAt) {
      this.lastRolloutAt = rollout.timestamp;
    }
    if (!this.updatedAt || rollout.timestamp > this.updatedAt) {
      this.updatedAt = rollout.timestamp;
    }
  }

  public get primaryCwd(): string {
    return firstSortedValue(this.cwdValues) ?? '-';
  }

  public get primarySource(): string {
    return firstSortedValue(this.sourceValues) ?? '-';
  }

  public get primaryProject(): string {
    return firstSortedValue(this.projectValues) ?? firstSortedValue(this.cwdValues) ?? '-';
  }

  public toRecord(includePaths = false): Record<string, unknown> {
    const data: Record<string, unknown> = {
      id: this.sessionId,
      thread_name: this.threadName,
      updated_at: isoformatOrNull(this.updatedAt),
      file_count: this.fileCount,
      total_size: this.totalSize,
      cwd_values: sortValues(this.cwdValues),
      source_values: sortValues(this.sourceValues),
      cli_versions: sortValues(this.cliVersions),
      workspace_roots_values: sortValues(this.workspaceRootsValues),
      project_values: sortValues(this.projectValues),
      first_rollout_at: isoformatOrNull(this.firstRolloutAt),
      last_rollout_at: isoformatOrNull(this.lastRolloutAt),
      deleted_at: isoformatOrNull(this.deletedAt),
    };
    if (includePaths) {
      data.rollout_paths = [...this.rolloutPaths].sort();
    }
    return data;
  }
}

export class CodexSessionsStore {
  public readonly codexHome: string;

  public constructor(codexHome?: string) {
    this.codexHome = resolveCodexHome(codexHome);
  }

  public async buildSessionSummaries(): Promise<SessionSummary[]> {
    const indexEntries = await readIndexEntries(path.join(this.codexHome, 'session_index.jsonl'));
    const rollouts = await scanRollouts(activeSessionsDir(this.codexHome));
    const summaries = new Map<string, SessionSummary>();

    for (const entry of indexEntries) {
      const summary = summaries.get(entry.sessionId) ?? new SessionSummary(entry.sessionId);
      summary.addIndexEntry(entry);
      summaries.set(entry.sessionId, summary);
    }

    for (const [sessionId, files] of rollouts.entries()) {
      const summary = summaries.get(sessionId) ?? new SessionSummary(sessionId);
      for (const rollout of files) {
        summary.addRollout(rollout);
      }
      summaries.set(sessionId, summary);
    }

    return [...summaries.values()].sort((left, right) => compareActiveSessions(left, right));
  }

  public async buildTrashSummaries(): Promise<SessionSummary[]> {
    const records = await this.loadTrashRecords();
    const summaries: SessionSummary[] = [];
    const baseDir = trashSessionsDir(this.codexHome);

    for (const record of records) {
      const sessionSnapshot = record.session;
      const sessionId = stringifyMetadata(record.id);
      if (!isPlainObject(sessionSnapshot) || !sessionId) {
        continue;
      }
      const rolloutPaths = normalizeStringList(asArray(record.rollout_paths)).map((relativePath) =>
        path.join(baseDir, relativePath),
      );
      const summary = buildSessionFromSnapshot(sessionSnapshot, {
        deletedAt: parseIso8601(record.deleted_at),
        indexEntriesRaw: Array.isArray(record.index_entries)
          ? record.index_entries.filter(isPlainObject).map((entry) => ({ ...entry }))
          : undefined,
        rolloutPaths,
      });
      if (!summary.sessionId) {
        summary.sessionId = sessionId;
      }
      summaries.push(summary);
    }

    return summaries.sort((left, right) => compareTrashSessions(left, right));
  }

  public async buildProjectStats(summaries: Iterable<SessionSummary>): Promise<Array<[string, number]>> {
    const counts = new Map<string, number>();
    for (const summary of summaries) {
      const project = summary.primaryProject;
      counts.set(project, (counts.get(project) ?? 0) + 1);
    }
    return [...counts.entries()].sort((left, right) => {
      const countDiff = right[1] - left[1];
      return countDiff !== 0 ? countDiff : left[0].localeCompare(right[0]);
    });
  }

  public async buildSessionMarkdown(session: SessionSummary): Promise<string> {
    const transcriptMessages = await collectSessionTranscriptMessages(session);
    const title = session.threadName || session.sessionId;
    const lines = [
      `# ${title}`,
      '',
      `- Session ID: \`${session.sessionId}\``,
      `- Thread: ${session.threadName || '-'}`,
      `- Updated: ${formatTimestamp(session.updatedAt)}`,
      `- First Rollout: ${formatTimestamp(session.firstRolloutAt)}`,
      `- Last Rollout: ${formatTimestamp(session.lastRolloutAt)}`,
      `- Project: \`${session.primaryProject}\``,
      `- CWD: \`${session.primaryCwd}\``,
      `- Source: \`${session.primarySource}\``,
      `- Rollout Files: ${session.fileCount}`,
      `- Total Size: ${formatBytes(session.totalSize)}`,
    ];
    if (session.deletedAt) {
      lines.push(`- Deleted: ${formatTimestamp(session.deletedAt)}`);
    }
    if (session.cliVersions.size > 0) {
      lines.push(`- CLI Versions: ${sortValues(session.cliVersions).map((value) => `\`${value}\``).join(', ')}`);
    }
    if (session.workspaceRootsValues.size > 0) {
      lines.push(
        `- Workspace Roots: ${sortValues(session.workspaceRootsValues)
          .map((value) => `\`${value}\``)
          .join(', ')}`,
      );
    }

    lines.push('', '## Transcript', '');
    if (transcriptMessages.length === 0) {
      lines.push('_No exportable user/assistant messages were found in the rollout files._');
    } else {
      for (const message of transcriptMessages) {
        let heading = capitalize(message.role);
        if (message.timestamp) {
          heading = `${heading} - ${formatTimestamp(message.timestamp)}`;
        }
        lines.push(`### ${heading}`, '', message.text.trimEnd(), '');
      }
    }

    lines.push('## Rollout Files', '');
    if (session.rolloutPaths.length > 0) {
      for (const rolloutPath of [...session.rolloutPaths].sort()) {
        lines.push(`- \`${rolloutPath}\``);
      }
    } else {
      lines.push('- _No rollout files found._');
    }

    return `${lines.join('\n').trimEnd()}\n`;
  }

  public async exportSessionMarkdown(session: SessionSummary, outputPath?: string): Promise<string> {
    const destination = await resolveSessionMarkdownOutputPath(session, outputPath);
    await ensureParentDir(destination);
    await fs.promises.writeFile(destination, await this.buildSessionMarkdown(session), 'utf8');
    return destination;
  }

  public async moveSessionsToTrash(sessions: SessionSummary[]): Promise<DeleteResult> {
    const deletedIds = new Set(sessions.map((session) => session.sessionId));
    const indexPath = path.join(this.codexHome, 'session_index.jsonl');
    const trashRecords = new Map<string, Record<string, unknown>>();
    for (const record of await this.loadTrashRecords()) {
      const sessionId = stringifyMetadata(record.id);
      if (sessionId) {
        trashRecords.set(sessionId, record);
      }
    }
    const relativeRollouts = collectRelativeRolloutPaths(this.codexHome, sessions);
    const activeDir = activeSessionsDir(this.codexHome);
    const recycleDir = trashSessionsDir(this.codexHome);
    const now = new Date().toISOString();
    let movedFiles = 0;

    for (const session of sessions) {
      const storedRelativePaths: string[] = [];
      for (const relativePath of relativeRollouts.get(session.sessionId) ?? []) {
        const sourcePath = path.join(activeDir, relativePath);
        const destinationPath = path.join(recycleDir, relativePath);
        if (!(await exists(sourcePath))) {
          continue;
        }
        await ensureParentDir(destinationPath);
        if (await exists(destinationPath)) {
          await fs.promises.unlink(destinationPath);
        }
        await fs.promises.rename(sourcePath, destinationPath);
        storedRelativePaths.push(toPosixPath(relativePath));
        movedFiles += 1;
        await pruneEmptyDirs(path.dirname(sourcePath), activeDir);
      }

      trashRecords.set(session.sessionId, {
        id: session.sessionId,
        deleted_at: now,
        session: session.toRecord(false),
        index_entries: session.indexEntriesRaw,
        rollout_paths: storedRelativePaths,
      });
    }

    await this.saveTrashRecords([...trashRecords.values()]);
    const removedIndexEntries = await rewriteIndex(indexPath, deletedIds);
    return {
      sessionCount: deletedIds.size,
      deletedFileCount: movedFiles,
      removedIndexEntryCount: removedIndexEntries,
    };
  }

  public async deleteActiveSessionsForever(sessions: SessionSummary[]): Promise<DeleteResult> {
    const deletedIds = new Set(sessions.map((session) => session.sessionId));
    const activeDir = activeSessionsDir(this.codexHome);
    let deletedFiles = 0;

    for (const session of sessions) {
      for (const rolloutPath of session.rolloutPaths) {
        if (!(await exists(rolloutPath))) {
          continue;
        }
        await fs.promises.unlink(rolloutPath);
        deletedFiles += 1;
        await pruneEmptyDirs(path.dirname(rolloutPath), activeDir);
      }
    }

    const removedIndexEntries = await rewriteIndex(path.join(this.codexHome, 'session_index.jsonl'), deletedIds);
    return {
      sessionCount: deletedIds.size,
      deletedFileCount: deletedFiles,
      removedIndexEntryCount: removedIndexEntries,
    };
  }

  public async deleteSessions(sessions: SessionSummary[], permanent = false): Promise<DeleteResult> {
    return permanent ? this.deleteActiveSessionsForever(sessions) : this.moveSessionsToTrash(sessions);
  }

  public async restoreSessionsFromTrash(sessions: SessionSummary[]): Promise<RestoreResult> {
    const records = await this.loadTrashRecords();
    const recordMap = new Map<string, Record<string, unknown>>();
    for (const record of records) {
      const sessionId = stringifyMetadata(record.id);
      if (sessionId) {
        recordMap.set(sessionId, record);
      }
    }

    const activeEntries = await readIndexEntries(path.join(this.codexHome, 'session_index.jsonl'));
    const activeIds = new Set(activeEntries.map((entry) => entry.sessionId));
    const activeDir = activeSessionsDir(this.codexHome);
    const recycleDir = trashSessionsDir(this.codexHome);
    const restoredIds = new Set<string>();
    const skippedSessionIds: string[] = [];
    let restoredFiles = 0;
    let restoredIndexEntries = 0;
    let restoredSessions = 0;

    for (const session of sessions) {
      const sessionId = session.sessionId;
      const record = recordMap.get(sessionId);
      if (!record || activeIds.has(sessionId)) {
        skippedSessionIds.push(sessionId);
        continue;
      }

      const relativePaths = normalizeStringList(asArray(record.rollout_paths));
      const hasConflict = relativePaths.some((relativePath) => pathExists(path.join(activeDir, relativePath)));
      if (hasConflict) {
        skippedSessionIds.push(sessionId);
        continue;
      }

      let indexEntries = Array.isArray(record.index_entries)
        ? record.index_entries.filter(isPlainObject).map((entry) => ({ ...entry }))
        : [];
      if (indexEntries.length === 0) {
        const snapshot = isPlainObject(record.session) ? record.session : {};
        indexEntries = [
          {
            id: sessionId,
            thread_name: snapshot.thread_name ?? '',
            updated_at: snapshot.updated_at ?? null,
          },
        ];
      }
      restoredIndexEntries += await appendIndexEntries(path.join(this.codexHome, 'session_index.jsonl'), indexEntries);

      for (const relativePath of relativePaths) {
        const sourcePath = path.join(recycleDir, relativePath);
        const destinationPath = path.join(activeDir, relativePath);
        if (!(await exists(sourcePath))) {
          continue;
        }
        await ensureParentDir(destinationPath);
        await fs.promises.rename(sourcePath, destinationPath);
        restoredFiles += 1;
        await pruneEmptyDirs(path.dirname(sourcePath), recycleDir);
      }

      restoredSessions += 1;
      restoredIds.add(sessionId);
      activeIds.add(sessionId);
    }

    await this.saveTrashRecords(records.filter((record) => !restoredIds.has(stringifyMetadata(record.id) ?? '')));
    return {
      restoredSessionCount: restoredSessions,
      restoredFileCount: restoredFiles,
      restoredIndexEntryCount: restoredIndexEntries,
      skippedSessionIds,
    };
  }

  public async purgeTrashedSessions(sessions: SessionSummary[]): Promise<PurgeResult> {
    const records = await this.loadTrashRecords();
    const purgeIds = new Set(sessions.map((session) => session.sessionId));
    const recycleDir = trashSessionsDir(this.codexHome);
    const remaining: Array<Record<string, unknown>> = [];
    let deletedFiles = 0;

    for (const record of records) {
      const sessionId = stringifyMetadata(record.id);
      if (!sessionId || !purgeIds.has(sessionId)) {
        remaining.push(record);
        continue;
      }
      for (const relativePath of normalizeStringList(asArray(record.rollout_paths))) {
        const rolloutPath = path.join(recycleDir, relativePath);
        if (!(await exists(rolloutPath))) {
          continue;
        }
        await fs.promises.unlink(rolloutPath);
        deletedFiles += 1;
        await pruneEmptyDirs(path.dirname(rolloutPath), recycleDir);
      }
    }

    await this.saveTrashRecords(remaining);
    return {
      sessionCount: purgeIds.size,
      deletedFileCount: deletedFiles,
    };
  }

  public async renameSession(sessionId: string, newName: string, inTrash = false): Promise<number> {
    return inTrash
      ? this.renameTrashedSession(sessionId, newName)
      : renameSessionInIndex(path.join(this.codexHome, 'session_index.jsonl'), sessionId, newName);
  }

  public async loadTrashRecords(): Promise<Array<Record<string, unknown>>> {
    return readJsonlRecords(trashManifestPath(this.codexHome));
  }

  public async saveTrashRecords(records: Array<Record<string, unknown>>): Promise<void> {
    const manifestPath = trashManifestPath(this.codexHome);
    if (records.length > 0) {
      await writeJsonlRecords(manifestPath, records);
      return;
    }
    if (await exists(manifestPath)) {
      await fs.promises.unlink(manifestPath);
    }
  }

  private async renameTrashedSession(sessionId: string, newName: string): Promise<number> {
    const records = await this.loadTrashRecords();
    let changed = 0;
    for (const record of records) {
      if (stringifyMetadata(record.id) !== sessionId) {
        continue;
      }
      if (isPlainObject(record.session)) {
        record.session.thread_name = newName;
      }
      if (Array.isArray(record.index_entries)) {
        for (const entry of record.index_entries) {
          if (isPlainObject(entry)) {
            entry.thread_name = newName;
          }
        }
      }
      changed += 1;
    }
    if (changed > 0) {
      await this.saveTrashRecords(records);
    }
    return changed;
  }
}

export function formatDeleteSummary(result: DeleteResult, movedToTrash: boolean): string {
  const action = movedToTrash ? 'Moved to trash' : 'Permanently deleted';
  return `${action} ${result.sessionCount} session(s), ${result.deletedFileCount} rollout file(s), and ${result.removedIndexEntryCount} index record(s).`;
}

export function formatRestoreSummary(result: RestoreResult): string {
  const suffix =
    result.skippedSessionIds.length > 0
      ? ` Skipped ${result.skippedSessionIds.length} session(s): ${result.skippedSessionIds.join(', ')}.`
      : '';
  return `Restored ${result.restoredSessionCount} session(s), ${result.restoredFileCount} rollout file(s), and ${result.restoredIndexEntryCount} index record(s).${suffix}`;
}

export function formatPurgeSummary(result: PurgeResult): string {
  return `Permanently deleted ${result.sessionCount} trashed session(s) and ${result.deletedFileCount} rollout file(s).`;
}

export function defaultCodexHome(): string {
  const configured = process.env.CODEX_HOME?.trim();
  return configured ? path.resolve(expandHome(configured)) : path.join(os.homedir(), '.codex');
}

export function resolveCodexHome(codexHome?: string): string {
  return codexHome?.trim() ? path.resolve(expandHome(codexHome.trim())) : defaultCodexHome();
}

export function sanitizeFilenameComponent(value: string): string {
  const collapsed = value.trim().split(/\s+/).join('_');
  const safe = [...collapsed].map((character) => (/[\p{L}\p{N}\-_.()]/u.test(character) ? character : '_')).join('');
  const trimmed = safe.replace(/^[._]+|[._]+$/g, '').slice(0, 80);
  return trimmed || 'session';
}

export function defaultSessionMarkdownFilename(session: SessionSummary): string {
  let label = sanitizeFilenameComponent(session.threadName || session.sessionId);
  const sessionToken = sanitizeFilenameComponent(session.sessionId);
  if (label !== sessionToken) {
    label = `${label}-${sessionToken}`;
  }
  return `${label}.md`;
}

export async function resolveSessionMarkdownOutputPath(session: SessionSummary, outputPath?: string): Promise<string> {
  if (!outputPath) {
    return path.join(process.cwd(), defaultSessionMarkdownFilename(session));
  }
  const resolved = path.resolve(expandHome(outputPath));
  if ((await exists(resolved)) && (await fs.promises.stat(resolved)).isDirectory()) {
    return path.join(resolved, defaultSessionMarkdownFilename(session));
  }
  if (outputPath.endsWith('/') || outputPath.endsWith('\\')) {
    return path.join(resolved, defaultSessionMarkdownFilename(session));
  }
  return resolved;
}

async function readIndexEntries(indexPath: string): Promise<SessionIndexEntry[]> {
  const records = await readJsonlRecords(indexPath);
  const entries: SessionIndexEntry[] = [];
  for (const record of records) {
    const sessionId = record.id;
    if (!sessionId) {
      continue;
    }
    entries.push({
      sessionId: String(sessionId),
      threadName: String(record.thread_name ?? ''),
      updatedAt: parseIso8601(record.updated_at),
      raw: { ...record },
    });
  }
  return entries;
}

async function readJsonlRecords(filePath: string): Promise<Array<Record<string, unknown>>> {
  if (!(await exists(filePath))) {
    return [];
  }
  const text = await fs.promises.readFile(filePath, 'utf8');
  const records: Array<Record<string, unknown>> = [];
  for (const [index, line] of text.split(/\r?\n/).entries()) {
    const rawLine = line.trim();
    if (!rawLine) {
      continue;
    }
    let data: unknown;
    try {
      data = JSON.parse(rawLine);
    } catch (error) {
      throw new Error(`failed to parse ${filePath} line ${index + 1}: ${String(error)}`);
    }
    if (isPlainObject(data)) {
      records.push(data);
    }
  }
  return records;
}

async function writeJsonlRecords(filePath: string, records: Iterable<Record<string, unknown>>): Promise<void> {
  await ensureParentDir(filePath);
  const content = [...records].map((record) => JSON.stringify(sortObjectKeys(record))).join('\n');
  await fs.promises.writeFile(filePath, content ? `${content}\n` : '', 'utf8');
}

async function readFirstJsonLine(filePath: string): Promise<Record<string, unknown> | null> {
  const text = await fs.promises.readFile(filePath, 'utf8');
  const firstLine = text.split(/\r?\n/, 1)[0]?.trim() ?? '';
  if (!firstLine) {
    return null;
  }
  const data = JSON.parse(firstLine);
  return isPlainObject(data) ? data : null;
}

async function scanRollouts(sessionsDir: string): Promise<Map<string, SessionRollout[]>> {
  const grouped = new Map<string, SessionRollout[]>();
  if (!(await exists(sessionsDir))) {
    return grouped;
  }

  for (const rolloutPath of await listJsonlFiles(sessionsDir)) {
    let firstRecord: Record<string, unknown> | null;
    try {
      firstRecord = await readFirstJsonLine(rolloutPath);
    } catch {
      continue;
    }
    if (!firstRecord || !isPlainObject(firstRecord.payload)) {
      continue;
    }
    const payload = firstRecord.payload;
    const sessionId = payload.session_id ?? payload.id;
    if (!sessionId) {
      continue;
    }
    const workspaceRootsRaw = payload.runtime_workspace_roots ?? payload.workspace_roots ?? [];
    const workspaceRoots = normalizeStringList(Array.isArray(workspaceRootsRaw) ? workspaceRootsRaw : [workspaceRootsRaw]);
    const stat = await fs.promises.stat(rolloutPath);
    const items = grouped.get(String(sessionId)) ?? [];
    items.push({
      path: rolloutPath,
      bytesSize: stat.size,
      timestamp: parseIso8601(payload.timestamp ?? firstRecord.timestamp),
      cwd: stringifyMetadata(payload.cwd),
      source: stringifyMetadata(payload.source),
      cliVersion: stringifyMetadata(payload.cli_version),
      workspaceRoots,
    });
    grouped.set(String(sessionId), items);
  }

  return grouped;
}

async function listJsonlFiles(rootDir: string): Promise<string[]> {
  const files: string[] = [];
  if (!(await exists(rootDir))) {
    return files;
  }
  const stack = [rootDir];
  while (stack.length > 0) {
    const current = stack.pop()!;
    const entries = await fs.promises.readdir(current, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(fullPath);
      } else if (entry.isFile() && fullPath.endsWith('.jsonl')) {
        files.push(fullPath);
      }
    }
  }
  return files;
}

function buildSessionFromSnapshot(
  snapshot: Record<string, unknown>,
  options: {
    deletedAt?: Date | null;
    indexEntriesRaw?: Array<Record<string, unknown>>;
    rolloutPaths?: string[];
  } = {},
): SessionSummary {
  const summary = new SessionSummary(String(snapshot.id ?? ''));
  summary.threadName = stringifyMetadata(snapshot.thread_name);
  summary.updatedAt = parseIso8601(snapshot.updated_at);
  summary.fileCount = Number(snapshot.file_count ?? 0) || 0;
  summary.totalSize = Number(snapshot.total_size ?? 0) || 0;
  summary.deletedAt = options.deletedAt ?? parseIso8601(snapshot.deleted_at);
  addValues(summary.cwdValues, normalizeStringList(asArray(snapshot.cwd_values)));
  addValues(summary.sourceValues, normalizeStringList(asArray(snapshot.source_values)));
  addValues(summary.cliVersions, normalizeStringList(asArray(snapshot.cli_versions)));
  addValues(summary.workspaceRootsValues, normalizeStringList(asArray(snapshot.workspace_roots_values)));
  addValues(summary.projectValues, normalizeStringList(asArray(snapshot.project_values)));
  summary.firstRolloutAt = parseIso8601(snapshot.first_rollout_at);
  summary.lastRolloutAt = parseIso8601(snapshot.last_rollout_at);
  if (summary.projectValues.size === 0) {
    if (summary.workspaceRootsValues.size > 0) {
      addValues(summary.projectValues, summary.workspaceRootsValues);
    } else if (summary.cwdValues.size > 0) {
      summary.projectValues.add(summary.primaryCwd);
    }
  }
  if (options.rolloutPaths) {
    summary.rolloutPaths = [...options.rolloutPaths];
    if (summary.fileCount === 0) {
      summary.fileCount = options.rolloutPaths.length;
    }
  }
  if (options.indexEntriesRaw) {
    summary.indexEntriesRaw = options.indexEntriesRaw.map((item) => ({ ...item }));
  }
  return summary;
}

async function collectSessionTranscriptMessages(session: SessionSummary): Promise<TranscriptMessage[]> {
  const messages: TranscriptMessage[] = [];
  const seenMessageIds = new Set<string>();
  for (const rolloutPath of [...session.rolloutPaths].sort()) {
    let records: Array<Record<string, unknown>>;
    try {
      records = await readJsonlRecords(rolloutPath);
    } catch {
      continue;
    }
    records.forEach((record, sequence) => {
      if (record.type !== 'response_item' || !isPlainObject(record.payload) || record.payload.type !== 'message') {
        return;
      }
      const payload = record.payload;
      const role = stringifyMetadata(payload.role) ?? '';
      if (role !== 'user' && role !== 'assistant') {
        return;
      }
      const messageId = stringifyMetadata(payload.id) ?? `${rolloutPath}:${sequence}`;
      if (seenMessageIds.has(messageId)) {
        return;
      }
      const content = Array.isArray(payload.content) ? payload.content : [payload.content];
      const rendered = renderTranscriptContentItems(content);
      if (!rendered) {
        return;
      }
      seenMessageIds.add(messageId);
      messages.push({
        messageId,
        role,
        timestampText: String(record.timestamp ?? ''),
        timestamp: parseIso8601(record.timestamp),
        ordinal: Number(record.ordinal ?? sequence) || sequence,
        text: rendered,
      });
    });
  }
  return messages.sort((left, right) => {
    const timeCompare = left.timestampText.localeCompare(right.timestampText);
    if (timeCompare !== 0) {
      return timeCompare;
    }
    const ordinalCompare = left.ordinal - right.ordinal;
    return ordinalCompare !== 0 ? ordinalCompare : left.messageId.localeCompare(right.messageId);
  });
}

function renderTranscriptContentItems(items: Iterable<unknown>): string {
  const parts: string[] = [];
  for (const item of items) {
    if (!isPlainObject(item)) {
      continue;
    }
    const itemType = String(item.type ?? '');
    const text = item.text;
    if (typeof text === 'string' && ['input_text', 'output_text', 'text', 'Text'].includes(itemType)) {
      const stripped = text.trim();
      if (stripped) {
        parts.push(stripped);
      }
      continue;
    }
    const location = typeof item.path === 'string' ? item.path : typeof item.image_url === 'string' ? item.image_url : typeof item.audio_url === 'string' ? item.audio_url : null;
    if (location) {
      parts.push(`[${itemType || 'attachment'}: ${location}]`);
      continue;
    }
    const rendered = stringifyMetadata(item);
    if (rendered) {
      parts.push(itemType ? `[${itemType}] ${rendered}` : rendered);
    }
  }
  return parts.join('\n\n').trim();
}

async function rewriteIndex(indexPath: string, deletedIds: Set<string>): Promise<number> {
  if (!(await exists(indexPath))) {
    return 0;
  }
  let removedCount = 0;
  const kept: Array<Record<string, unknown>> = [];
  for (const record of await readJsonlRecords(indexPath)) {
    if (deletedIds.has(stringifyMetadata(record.id) ?? '')) {
      removedCount += 1;
      continue;
    }
    kept.push(record);
  }
  await writeJsonlRecords(indexPath, kept);
  return removedCount;
}

async function appendIndexEntries(indexPath: string, entries: Array<Record<string, unknown>>): Promise<number> {
  const records = await readJsonlRecords(indexPath);
  const existingIds = new Set(records.map((record) => stringifyMetadata(record.id) ?? '').filter(Boolean));
  let appended = 0;
  for (const entry of entries) {
    const sessionId = stringifyMetadata(entry.id);
    if (!sessionId || existingIds.has(sessionId)) {
      continue;
    }
    records.push(entry);
    existingIds.add(sessionId);
    appended += 1;
  }
  await writeJsonlRecords(indexPath, records);
  return appended;
}

async function renameSessionInIndex(indexPath: string, sessionId: string, newName: string): Promise<number> {
  const records = await readJsonlRecords(indexPath);
  let changed = 0;
  for (const record of records) {
    if (stringifyMetadata(record.id) !== sessionId) {
      continue;
    }
    record.thread_name = newName;
    changed += 1;
  }
  if (changed > 0) {
    await writeJsonlRecords(indexPath, records);
  }
  return changed;
}

async function pruneEmptyDirs(startPath: string, stopAt: string): Promise<void> {
  let current = path.resolve(startPath);
  const stop = path.resolve(stopAt);
  while (current !== stop && isSubpath(current, stop)) {
    try {
      await fs.promises.rmdir(current);
    } catch {
      break;
    }
    current = path.dirname(current);
  }
}

function collectRelativeRolloutPaths(codexHome: string, sessions: SessionSummary[]): Map<string, string[]> {
  const baseDir = activeSessionsDir(codexHome);
  const grouped = new Map<string, string[]>();
  for (const session of sessions) {
    const relativePaths: string[] = [];
    for (const rolloutPath of session.rolloutPaths) {
      const relativePath = path.relative(baseDir, rolloutPath);
      if (!relativePath || relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
        continue;
      }
      relativePaths.push(relativePath);
    }
    grouped.set(session.sessionId, relativePaths);
  }
  return grouped;
}

function activeSessionsDir(codexHome: string): string {
  return path.join(codexHome, 'sessions');
}

function trashRootDir(codexHome: string): string {
  return path.join(codexHome, 'session_trash');
}

function trashSessionsDir(codexHome: string): string {
  return path.join(trashRootDir(codexHome), 'sessions');
}

function trashManifestPath(codexHome: string): string {
  return path.join(trashRootDir(codexHome), 'manifest.jsonl');
}

function parseIso8601(value: unknown): Date | null {
  if (typeof value !== 'string' || !value) {
    return null;
  }
  const parsed = new Date(value.replace('Z', '+00:00'));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function isoformatOrNull(value: Date | null): string | null {
  return value ? value.toISOString() : null;
}

function formatTimestamp(value: Date | null): string {
  if (!value) {
    return '-';
  }
  const local = new Date(value.getTime());
  const offsetMinutes = -local.getTimezoneOffset();
  const sign = offsetMinutes >= 0 ? '+' : '-';
  const absoluteOffset = Math.abs(offsetMinutes);
  const offsetHours = padNumber(Math.floor(absoluteOffset / 60));
  const offsetRemainder = padNumber(absoluteOffset % 60);
  return `${local.getFullYear()}-${padNumber(local.getMonth() + 1)}-${padNumber(local.getDate())} ${padNumber(local.getHours())}:${padNumber(local.getMinutes())}:${padNumber(local.getSeconds())} ${sign}${offsetHours}${offsetRemainder}`;
}

function formatBytes(size: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = size;
  for (const unit of units) {
    if (value < 1024 || unit === units[units.length - 1]) {
      return unit === 'B' ? `${Math.trunc(value)}${unit}` : `${value.toFixed(1)}${unit}`;
    }
    value /= 1024;
  }
  return `${size}B`;
}

function stringifyMetadata(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === 'string') {
    return value;
  }
  return JSON.stringify(sortObjectKeys(value));
}

function normalizeStringList(values: Iterable<unknown>): string[] {
  const normalized: string[] = [];
  for (const value of values) {
    const rendered = stringifyMetadata(value);
    if (rendered) {
      normalized.push(rendered);
    }
  }
  return normalized;
}

function sortObjectKeys(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sortObjectKeys(item));
  }
  if (isPlainObject(value)) {
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(value).sort()) {
      sorted[key] = sortObjectKeys(value[key]);
    }
    return sorted;
  }
  return value;
}

async function ensureParentDir(filePath: string): Promise<void> {
  await fs.promises.mkdir(path.dirname(filePath), { recursive: true });
}

function firstSortedValue(values: Iterable<string>): string | undefined {
  return [...values].sort()[0];
}

function sortValues(values: Iterable<string>): string[] {
  return [...values].sort();
}

function addValues(target: Set<string>, values: Iterable<string>): void {
  for (const value of values) {
    target.add(value);
  }
}

function compareActiveSessions(left: SessionSummary, right: SessionSummary): number {
  const updatedCompare = compareDatesDesc(left.updatedAt, right.updatedAt);
  return updatedCompare !== 0 ? updatedCompare : right.sessionId.localeCompare(left.sessionId);
}

function compareTrashSessions(left: SessionSummary, right: SessionSummary): number {
  const deletedCompare = compareDatesDesc(left.deletedAt, right.deletedAt);
  if (deletedCompare !== 0) {
    return deletedCompare;
  }
  const updatedCompare = compareDatesDesc(left.updatedAt, right.updatedAt);
  return updatedCompare !== 0 ? updatedCompare : right.sessionId.localeCompare(left.sessionId);
}

function compareDatesDesc(left: Date | null, right: Date | null): number {
  return (right?.getTime() ?? Number.MIN_SAFE_INTEGER) - (left?.getTime() ?? Number.MIN_SAFE_INTEGER);
}

function isPlainObject(value: unknown): value is Record<string, any> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

async function exists(filePath: string): Promise<boolean> {
  try {
    await fs.promises.access(filePath);
    return true;
  } catch {
    return false;
  }
}

function pathExists(filePath: string): boolean {
  return fs.existsSync(filePath);
}

function isSubpath(targetPath: string, basePath: string): boolean {
  const relativePath = path.relative(basePath, targetPath);
  return relativePath !== '' && !relativePath.startsWith('..') && !path.isAbsolute(relativePath);
}

function expandHome(value: string): string {
  if (value === '~') {
    return os.homedir();
  }
  if (value.startsWith(`~${path.sep}`) || value.startsWith('~/') || value.startsWith('~\\')) {
    return path.join(os.homedir(), value.slice(2));
  }
  return value;
}

function toPosixPath(value: string): string {
  return value.split(path.sep).join('/');
}

function padNumber(value: number): string {
  return String(value).padStart(2, '0');
}

function capitalize(value: string): string {
  return value ? `${value[0].toUpperCase()}${value.slice(1)}` : value;
}
