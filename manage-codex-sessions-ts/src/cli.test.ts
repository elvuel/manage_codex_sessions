import test from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { spawnSync } from 'node:child_process';

async function writeJsonl(filePath: string, records: Array<Record<string, unknown>>): Promise<void> {
  await fs.promises.mkdir(path.dirname(filePath), { recursive: true });
  const content = records.map((record) => JSON.stringify(record)).join('\n');
  await fs.promises.writeFile(filePath, `${content}\n`, 'utf8');
}

async function createSessionFixture(codexHome: string): Promise<string> {
  const sessionId = 'session-1';
  const threadName = 'First session';
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
  const codexHome = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'mcs-cli-'));
  try {
    await run(codexHome);
  } finally {
    await fs.promises.rm(codexHome, { recursive: true, force: true });
  }
}

function runCli(args: string[], cwd: string): { stdout: string; stderr: string; status: number | null } {
  const cliPath = path.join(cwd, 'out', 'cli.js');
  const result = spawnSync(process.execPath, [cliPath, ...args], {
    cwd,
    encoding: 'utf8',
  });
  return {
    stdout: result.stdout,
    stderr: result.stderr,
    status: result.status,
  };
}

test('cli query --json returns expected payload', async () => {
  const cwd = path.resolve(__dirname, '..');
  await withTempCodexHome(async (codexHome) => {
    const rolloutPath = await createSessionFixture(codexHome);
    const result = runCli(['query', '--codex-home', codexHome, '--json', '--show-files'], cwd);

    assert.equal(result.status, 0, result.stderr);
    const payload = JSON.parse(result.stdout) as Array<Record<string, unknown>>;
    assert.equal(payload.length, 1);
    assert.equal(payload[0].id, 'session-1');
    assert.equal(payload[0].thread_name, 'First session');
    assert.deepEqual(payload[0].rollout_paths, [rolloutPath]);
  });
});

test('cli export writes expected markdown file', async () => {
  const cwd = path.resolve(__dirname, '..');
  await withTempCodexHome(async (codexHome) => {
    await createSessionFixture(codexHome);
    const outputPath = path.join(codexHome, 'exports', 'session-1.md');
    const result = runCli(['export', '--codex-home', codexHome, '--id', 'session-1', '--output', outputPath], cwd);

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Exported session session-1 to/);
    const exported = await fs.promises.readFile(outputPath, 'utf8');
    assert.match(exported, /# First session/);
    assert.match(exported, /How do I export this session\?/);
    assert.match(exported, /Use the new Markdown export flow\./);
  });
});
