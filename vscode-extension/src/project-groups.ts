import { SessionSummary } from './core';

export interface SessionWithProject {
  summary: Pick<SessionSummary, 'primaryProject' | 'updatedAt'>;
}

export interface ProjectNodeModel {
  project: string;
  sessionCount: number;
}

export function groupSessionsByProject<TSession extends SessionWithProject>(sessions: TSession[]): ProjectNodeModel[] {
  const grouped = new Map<string, TSession[]>();
  for (const session of sessions) {
    const project = session.summary.primaryProject;
    const items = grouped.get(project) || [];
    items.push(session);
    grouped.set(project, items);
  }

  return [...grouped.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([project, projectSessions]) => ({
      project,
      sessionCount: projectSessions.length,
    }));
}

export function sessionsForProject<TSession extends SessionWithProject>(sessions: TSession[], project: string): TSession[] {
  return sessions
    .filter((session) => session.summary.primaryProject === project)
    .sort((left, right) => (right.summary.updatedAt?.getTime() ?? 0) - (left.summary.updatedAt?.getTime() ?? 0));
}
