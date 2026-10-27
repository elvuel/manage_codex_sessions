import test from 'node:test';
import assert from 'node:assert/strict';
import { groupSessionsByProject, sessionsForProject } from './project-groups';

interface FakeSession {
  id: string;
  summary: {
    primaryProject: string;
    updatedAt: Date | null;
  };
}

test('groupSessionsByProject counts current sessions by project', () => {
  const sessions: FakeSession[] = [
    { id: 'session-1', summary: { primaryProject: 'workspace-a', updatedAt: new Date('2026-10-12T10:00:00Z') } },
    { id: 'session-2', summary: { primaryProject: 'workspace-a', updatedAt: new Date('2026-10-12T11:00:00Z') } },
    { id: 'session-3', summary: { primaryProject: '-', updatedAt: new Date('2026-10-12T12:00:00Z') } },
  ];

  assert.deepEqual(groupSessionsByProject(sessions), [
    { project: '-', sessionCount: 1 },
    { project: 'workspace-a', sessionCount: 2 },
  ]);
});

test('sessionsForProject returns only current sessions for one project in updated order', () => {
  const sessions: FakeSession[] = [
    { id: 'session-1', summary: { primaryProject: '-', updatedAt: new Date('2026-10-12T10:00:00Z') } },
    { id: 'session-2', summary: { primaryProject: 'workspace-a', updatedAt: new Date('2026-10-12T12:00:00Z') } },
    { id: 'session-3', summary: { primaryProject: '-', updatedAt: new Date('2026-10-12T11:00:00Z') } },
  ];

  assert.deepEqual(
    sessionsForProject(sessions, '-').map((session) => session.id),
    ['session-3', 'session-1'],
  );
  assert.deepEqual(sessionsForProject([], '-'), []);
});
