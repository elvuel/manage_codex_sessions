import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import * as vscode from 'vscode';
import {
  CodexSessionsStore,
  SessionSummary,
  formatDeleteSummary,
  formatPurgeSummary,
  formatRestoreSummary,
  resolveCodexHome,
} from './core';
import { ProjectNodeModel, groupSessionsByProject, sessionsForProject } from './project-groups';

type SessionLocation = 'active' | 'trash';

interface SessionItemModel {
  summary: SessionSummary;
  location: SessionLocation;
}


class NativeCoreService {
  public resolveCodexHomePath(): string {
    const configured = this.getSetting<string>('codexHome')?.trim();
    return resolveCodexHome(configured || undefined);
  }

  public async listSessions(location: SessionLocation): Promise<SessionItemModel[]> {
    const store = this.createStore();
    const sessions = location === 'active' ? await store.buildSessionSummaries() : await store.buildTrashSummaries();
    return sessions.map((summary) => ({ summary, location }));
  }

  public async buildMarkdown(session: SessionItemModel): Promise<string> {
    return this.createStore().buildSessionMarkdown(session.summary);
  }

  public async exportSession(session: SessionItemModel, outputPath: string): Promise<string> {
    return this.createStore().exportSessionMarkdown(session.summary, outputPath);
  }

  public async renameSession(session: SessionItemModel, newName: string): Promise<string> {
    const changed = await this.createStore().renameSession(session.summary.sessionId, newName, session.location === 'trash');
    if (!changed) {
      throw new Error(`Session not found: ${session.summary.sessionId}`);
    }
    return `Renamed session ${session.summary.sessionId} to ${newName}.`;
  }

  public async deleteSession(session: SessionItemModel): Promise<string> {
    const result = await this.createStore().deleteSessions([session.summary], false);
    return formatDeleteSummary(result, true);
  }

  public async restoreSession(session: SessionItemModel): Promise<string> {
    const result = await this.createStore().restoreSessionsFromTrash([session.summary]);
    return formatRestoreSummary(result);
  }

  public async purgeSession(session: SessionItemModel): Promise<string> {
    const result = await this.createStore().purgeTrashedSessions([session.summary]);
    return formatPurgeSummary(result);
  }

  private createStore(): CodexSessionsStore {
    return new CodexSessionsStore(this.resolveCodexHomePath());
  }

  private getSetting<T>(name: string): T | undefined {
    return vscode.workspace.getConfiguration('manageCodexSessions').get<T>(name);
  }
}

class CodexHomeWatcher implements vscode.Disposable {
  private readonly watchers: fs.FSWatcher[] = [];
  private refreshTimer: NodeJS.Timeout | undefined;
  private restartTimer: NodeJS.Timeout | undefined;
  private watchedCodexHome = '';

  public constructor(
    private readonly service: NativeCoreService,
    private readonly isEnabled: () => boolean,
    private readonly onChange: () => void,
  ) {}

  public reset(): void {
    this.disposeWatchers();

    if (!this.isEnabled()) {
      return;
    }

    this.watchedCodexHome = this.service.resolveCodexHomePath();
    if (this.tryWatch(this.watchedCodexHome, true)) {
      return;
    }

    const fallbackTargets = [
      this.watchedCodexHome,
      path.join(this.watchedCodexHome, 'sessions'),
      path.join(this.watchedCodexHome, 'session_trash'),
      path.join(this.watchedCodexHome, 'session_trash', 'sessions'),
    ];
    const seen = new Set<string>();
    for (const target of fallbackTargets) {
      const watchPath = nearestExistingPath(target);
      if (!watchPath || seen.has(watchPath)) {
        continue;
      }
      seen.add(watchPath);
      this.tryWatch(watchPath, false);
    }
  }

  public dispose(): void {
    this.disposeWatchers();
    clearTimeout(this.refreshTimer);
    clearTimeout(this.restartTimer);
  }

  private tryWatch(targetPath: string, recursive: boolean): boolean {
    const watchPath = recursive ? nearestExistingPath(targetPath) : targetPath;
    if (!watchPath) {
      return false;
    }

    try {
      const watcher = fs.watch(
        watchPath,
        { recursive },
        (_eventType, filename) => {
          if (this.shouldRefresh(watchPath, filename)) {
            this.scheduleRefresh();
          }
        },
      );
      watcher.on('error', () => {
        this.scheduleRestart();
      });
      this.watchers.push(watcher);
      return true;
    } catch {
      return false;
    }
  }

  private shouldRefresh(watchPath: string, filename: string | Buffer | null): boolean {
    if (!filename) {
      return true;
    }
    const changedPath = path.resolve(watchPath, filename.toString());
    return changedPath.startsWith(this.watchedCodexHome);
  }

  private scheduleRefresh(): void {
    clearTimeout(this.refreshTimer);
    this.refreshTimer = setTimeout(() => {
      this.onChange();
    }, 400);
  }

  private scheduleRestart(): void {
    clearTimeout(this.restartTimer);
    this.restartTimer = setTimeout(() => {
      this.reset();
    }, 1000);
  }

  private disposeWatchers(): void {
    while (this.watchers.length > 0) {
      this.watchers.pop()?.close();
    }
  }
}

class SessionTreeItem extends vscode.TreeItem {
  public constructor(public readonly session: SessionItemModel) {
    super(session.summary.threadName?.trim() || session.summary.sessionId, vscode.TreeItemCollapsibleState.None);
    this.id = `${session.location}:${session.summary.sessionId}`;
    this.contextValue = session.location === 'active' ? 'session-active' : 'session-trash';
    this.description = describeSession(session.summary);
    this.tooltip = buildSessionTooltip(session.summary);
  }
}

class ProjectTreeItem extends vscode.TreeItem {
  public constructor(public readonly projectNode: ProjectNodeModel) {
    super(projectNode.project, vscode.TreeItemCollapsibleState.Collapsed);
    this.id = `project:${projectNode.project}`;
    this.contextValue = 'project-group';
    this.description = `${projectNode.sessionCount}`;
    this.tooltip = new vscode.MarkdownString(`**${projectNode.project}**\n\n${projectNode.sessionCount} session(s)`);
  }
}

class SessionsProvider implements vscode.TreeDataProvider<SessionTreeItem> {
  private readonly emitter = new vscode.EventEmitter<SessionTreeItem | undefined | void>();
  public readonly onDidChangeTreeData = this.emitter.event;

  public constructor(private readonly service: NativeCoreService, private readonly location: SessionLocation) {}

  public refresh(): void {
    this.emitter.fire();
  }

  public getTreeItem(element: SessionTreeItem): vscode.TreeItem {
    return element;
  }

  public async getChildren(): Promise<SessionTreeItem[]> {
    try {
      const sessions = await this.service.listSessions(this.location);
      return sessions.map((session) => new SessionTreeItem(session));
    } catch (error) {
      void vscode.window.showErrorMessage(asErrorMessage(error));
      return [];
    }
  }
}

class ProjectsProvider implements vscode.TreeDataProvider<ProjectTreeItem | SessionTreeItem> {
  private readonly emitter = new vscode.EventEmitter<ProjectTreeItem | SessionTreeItem | undefined | void>();
  public readonly onDidChangeTreeData = this.emitter.event;

  public constructor(private readonly service: NativeCoreService) {}

  public refresh(): void {
    this.emitter.fire();
  }

  public getTreeItem(element: ProjectTreeItem | SessionTreeItem): vscode.TreeItem {
    return element;
  }

  public async getChildren(element?: ProjectTreeItem | SessionTreeItem): Promise<Array<ProjectTreeItem | SessionTreeItem>> {
    if (element instanceof SessionTreeItem) {
      return [];
    }
    try {
      const sessions = await this.service.listSessions('active');
      if (element instanceof ProjectTreeItem) {
        return sessionsForProject(sessions, element.projectNode.project).map((session) => new SessionTreeItem(session));
      }
      return groupSessionsByProject(sessions).map((projectNode) => new ProjectTreeItem(projectNode));
    } catch (error) {
      void vscode.window.showErrorMessage(asErrorMessage(error));
      return [];
    }
  }
}

export function activate(context: vscode.ExtensionContext): void {
  const service = new NativeCoreService();
  const activeProvider = new SessionsProvider(service, 'active');
  const trashProvider = new SessionsProvider(service, 'trash');
  const projectsProvider = new ProjectsProvider(service);
  const watcher = new CodexHomeWatcher(
    service,
    () => vscode.workspace.getConfiguration('manageCodexSessions').get<boolean>('autoRefresh', true),
    () => refreshAll(activeProvider, trashProvider, projectsProvider),
  );

  watcher.reset();

  context.subscriptions.push(
    watcher,
    vscode.window.registerTreeDataProvider('manageCodexSessions.activeSessions', activeProvider),
    vscode.window.registerTreeDataProvider('manageCodexSessions.trashSessions', trashProvider),
    vscode.window.registerTreeDataProvider('manageCodexSessions.projects', projectsProvider),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (!event.affectsConfiguration('manageCodexSessions')) {
        return;
      }
      if (event.affectsConfiguration('manageCodexSessions.autoRefresh') || event.affectsConfiguration('manageCodexSessions.codexHome')) {
        watcher.reset();
      }
      refreshAll(activeProvider, trashProvider, projectsProvider);
    }),
    vscode.commands.registerCommand('manageCodexSessions.refresh', () => {
      refreshAll(activeProvider, trashProvider, projectsProvider);
    }),
    vscode.commands.registerCommand('manageCodexSessions.openSettings', async () => {
      await vscode.commands.executeCommand('workbench.action.openSettings', '@ext:local-dev.manage-codex-sessions-vscode');
    }),
    vscode.commands.registerCommand('manageCodexSessions.setCodexHome', async () => {
      const config = vscode.workspace.getConfiguration('manageCodexSessions');
      const currentValue = config.get<string>('codexHome') || '';
      const nextValue = await vscode.window.showInputBox({
        prompt: 'Set an optional CODEX_HOME override',
        value: currentValue,
        placeHolder: 'Leave empty to use ~/.codex or the current environment',
      });
      if (nextValue === undefined) {
        return;
      }
      await config.update('codexHome', nextValue.trim(), vscode.ConfigurationTarget.Global);
      watcher.reset();
      refreshAll(activeProvider, trashProvider, projectsProvider);
    }),
    vscode.commands.registerCommand('manageCodexSessions.copySessionId', async (target?: SessionItemModel | SessionTreeItem) => {
      const session = toSessionModel(target);
      if (!session) {
        return;
      }
      await vscode.env.clipboard.writeText(session.summary.sessionId);
      void vscode.window.showInformationMessage(`Copied session ID: ${session.summary.sessionId}`);
    }),
    vscode.commands.registerCommand('manageCodexSessions.previewSession', async (target?: SessionItemModel | SessionTreeItem) => {
      const session = toSessionModel(target);
      if (!session) {
        return;
      }
      await withProgress(`Previewing ${session.summary.sessionId}`, async () => {
        const markdown = await service.buildMarkdown(session);
        const document = await vscode.workspace.openTextDocument({ content: markdown, language: 'markdown' });
        await vscode.window.showTextDocument(document, { preview: false });
        await vscode.commands.executeCommand('markdown.showPreviewToSide', document.uri);
      });
    }),
    vscode.commands.registerCommand('manageCodexSessions.exportSession', async (target?: SessionItemModel | SessionTreeItem) => {
      const session = toSessionModel(target);
      if (!session) {
        return;
      }
      const defaultName = `${session.summary.sessionId}.md`;
      const destination = await vscode.window.showSaveDialog({
        defaultUri: vscode.Uri.file(path.join(vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || os.homedir(), defaultName)),
        filters: { Markdown: ['md'] },
        saveLabel: 'Export Session Markdown',
      });
      if (!destination) {
        return;
      }
      await withProgress(`Exporting ${session.summary.sessionId}`, async () => {
        const output = await service.exportSession(session, destination.fsPath);
        void vscode.window.showInformationMessage(`Exported session ${session.summary.sessionId} to ${output}`);
      });
    }),
    vscode.commands.registerCommand('manageCodexSessions.renameSession', async (target?: SessionItemModel | SessionTreeItem) => {
      const session = toSessionModel(target);
      if (!session) {
        return;
      }
      const nextName = await vscode.window.showInputBox({
        prompt: 'Rename session',
        value: session.summary.threadName || '',
        valueSelection: [0, (session.summary.threadName || '').length],
      });
      if (nextName === undefined || nextName.trim() === '') {
        return;
      }
      await withProgress(`Renaming ${session.summary.sessionId}`, async () => {
        const output = await service.renameSession(session, nextName.trim());
        void vscode.window.showInformationMessage(output);
        refreshAll(activeProvider, trashProvider, projectsProvider);
      });
    }),
    vscode.commands.registerCommand('manageCodexSessions.deleteSession', async (target?: SessionItemModel | SessionTreeItem) => {
      const session = toSessionModel(target);
      if (!session) {
        return;
      }
      const confirmed = await confirmAction(`Move session ${session.summary.sessionId} to trash?`, 'Move to Trash');
      if (!confirmed) {
        return;
      }
      await withProgress(`Deleting ${session.summary.sessionId}`, async () => {
        const output = await service.deleteSession(session);
        void vscode.window.showInformationMessage(output);
        refreshAll(activeProvider, trashProvider, projectsProvider);
      });
    }),
    vscode.commands.registerCommand('manageCodexSessions.restoreSession', async (target?: SessionItemModel | SessionTreeItem) => {
      const session = toSessionModel(target);
      if (!session) {
        return;
      }
      const confirmed = await confirmAction(`Restore session ${session.summary.sessionId}?`, 'Restore');
      if (!confirmed) {
        return;
      }
      await withProgress(`Restoring ${session.summary.sessionId}`, async () => {
        const output = await service.restoreSession(session);
        void vscode.window.showInformationMessage(output);
        refreshAll(activeProvider, trashProvider, projectsProvider);
      });
    }),
    vscode.commands.registerCommand('manageCodexSessions.purgeSession', async (target?: SessionItemModel | SessionTreeItem) => {
      const session = toSessionModel(target);
      if (!session) {
        return;
      }
      const confirmed = await confirmAction(`Permanently delete session ${session.summary.sessionId}?`, 'Delete Permanently');
      if (!confirmed) {
        return;
      }
      await withProgress(`Purging ${session.summary.sessionId}`, async () => {
        const output = await service.purgeSession(session);
        void vscode.window.showInformationMessage(output);
        refreshAll(activeProvider, trashProvider, projectsProvider);
      });
    }),
  );
}

export function deactivate(): void {}

function toSessionModel(target?: SessionItemModel | SessionTreeItem): SessionItemModel | undefined {
  if (!target) {
    return undefined;
  }
  return target instanceof SessionTreeItem ? target.session : target;
}

function refreshAll(...providers: Array<SessionsProvider | ProjectsProvider>): void {
  for (const provider of providers) {
    provider.refresh();
  }
}

async function withProgress<T>(title: string, callback: () => Promise<T>): Promise<T> {
  try {
    return await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title,
      },
      callback,
    );
  } catch (error) {
    void vscode.window.showErrorMessage(asErrorMessage(error));
    throw error;
  }
}

async function confirmAction(message: string, actionLabel: string): Promise<boolean> {
  const choice = await vscode.window.showWarningMessage(message, { modal: true }, actionLabel);
  return choice === actionLabel;
}

function describeSession(session: SessionSummary): string {
  const updated = session.updatedAt ? session.updatedAt.toLocaleString() : 'unknown';
  return `${session.primaryProject} · ${updated}`;
}

function buildSessionTooltip(session: SessionSummary): vscode.MarkdownString {
  const tooltip = new vscode.MarkdownString(undefined, true);
  tooltip.appendMarkdown(`**${escapeMarkdown(session.threadName || session.sessionId)}**\n\n`);
  tooltip.appendMarkdown(`- Session ID: \`${session.sessionId}\`\n`);
  tooltip.appendMarkdown(`- Project: \`${session.primaryProject}\`\n`);
  tooltip.appendMarkdown(`- CWD: \`${session.primaryCwd}\`\n`);
  tooltip.appendMarkdown(`- Source: \`${session.primarySource}\`\n`);
  tooltip.appendMarkdown(`- Files: ${session.fileCount}\n`);
  tooltip.appendMarkdown(`- Updated: ${session.updatedAt?.toISOString() || '-'}\n`);
  if (session.deletedAt) {
    tooltip.appendMarkdown(`- Deleted: ${session.deletedAt.toISOString()}\n`);
  }
  return tooltip;
}

function nearestExistingPath(targetPath: string): string | undefined {
  let current = path.resolve(targetPath);
  while (!fs.existsSync(current)) {
    const parent = path.dirname(current);
    if (parent === current) {
      return undefined;
    }
    current = parent;
  }
  return current;
}

function escapeMarkdown(value: string): string {
  return value.replace(/[\\`*_{}\[\]()#+\-.!|>]/g, '\\$&');
}

function asErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}





