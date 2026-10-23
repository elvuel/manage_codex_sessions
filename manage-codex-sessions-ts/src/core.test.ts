import test from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { CodexSessionsStore } from './core';

async function writeJsonl(filePath: string, records: Array<Record<string, unknown>>): Promise<void> {
  await fs.promises.mkdir(path.dirname(filePath), { recursive: true });
  const content = records.map((record) => JSON.stringify(record)).join('\n');
  await fs.promises.writeFile(filePath, `${content}\n`, 'utf8');
}

async function createSessionFixture(
  codexHome: string,
  options: { sessionId?: string; threadName?: string } = {},
): Promise<string> {
  const sessionId = options.sessionId ?? 'session-1';
  const threadName = options.threadName ?? 'First session';
  const workspaceRoot = path.join(codexHome, 'workspace-alpha');
  const updatedAt = '2026-10-12T10:00:00+00:00';
  const rolloutPath = path.join(codexHome, 'sessions', 'workspace-alpha', sessionId, 'rollout.jsonl');

  await writeJsonl(path.join(codexHome, 'session_index.jsonl'), [
    { id: sessionId, thread_name: threadName, updated_at: updatedAt },
  ]);
  await writeJsonl(rolloutPath, [
    {
      type: 'session_meta',
      timestamp: updatedAt,
      ordinal: 0,
      payload: {
        session_id: sessionId,
        timestamp: updatedAt,
        cwd: workspaceRoot,
        source: 'codex-cli',
        cli_version: '1.2.0',
        runtime_workspace_roots: [workspaceRoot],
      },
    },
    {
      timestamp: '2026-10-12T10:01:00+00:00',
      ordinal: 1,
      type: 'response_item',
      payload: {
        type: 'message',
        id: `msg-user-${sessionId}`,
        role: 'user',
        content: [{ type: 'input_text', text: 'How do I export this session?' }],
      },
    },
    {
      timestamp: '2026-10-12T10:02:00+00:00',
      ordinal: 2,
      type: 'response_item',
      payload: {
        type: 'message',
        id: `msg-assistant-${sessionId}`,
        role: 'assistant',
        content: [{ type: 'output_text', text: 'Use the new Markdown export flow.' }],
      },
    },
  ]);
  return rolloutPath;
}

async function withTempCodexHome(run: (codexHome: string) => Promise<void>): Promise<void> {
  const codexHome = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'mcs-ts-'));
  try {
    await run(codexHome);
  } finally {
    await fs.promises.rm(codexHome, { recursive: true, force: true });
  }
}

test('buildSessionSummaries collects index and rollout metadata', async () => {
  await withTempCodexHome(async (codexHome) => {
    await createSessionFixture(codexHome);
    const store = new CodexSessionsStore(codexHome);

    const summaries = await store.buildSessionSummaries();

    assert.equal(summaries.length, 1);
    const summary = summaries[0];
    assert.equal(summary.sessionId, 'session-1');
    assert.equal(summary.threadName, 'First session');
    assert.equal(summary.fileCount, 1);
    assert.equal(summary.primarySource, 'codex-cli');
    assert.equal(summary.primaryProject, path.join(codexHome, 'workspace-alpha'));
    assert.deepEqual([...summary.cliVersions].sort(), ['1.2.0']);
  });
});

test('move to trash and restore round-trip', async () => {
  await withTempCodexHome(async (codexHome) => {
    const rolloutPath = await createSessionFixture(codexHome);
    const store = new CodexSessionsStore(codexHome);
    const session = (await store.buildSessionSummaries())[0];

    const deleteResult = await store.moveSessionsToTrash([session]);

    assert.equal(deleteResult.sessionCount, 1);
    assert.equal(deleteResult.deletedFileCount, 1);
    assert.equal(deleteResult.removedIndexEntryCount, 1);
    assert.equal(fs.existsSync(rolloutPath), false);

    const trashedRolloutPath = path.join(codexHome, 'session_trash', 'sessions', 'workspace-alpha', 'session-1', 'rollout.jsonl');
    assert.equal(fs.existsSync(trashedRolloutPath), true);
    assert.deepEqual(await store.buildSessionSummaries(), []);

    const trashSummaries = await store.buildTrashSummaries();
    const restoreResult = await store.restoreSessionsFromTrash(trashSummaries);

    assert.equal(restoreResult.restoredSessionCount, 1);
    assert.equal(restoreResult.restoredFileCount, 1);
    assert.equal(restoreResult.restoredIndexEntryCount, 1);
    assert.deepEqual(restoreResult.skippedSessionIds, []);
    assert.equal(fs.existsSync(rolloutPath), true);
    assert.equal(fs.existsSync(trashedRolloutPath), false);
    const restoredSummaries = await store.buildSessionSummaries();
    assert.equal(restoredSummaries[0].threadName, 'First session');
    assert.deepEqual(await store.loadTrashRecords(), []);
  });
});

test('rename session updates active index entries and trash records', async () => {
  await withTempCodexHome(async (codexHome) => {
    const store = new CodexSessionsStore(codexHome);
    await createSessionFixture(codexHome);

    const changedActive = await store.renameSession('session-1', 'Renamed active session');
    assert.equal(changedActive, 1);
    assert.equal((await store.buildSessionSummaries())[0].threadName, 'Renamed active session');

    const session = (await store.buildSessionSummaries())[0];
    await store.moveSessionsToTrash([session]);

    const changedTrash = await store.renameSession('session-1', 'Renamed trash session', true);
    assert.equal(changedTrash, 1);
    const trashSummaries = await store.buildTrashSummaries();
    assert.equal(trashSummaries[0].threadName, 'Renamed trash session');

    await store.restoreSessionsFromTrash(trashSummaries);
    assert.equal((await store.buildSessionSummaries())[0].threadName, 'Renamed trash session');
  });
});

test('buildSessionMarkdown includes transcript and export writes file', async () => {
  await withTempCodexHome(async (codexHome) => {
    await createSessionFixture(codexHome);
    const store = new CodexSessionsStore(codexHome);
    const session = (await store.buildSessionSummaries())[0];
    const markdown = await store.buildSessionMarkdown(session);

    assert.match(markdown, /^# First session\n/);
    assert.match(markdown, /- Session ID: `session-1`/);
    assert.match(markdown, /## Transcript/);
    assert.match(markdown, /### User -/);
    assert.match(markdown, /How do I export this session\?/);
    assert.match(markdown, /### Assistant -/);
    assert.match(markdown, /Use the new Markdown export flow\./);

    const outputPath = path.join(codexHome, 'exports', 'session-1.md');
    const writtenPath = await store.exportSessionMarkdown(session, outputPath);
    assert.equal(writtenPath, outputPath);
    const exported = await fs.promises.readFile(outputPath, 'utf8');
    assert.match(exported, /# First session/);
    assert.match(exported, /Use the new Markdown export flow\./);
  });
});
