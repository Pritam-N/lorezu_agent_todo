import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

interface Task {
    id: number;
    text: string;
    done: boolean;
    created_at: string;
    done_at: string;
    priority: string;
    due: string;
    tags: string[];
}

interface TodoDatabase {
    version: number;
    next_id: number;
    tasks: Task[];
}

// Set during activation (used to refresh tree view when status changes)
let todoTreeProvider: { refresh: () => void } | undefined;

class TodoStatusBar {
    private statusBarItem: vscode.StatusBarItem;
    private refreshTimer?: NodeJS.Timeout;
    private config: vscode.WorkspaceConfiguration;
    private fileWatcher?: fs.FSWatcher;
    private fileWatchDebounce?: NodeJS.Timeout;
    private watchedDbPath: string = '';
    private context: vscode.ExtensionContext;
    private lastLoadError: string = '';
    private lastNotifiedErrorKey: string = '';

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.config = vscode.workspace.getConfiguration('todo-cli');
        this.statusBarItem = vscode.window.createStatusBarItem(
            'todo-cli.statusBar',
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'todo-cli.openList';
        this.statusBarItem.tooltip = 'Click to open todo list | Right-click for options';
        context.subscriptions.push(this.statusBarItem);

        // Register commands
        const refreshCommand = vscode.commands.registerCommand('todo-cli.refresh', () => {
            this.updateStatus();
        });
        context.subscriptions.push(refreshCommand);

        const openListCommand = vscode.commands.registerCommand('todo-cli.openList', () => {
            this.openTodoList();
        });
        context.subscriptions.push(openListCommand);

        const addFromEditorCommand = vscode.commands.registerCommand('todo-cli.addFromEditor', () => {
            this.addTodoFromEditor();
        });
        context.subscriptions.push(addFromEditorCommand);

        const configureCommand = vscode.commands.registerCommand('todo-cli.configure', () => {
            this.configureDatabase();
        });
        context.subscriptions.push(configureCommand);

        const showPathCommand = vscode.commands.registerCommand('todo-cli.showCurrentPath', () => {
            this.showCurrentPath();
        });
        context.subscriptions.push(showPathCommand);

        const openSettingsCommand = vscode.commands.registerCommand('todo-cli.openSettings', () => {
            vscode.commands.executeCommand('workbench.action.openSettings', '@ext:todo-cli-status');
        });
        context.subscriptions.push(openSettingsCommand);

        const initializeCommand = vscode.commands.registerCommand('todo-cli.initializeDatabase', () => {
            this.initializeDatabase();
        });
        context.subscriptions.push(initializeCommand);

        const selectWorkspaceFolderCommand = vscode.commands.registerCommand('todo-cli.selectWorkspaceFolder', () => {
            this.selectWorkspaceFolder();
        });
        context.subscriptions.push(selectWorkspaceFolderCommand);

        // Watch for configuration changes (workspace and global)
        context.subscriptions.push(
            vscode.workspace.onDidChangeConfiguration(e => {
                if (e.affectsConfiguration('todo-cli.dbPath')) {
                    this.config = vscode.workspace.getConfiguration('todo-cli');
                    console.log('[Todo CLI] Configuration changed, refreshing...');
                    this.updateStatus();
                    this.startAutoRefresh();
                }
            })
        );

        // Watch for workspace folder changes
        context.subscriptions.push(
            vscode.workspace.onDidChangeWorkspaceFolders(() => {
                console.log('[Todo CLI] Workspace folders changed, refreshing...');
                this.updateStatus();
            })
        );

        // Initial update - show immediately
        this.statusBarItem.text = '$(sync~spin) Todo: Loading...';
        this.statusBarItem.show();
        
        // Update after a short delay to ensure VSCode is ready
        setTimeout(() => {
            this.updateStatus();
            this.startAutoRefresh();
        }, 500);
    }

    public resolveDbPath(): string {
        // 1. Check VSCode config (workspace-folder scope first, then global)
        const folders = vscode.workspace.workspaceFolders || [];
        const activeFolderPath = this.context.globalState.get<string>('todo-cli.activeWorkspaceFolderPath', '');
        const activeFolder = folders.find(f => f.uri.fsPath === activeFolderPath) || folders[0];

        const workspaceConfig = activeFolder
            ? vscode.workspace.getConfiguration('todo-cli', activeFolder.uri).get<string>('dbPath', '')
            : '';
        const globalConfig = vscode.workspace.getConfiguration('todo-cli', null).get<string>('dbPath', '');

        // Prefer workspace-folder setting over global
        const configPath = workspaceConfig || globalConfig;
        const configScope = workspaceConfig ? 'workspace' : (globalConfig ? 'global' : 'none');

        if (configPath) {
            const baseDir = activeFolder ? activeFolder.uri.fsPath : undefined;
            const resolved = this.expandPath(configPath, baseDir);
            console.log(`[Todo CLI] Using VSCode ${configScope} config path: ${resolved}`);
            return resolved;
        }

        // 2. Check environment variable
        const envPath = process.env.TODO_DB;
        if (envPath) {
            const resolved = this.expandPath(envPath);
            console.log(`[Todo CLI] Using TODO_DB env var: ${resolved}`);
            return resolved;
        }

        // 3. Check config file (same logic as CLI)
        const configDir = this.getConfigDir();
        const configFile = path.join(configDir, 'config.json');
        console.log(`[Todo CLI] Checking config file: ${configFile}`);
        
        if (fs.existsSync(configFile)) {
            try {
                const configData = JSON.parse(fs.readFileSync(configFile, 'utf8'));
                console.log(`[Todo CLI] Config file contents:`, configData);
                if (configData.db_path) {
                    let dbPath = configData.db_path.trim();
                    if (dbPath) {
                        // Match CLI behavior:
                        // - if absolute (or ~), use as-is (after ~ expansion)
                        // - if relative, resolve relative to config directory
                        if (dbPath.startsWith('~')) {
                            dbPath = this.expandPath(dbPath);
                        } else if (!path.isAbsolute(dbPath)) {
                            dbPath = path.resolve(configDir, dbPath);
                        } else {
                            dbPath = path.resolve(dbPath);
                        }
                        console.log(`[Todo CLI] Using config file path: ${dbPath}`);
                        return dbPath;
                    }
                }
            } catch (e) {
                console.error(`[Todo CLI] Error reading config file:`, e);
            }
        } else {
            console.log(`[Todo CLI] Config file not found at: ${configFile}`);
        }

        // 4. Default path
        const defaultPath = this.getDefaultDbPath();
        console.log(`[Todo CLI] Using default path: ${defaultPath}`);
        return defaultPath;
    }

    private expandPath(filePath: string, baseDir?: string): string {
        // Expand ~ to home directory
        const expanded = filePath.replace(/^~/, os.homedir());
        // Resolve relative paths against workspace folder when available
        if (!path.isAbsolute(expanded) && baseDir) {
            return path.resolve(baseDir, expanded);
        }
        return path.resolve(expanded);
    }

    private async selectWorkspaceFolder(): Promise<void> {
        const folders = vscode.workspace.workspaceFolders || [];
        if (folders.length <= 1) {
            vscode.window.showInformationMessage('No multi-root workspace detected.');
            return;
        }

        const picks = folders.map(f => ({
            label: f.name,
            description: f.uri.fsPath,
            folder: f,
        }));

        const selected = await vscode.window.showQuickPick(picks, {
            placeHolder: 'Select workspace folder for Todo CLI database',
            ignoreFocusOut: true,
        });

        if (!selected) {
            return;
        }

        await this.context.globalState.update('todo-cli.activeWorkspaceFolderPath', selected.folder.uri.fsPath);
        this.updateStatus();
        this.startAutoRefresh();
    }

    private getConfigDir(): string {
        const homeDir = os.homedir();
        if (process.platform === 'win32') {
            const appdata = process.env.APPDATA || path.join(homeDir, 'AppData', 'Roaming');
            return path.join(appdata, 'todo-cli');
        }
        if (process.platform === 'darwin') {
            return path.join(homeDir, 'Library', 'Application Support', 'todo-cli');
        }
        const xdg = process.env.XDG_CONFIG_HOME;
        if (xdg) {
            return path.join(xdg, 'todo-cli');
        }
        return path.join(homeDir, '.config', 'todo-cli');
    }

    private getDefaultDbPath(): string {
        const docsPath = path.join(os.homedir(), 'Documents', 'todo-cli', 'todos.json');
        if (fs.existsSync(path.dirname(docsPath))) {
            return docsPath;
        }
        return path.join(os.homedir(), '.todo-cli', 'todos.json');
    }

    public initializeDefaultDatabase(dbPath: string): boolean {
        try {
            const parentDir = path.dirname(dbPath);
            
            // Create parent directory if it doesn't exist
            if (!fs.existsSync(parentDir)) {
                fs.mkdirSync(parentDir, { recursive: true });
                console.log(`[Todo CLI] Created directory: ${parentDir}`);
            }

            // Create default database structure
            const defaultDb: TodoDatabase = {
                version: 1,
                next_id: 1,
                tasks: []
            };

            // Write default database file
            fs.writeFileSync(dbPath, JSON.stringify(defaultDb, null, 2), 'utf8');
            console.log(`[Todo CLI] Created default database at: ${dbPath}`);
            return true;
        } catch (error) {
            console.error('[Todo CLI] Error creating default database:', error);
            return false;
        }
    }

    public loadTasks(): TodoDatabase | null {
        const dbPath = this.resolveDbPath();
        console.log(`[Todo CLI] Resolved DB path: ${dbPath}`);
        console.log(`[Todo CLI] Path exists: ${fs.existsSync(dbPath)}`);
        
        if (!fs.existsSync(dbPath)) {
            this.lastLoadError = '';
            console.log(`[Todo CLI] Database file not found at: ${dbPath}`);
            
            // Try to create default database
            const created = this.initializeDefaultDatabase(dbPath);
            if (created) {
                // Return the newly created database
                return {
                    version: 1,
                    next_id: 1,
                    tasks: []
                };
            }
            
            // Check if parent directory exists
            const parentDir = path.dirname(dbPath);
            console.log(`[Todo CLI] Parent directory exists: ${fs.existsSync(parentDir)}`);
            if (fs.existsSync(parentDir)) {
                console.log(`[Todo CLI] Parent directory contents:`, fs.readdirSync(parentDir));
            }
            return null;
        }

        try {
            const data = fs.readFileSync(dbPath, 'utf8');
            const db: TodoDatabase = JSON.parse(data);
            db.tasks = db.tasks || [];
            // Schema/version sanity
            const rawVersion: any = (db as any).version ?? 1;
            const version = Number(rawVersion);
            if (!Number.isFinite(version)) {
                (db as any).version = 1;
                this.saveDatabase(dbPath, db);
            } else if (version > 1) {
                this.lastLoadError = `Unsupported DB version: ${version}`;
                return null;
            } else if (version !== 1) {
                (db as any).version = 1;
                this.saveDatabase(dbPath, db);
            }
            if (!(db as any).next_id || typeof (db as any).next_id !== 'number') {
                const maxId = db.tasks.reduce((m, t) => Math.max(m, t.id || 0), 0);
                (db as any).next_id = maxId + 1;
                this.saveDatabase(dbPath, db);
            }
            this.lastLoadError = '';
            console.log(`[Todo CLI] Loaded ${db.tasks.length} tasks from database`);
            return db;
        } catch (error) {
            this.lastLoadError = String(error);
            console.error('[Todo CLI] Error loading todo database:', error);
            return null;
        }
    }

    private notifyDbIssueOnce(key: string, message: string, actions: string[]): void {
        if (this.lastNotifiedErrorKey === key) {
            return;
        }
        this.lastNotifiedErrorKey = key;
        vscode.window.showWarningMessage(message, ...actions).then(selection => {
            if (!selection) return;
            if (selection === 'Fix Path') {
                vscode.commands.executeCommand('todo-cli.configure');
            } else if (selection === 'Open DB') {
                const dbPath = this.resolveDbPath();
                vscode.commands.executeCommand('vscode.open', vscode.Uri.file(dbPath));
            } else if (selection === 'Initialize') {
                vscode.commands.executeCommand('todo-cli.initializeDatabase');
            } else if (selection === 'Show Path') {
                vscode.commands.executeCommand('todo-cli.showCurrentPath');
            }
        });
    }

    private saveDatabase(dbPath: string, db: TodoDatabase): boolean {
        try {
            const parentDir = path.dirname(dbPath);
            if (!fs.existsSync(parentDir)) {
                fs.mkdirSync(parentDir, { recursive: true });
            }

            // Atomic-ish write: write temp then replace
            const tmpPath = `${dbPath}.tmp`;
            fs.writeFileSync(tmpPath, JSON.stringify(db, null, 2), 'utf8');
            fs.renameSync(tmpPath, dbPath);
            return true;
        } catch (error) {
            console.error('[Todo CLI] Error saving database:', error);
            return false;
        }
    }

    public updateDatabase(mutator: (db: TodoDatabase) => void): TodoDatabase | null {
        const dbPath = this.resolveDbPath();
        const db = this.loadTasks();
        if (!db) {
            return null;
        }
        mutator(db);
        const ok = this.saveDatabase(dbPath, db);
        return ok ? db : null;
    }

    private calculateStats(db: TodoDatabase) {
        const total = db.tasks.length;
        const done = db.tasks.filter(t => t.done).length;
        const pending = total - done;
        const highPriority = db.tasks.filter(t => !t.done && t.priority?.toLowerCase() === 'high').length;
        
        const today = new Date().toISOString().split('T')[0];
        const overdue = db.tasks.filter(t => {
            if (t.done || !t.due) return false;
            return t.due < today;
        }).length;
        
        const dueToday = db.tasks.filter(t => {
            if (t.done || !t.due) return false;
            return t.due === today;
        }).length;

        return { total, done, pending, highPriority, overdue, dueToday };
    }

    private updateStatus(): void {
        try {
            const db = this.loadTasks();
            
            if (!db) {
                const dbPath = this.resolveDbPath();
                if (this.lastLoadError) {
                    this.statusBarItem.text = '$(error) Todo: DB error';
                    this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                    this.statusBarItem.tooltip = `Todo database error at:\n${dbPath}\n\n${this.lastLoadError}\n\nFix: Configure path, open DB, or re-initialize.`;
                    this.statusBarItem.show();
                    this.notifyDbIssueOnce(
                        `db-error:${dbPath}`,
                        `Todo CLI: DB error at ${dbPath}\n${this.lastLoadError}`,
                        ['Fix Path', 'Open DB', 'Initialize', 'Show Path']
                    );
                } else {
                    this.statusBarItem.text = '$(checklist) Todo: No database';
                    this.statusBarItem.backgroundColor = undefined;
                    this.statusBarItem.tooltip = `Todo database not found at:\n${dbPath}\n\nClick to configure or initialize.`;
                    this.statusBarItem.show();
                    this.notifyDbIssueOnce(
                        `db-missing:${dbPath}`,
                        `Todo CLI: database not found at ${dbPath}`,
                        ['Fix Path', 'Initialize', 'Show Path']
                    );
                }
                todoTreeProvider?.refresh();
                return;
            }

        const stats = this.calculateStats(db);
        const showPendingOnly = this.config.get<boolean>('showPendingOnly', false);

        if (showPendingOnly) {
            this.statusBarItem.text = `$(checklist) ${stats.pending} pending`;
        } else {
            let text = `$(checklist) ${stats.pending}`;
            if (stats.done > 0) {
                text += `/${stats.done}`;
            }
            if (stats.highPriority > 0) {
                text += ` $(warning) ${stats.highPriority}`;
            }
            if (stats.overdue > 0) {
                text += ` $(error) ${stats.overdue}`;
            } else if (stats.dueToday > 0) {
                text += ` $(clock) ${stats.dueToday}`;
            }
            this.statusBarItem.text = text;
        }

        // Color coding based on urgency
        if (stats.overdue > 0) {
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
        } else if (stats.dueToday > 0 || stats.highPriority > 0) {
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        } else if (stats.pending > 0) {
            this.statusBarItem.backgroundColor = undefined;
        } else {
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.prominentBackground');
        }

        // Update tooltip
        const tooltip = [
            `Total: ${stats.total}`,
            `Pending: ${stats.pending}`,
            `Done: ${stats.done}`,
            stats.highPriority > 0 ? `High Priority: ${stats.highPriority}` : '',
            stats.overdue > 0 ? `Overdue: ${stats.overdue}` : '',
            stats.dueToday > 0 ? `Due Today: ${stats.dueToday}` : '',
            '',
            'Click to open todo list',
            'Right-click for more options'
        ].filter(Boolean).join('\n');
        
        this.statusBarItem.tooltip = tooltip;
        this.statusBarItem.show();
        todoTreeProvider?.refresh();
        } catch (error) {
            console.error('Todo CLI Extension Error:', error);
            this.statusBarItem.text = '$(error) Todo: Error';
            this.statusBarItem.tooltip = `Error loading todos: ${error}`;
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
            this.statusBarItem.show();
            todoTreeProvider?.refresh();
        }
    }

    private startAutoRefresh(): void {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        // Start file watcher for instant refresh on DB changes
        this.startFileWatch();

        // Keep polling as a fallback (e.g., network FS where watch is unreliable)
        const interval = this.config.get<number>('refreshInterval', 5000);
        if (interval > 0) {
            this.refreshTimer = setInterval(() => {
                this.updateStatus();
            }, interval);
        }
    }

    private stopFileWatch(): void {
        try {
            this.fileWatcher?.close();
        } catch {
            // ignore
        }
        this.fileWatcher = undefined;
        this.watchedDbPath = '';
        if (this.fileWatchDebounce) {
            clearTimeout(this.fileWatchDebounce);
            this.fileWatchDebounce = undefined;
        }
    }

    private startFileWatch(): void {
        const dbPath = this.resolveDbPath();
        if (dbPath && dbPath === this.watchedDbPath && this.fileWatcher) {
            return;
        }

        this.stopFileWatch();
        this.watchedDbPath = dbPath;

        const dir = path.dirname(dbPath);
        const base = path.basename(dbPath);
        if (!fs.existsSync(dir)) {
            return;
        }

        try {
            this.fileWatcher = fs.watch(dir, { persistent: false }, (_eventType, filename) => {
                // Some platforms may not provide filename
                if (filename && filename.toString() !== base) {
                    return;
                }
                if (this.fileWatchDebounce) {
                    clearTimeout(this.fileWatchDebounce);
                }
                this.fileWatchDebounce = setTimeout(() => {
                    console.log('[Todo CLI] DB file change detected, refreshing...');
                    this.updateStatus();
                }, 200);
            });
        } catch (err) {
            console.error('[Todo CLI] Failed to start file watcher:', err);
            // Keep polling fallback running
        }
    }

    private async initializeDatabase(): Promise<void> {
        const dbPath = this.resolveDbPath();
        
        if (fs.existsSync(dbPath)) {
            const action = await vscode.window.showWarningMessage(
                `Database already exists at:\n${dbPath}\n\nDo you want to overwrite it?`,
                { modal: true },
                'Overwrite',
                'Cancel'
            );
            
            if (action !== 'Overwrite') {
                return;
            }
        }

        const created = this.initializeDefaultDatabase(dbPath);
        if (created) {
            this.updateStatus();
            vscode.window.showInformationMessage(
                `✅ Database initialized at:\n${dbPath}`,
                'Open File', 'Change Path'
            ).then(selection => {
                if (selection === 'Open File') {
                    const fileUri = vscode.Uri.file(dbPath);
                    vscode.commands.executeCommand('vscode.open', fileUri);
                } else if (selection === 'Change Path') {
                    this.configureDatabase();
                }
            });
        } else {
            vscode.window.showErrorMessage(`Failed to create database at:\n${dbPath}`);
        }
    }

    private async openTodoList(): Promise<void> {
        type TaskPickItem = vscode.QuickPickItem & { task: Task };

        const buildItems = (db: TodoDatabase): TaskPickItem[] => {
            const pending = db.tasks.filter(t => !t.done);
            return pending.map(task => {
                const pri = task.priority ? task.priority.toLowerCase() : '';
                const priIcon = pri === 'high' ? '$(warning) ' : pri === 'med' ? '$(circle-filled) ' : pri === 'low' ? '$(circle-outline) ' : '';
                const dueText = task.due ? `Due: ${task.due}` : '';
                const tagText = task.tags?.length ? `Tags: ${task.tags.join(', ')}` : '';
                return {
                    label: `${priIcon}${task.text}`,
                    description: `#${task.id}` + (task.priority ? `  ${task.priority}` : ''),
                    detail: [dueText, tagText].filter(Boolean).join('  |  '),
                    task,
                };
            });
        };

        const qp = vscode.window.createQuickPick<TaskPickItem>();
        qp.matchOnDescription = true;
        qp.matchOnDetail = true;
        qp.placeholder = 'Enter=toggle done, e=edit, d=delete, p=priority, t=add tag (type to search)';

        let active: TaskPickItem | undefined;

        const refresh = () => {
            const db = this.loadTasks();
            if (!db) {
                qp.hide();
                vscode.window.showErrorMessage('Todo database not found. Use "Todo CLI: Configure Database Path" or "Initialize Database".');
                return;
            }
            const items = buildItems(db);
            qp.items = items;
            if (items.length === 0) {
                qp.hide();
                vscode.window.showInformationMessage('No pending tasks! 🎉');
                this.updateStatus();
                return;
            }
            // Keep active selection stable
            if (!active) {
                qp.activeItems = [items[0]];
            }
            this.updateStatus();
        };

        const nowIso = () => new Date().toISOString();

        const toggleDone = async (taskId: number) => {
            const updated = this.updateDatabase(db => {
                const t = db.tasks.find(x => x.id === taskId);
                if (!t) return;
                t.done = !t.done;
                t.done_at = t.done ? nowIso() : '';
            });
            if (!updated) {
                vscode.window.showErrorMessage('Failed to update task.');
            }
        };

        const editTask = async (task: Task) => {
            const text = await vscode.window.showInputBox({
                prompt: 'Edit task text',
                value: task.text || '',
            });
            if (text === undefined) return;
            const updated = this.updateDatabase(db => {
                const t = db.tasks.find(x => x.id === task.id);
                if (!t) return;
                t.text = text.trim();
            });
            if (!updated) vscode.window.showErrorMessage('Failed to edit task.');
        };

        const deleteTask = async (task: Task) => {
            const confirm = await vscode.window.showWarningMessage(
                `Delete task #${task.id}?`,
                { modal: true },
                'Delete'
            );
            if (confirm !== 'Delete') return;
            const updated = this.updateDatabase(db => {
                db.tasks = db.tasks.filter(x => x.id !== task.id);
            });
            if (!updated) vscode.window.showErrorMessage('Failed to delete task.');
        };

        const changePriority = async (task: Task) => {
            const choice = await vscode.window.showQuickPick(
                [
                    { label: 'high', description: 'High priority' },
                    { label: 'med', description: 'Medium priority' },
                    { label: 'low', description: 'Low priority' },
                    { label: '(none)', description: 'Clear priority' },
                ],
                { placeHolder: `Priority for #${task.id}` }
            );
            if (!choice) return;
            const value = choice.label === '(none)' ? '' : choice.label;
            const updated = this.updateDatabase(db => {
                const t = db.tasks.find(x => x.id === task.id);
                if (!t) return;
                t.priority = value;
            });
            if (!updated) vscode.window.showErrorMessage('Failed to update priority.');
        };

        const addTag = async (task: Task) => {
            const tagInput = await vscode.window.showInputBox({
                prompt: `Add tag(s) to #${task.id} (comma or space separated)`,
            });
            if (!tagInput) return;
            const tags = tagInput
                .split(/[, ]+/)
                .map(s => s.trim())
                .filter(Boolean);
            if (tags.length === 0) return;
            const updated = this.updateDatabase(db => {
                const t = db.tasks.find(x => x.id === task.id);
                if (!t) return;
                const existing = new Set((t.tags || []).map(x => x.trim()).filter(Boolean));
                for (const tg of tags) existing.add(tg);
                t.tags = Array.from(existing).sort();
            });
            if (!updated) vscode.window.showErrorMessage('Failed to add tag(s).');
        };

        qp.onDidChangeActive(items => {
            active = items[0];
        });

        qp.onDidAccept(async () => {
            const item = active ?? qp.selectedItems[0];
            if (!item) return;
            // Enter toggles done
            await toggleDone(item.task.id);
            refresh();
        });

        qp.onDidChangeValue(async (value) => {
            const cmd = value.trim().toLowerCase();
            if (!cmd) return;
            const item = active ?? qp.activeItems[0];
            if (!item) return;

            if (cmd === 'e') {
                qp.value = '';
                await editTask(item.task);
                refresh();
            } else if (cmd === 'd') {
                qp.value = '';
                await deleteTask(item.task);
                refresh();
            } else if (cmd === 'p') {
                qp.value = '';
                await changePriority(item.task);
                refresh();
            } else if (cmd === 't') {
                qp.value = '';
                await addTag(item.task);
                refresh();
            }
        });

        qp.onDidHide(() => qp.dispose());

        // Initial load
        refresh();
        qp.show();
    }

    private async addTodoFromEditor(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        let seedText = '';
        let fileHint = '';

        if (editor) {
            const selText = editor.document.getText(editor.selection).trim();
            seedText = selText;
            fileHint = path.basename(editor.document.fileName || '');
            if (!seedText) {
                const line = editor.document.lineAt(editor.selection.active.line).text.trim();
                seedText = line;
            }
        }

        const prefill = seedText ? seedText : (fileHint ? `${fileHint}: ` : '');
        const input = await vscode.window.showInputBox({
            prompt: 'Add a new todo',
            value: prefill,
            placeHolder: 'Type your task…',
            ignoreFocusOut: true,
        });

        if (input === undefined) {
            return;
        }
        const text = input.trim();
        if (!text) {
            return;
        }

        const nowIso = () => new Date().toISOString();

        const updated = this.updateDatabase(db => {
            const id = db.next_id || 1;
            db.tasks = db.tasks || [];
            db.tasks.push({
                id,
                text,
                done: false,
                created_at: nowIso(),
                done_at: '',
                priority: '',
                due: '',
                tags: [],
            });
            db.next_id = id + 1;
        });

        if (!updated) {
            vscode.window.showErrorMessage('Failed to add todo. Check DB path or initialize database.');
            return;
        }

        this.updateStatus();
        vscode.window.showInformationMessage(`✅ Added todo: ${text}`);
    }

    private async configureDatabase(): Promise<void> {
        const currentPath = this.resolveDbPath();
        const workspaceConfig = vscode.workspace.getConfiguration('todo-cli').get<string>('dbPath', '');
        const globalConfig = vscode.workspace.getConfiguration('todo-cli', null).get<string>('dbPath', '');
        const hasWorkspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0;
        const configFile = path.join(this.getConfigDir(), 'config.json');
        const configFileExists = fs.existsSync(configFile);
        
        // Show quick pick with options
        const options = [
            {
                label: '$(folder-opened) Set Workspace Path',
                description: 'Set database path for this workspace only',
                detail: hasWorkspace ? (workspaceConfig || 'Not set - will use workspace setting') : 'No workspace open',
                target: vscode.ConfigurationTarget.Workspace,
                enabled: hasWorkspace
            },
            {
                label: '$(globe) Set Global Path',
                description: 'Set database path globally (all workspaces)',
                detail: globalConfig || 'Not set - will use global setting',
                target: vscode.ConfigurationTarget.Global,
                enabled: true
            },
            {
                label: '$(edit) Enter Custom Path',
                description: 'Manually enter database path',
                detail: 'Choose workspace or global scope',
                target: null,
                enabled: true
            },
            {
                label: '$(folder-opened) Browse for File',
                description: 'Select database file from file system',
                detail: 'Choose workspace or global scope',
                target: null,
                enabled: true
            },
            {
                label: '$(clear) Clear Workspace Setting',
                description: 'Remove workspace path (use global/default)',
                detail: workspaceConfig ? `Currently: ${workspaceConfig}` : 'No workspace setting',
                target: vscode.ConfigurationTarget.Workspace,
                enabled: hasWorkspace && !!workspaceConfig
            },
            {
                label: '$(clear) Clear Global Setting',
                description: 'Remove global path (use default resolution)',
                detail: globalConfig ? `Currently: ${globalConfig}` : 'No global setting',
                target: vscode.ConfigurationTarget.Global,
                enabled: !!globalConfig
            },
            {
                label: '$(info) Show Current Path',
                description: 'Display current resolved path and settings',
                detail: currentPath
            }
        ].filter(opt => opt.enabled);

        const selected = await vscode.window.showQuickPick(options, {
            placeHolder: 'Configure Todo Database Path',
            ignoreFocusOut: true
        });

        if (!selected) {
            return;
        }

        // Handle scope selection for Set Workspace/Global Path
        if (selected.label.includes('Set Workspace Path') || selected.label.includes('Set Global Path')) {
            const target = selected.target!;
            const scopeName = target === vscode.ConfigurationTarget.Workspace ? 'workspace' : 'global';
            const currentValue = target === vscode.ConfigurationTarget.Workspace ? workspaceConfig : globalConfig;
            
            const input = await vscode.window.showInputBox({
                prompt: `Enter path for ${scopeName} setting`,
                value: currentValue || currentPath,
                placeHolder: 'e.g., ~/Documents/todos.json or /absolute/path/todos.json',
                validateInput: (value) => {
                    if (!value || value.trim() === '') {
                        return null; // Empty is valid (uses default)
                    }
                    const expanded = this.expandPath(value.trim());
                    if (!fs.existsSync(expanded) && !expanded.endsWith('.json')) {
                        return 'Path does not exist. Make sure the file exists or will be created.';
                    }
                    return null;
                }
            });

            if (input !== undefined) {
                const value = input.trim();
                await vscode.workspace.getConfiguration('todo-cli').update('dbPath', value, target);
                this.updateStatus();
                const newPath = this.resolveDbPath();
                vscode.window.showInformationMessage(
                    `✅ ${scopeName.charAt(0).toUpperCase() + scopeName.slice(1)} database path updated!\n` +
                    `Setting: ${value || '(default)'}\n` +
                    `Resolved: ${newPath}`
                );
            }
            return;
        }

        // Handle Enter Custom Path - ask for scope first
        if (selected.label.includes('Enter Custom Path')) {
            const scopeOptions = [];
            if (hasWorkspace) {
                scopeOptions.push({
                    label: '$(folder-opened) Workspace',
                    description: 'Set for this workspace only',
                    target: vscode.ConfigurationTarget.Workspace
                });
            }
            scopeOptions.push({
                label: '$(globe) Global',
                description: 'Set for all workspaces',
                target: vscode.ConfigurationTarget.Global
            });

            const scopeSelected = await vscode.window.showQuickPick(scopeOptions, {
                placeHolder: 'Choose scope for database path'
            });

            if (!scopeSelected) {
                return;
            }

            const currentValue = scopeSelected.target === vscode.ConfigurationTarget.Workspace 
                ? workspaceConfig 
                : globalConfig;

            const input = await vscode.window.showInputBox({
                prompt: `Enter path for ${scopeSelected.label.includes('Workspace') ? 'workspace' : 'global'} setting`,
                value: currentValue || currentPath,
                placeHolder: 'e.g., ~/Documents/todos.json or /absolute/path/todos.json',
                validateInput: (value) => {
                    if (!value || value.trim() === '') {
                        return null;
                    }
                    const expanded = this.expandPath(value.trim());
                    if (!fs.existsSync(expanded) && !expanded.endsWith('.json')) {
                        return 'Path does not exist. Make sure the file exists or will be created.';
                    }
                    return null;
                }
            });

            if (input !== undefined) {
                const value = input.trim();
                await vscode.workspace.getConfiguration('todo-cli').update('dbPath', value, scopeSelected.target);
                this.updateStatus();
                const newPath = this.resolveDbPath();
                const scopeName = scopeSelected.label.includes('Workspace') ? 'workspace' : 'global';
                vscode.window.showInformationMessage(
                    `✅ ${scopeName.charAt(0).toUpperCase() + scopeName.slice(1)} database path updated!\n` +
                    `Setting: ${value || '(default)'}\n` +
                    `Resolved: ${newPath}`
                );
            }
            return;
        }

        // Handle Browse for File - ask for scope first
        if (selected.label.includes('Browse')) {
            const scopeOptions = [];
            if (hasWorkspace) {
                scopeOptions.push({
                    label: '$(folder-opened) Workspace',
                    description: 'Set for this workspace only',
                    target: vscode.ConfigurationTarget.Workspace
                });
            }
            scopeOptions.push({
                label: '$(globe) Global',
                description: 'Set for all workspaces',
                target: vscode.ConfigurationTarget.Global
            });

            const scopeSelected = await vscode.window.showQuickPick(scopeOptions, {
                placeHolder: 'Choose scope for database path'
            });

            if (!scopeSelected) {
                return;
            }

            const fileUri = await vscode.window.showOpenDialog({
                canSelectFiles: true,
                canSelectFolders: false,
                canSelectMany: false,
                openLabel: 'Select Database File',
                filters: {
                    'JSON Files': ['json'],
                    'All Files': ['*']
                },
                defaultUri: currentPath && fs.existsSync(currentPath) 
                    ? vscode.Uri.file(currentPath) 
                    : vscode.Uri.file(os.homedir())
            });

            if (fileUri && fileUri.length > 0) {
                const selectedPath = fileUri[0].fsPath;
                await vscode.workspace.getConfiguration('todo-cli').update('dbPath', selectedPath, scopeSelected.target);
                this.updateStatus();
                const scopeName = scopeSelected.label.includes('Workspace') ? 'workspace' : 'global';
                vscode.window.showInformationMessage(
                    `✅ ${scopeName.charAt(0).toUpperCase() + scopeName.slice(1)} database path set to:\n${selectedPath}`
                );
            }
            return;
        }

        // Handle Clear settings
        if (selected.label.includes('Clear')) {
            const target = selected.target!;
            const scopeName = target === vscode.ConfigurationTarget.Workspace ? 'workspace' : 'global';
            const currentValue = target === vscode.ConfigurationTarget.Workspace ? workspaceConfig : globalConfig;
            
            if (currentValue) {
                const confirm = await vscode.window.showWarningMessage(
                    `Remove ${scopeName} database path setting?`,
                    { modal: true },
                    'Remove'
                );
                if (confirm === 'Remove') {
                    await vscode.workspace.getConfiguration('todo-cli').update('dbPath', undefined, target);
                    this.updateStatus();
                    vscode.window.showInformationMessage(
                        `✅ ${scopeName.charAt(0).toUpperCase() + scopeName.slice(1)} path removed. Using default resolution:\n${this.resolveDbPath()}`
                    );
                }
            } else {
                vscode.window.showInformationMessage(`No ${scopeName} path is currently set.`);
            }
            return;
        }

        // Handle Show Current Path
        if (selected.label.includes('Show Current Path')) {
            this.showCurrentPath();
        }
    }

    private async showCurrentPath(): Promise<void> {
        const currentPath = this.resolveDbPath();
        const workspaceConfig = vscode.workspace.getConfiguration('todo-cli').get<string>('dbPath', '');
        const globalConfig = vscode.workspace.getConfiguration('todo-cli', null).get<string>('dbPath', '');
        const envPath = process.env.TODO_DB;
        const configFile = path.join(this.getConfigDir(), 'config.json');
        
        let configFileContent = '';
        if (fs.existsSync(configFile)) {
            try {
                const configData = JSON.parse(fs.readFileSync(configFile, 'utf8'));
                configFileContent = configData.db_path || '(not set)';
            } catch (e) {
                configFileContent = '(error reading)';
            }
        }

        const exists = fs.existsSync(currentPath);
        let source = 'default path';
        if (workspaceConfig) {
            source = 'workspace setting';
        } else if (globalConfig) {
            source = 'global setting';
        } else if (envPath) {
            source = 'environment variable';
        } else if (configFileContent && configFileContent !== '(not set)') {
            source = 'config file';
        }

        // Show as input box (read-only) for better formatting
        await vscode.window.showInputBox({
            value: currentPath,
            prompt: `Current Database Path (read-only) - Using: ${source}`,
            ignoreFocusOut: true
        });

        const action = await vscode.window.showQuickPick([
            {
                label: '$(edit) Configure Path',
                description: 'Change database path setting'
            },
            {
                label: '$(folder-opened) Open File Location',
                description: 'Reveal database file in file explorer'
            },
            {
                label: '$(copy) Copy Path',
                description: 'Copy path to clipboard'
            },
            {
                label: '$(info) View All Settings',
                description: 'Show workspace, global, and other settings'
            }
        ], {
            placeHolder: 'Choose an action'
        });

        if (action) {
            if (action.label.includes('Configure')) {
                this.configureDatabase();
            } else if (action.label.includes('Open File Location')) {
                const fileUri = vscode.Uri.file(path.dirname(currentPath));
                vscode.commands.executeCommand('revealFileInOS', fileUri);
            } else if (action.label.includes('Copy')) {
                vscode.env.clipboard.writeText(currentPath);
                vscode.window.showInformationMessage(`✅ Path copied: ${currentPath}`);
            } else if (action.label.includes('View All')) {
                const details = [
                    `**Resolved Path:** ${currentPath}`,
                    `**File Exists:** ${exists ? '✅ Yes' : '❌ No'}`,
                    '',
                    '**Configuration Sources:**',
                    `1. **Workspace Setting:** ${workspaceConfig || '*(not set)*'}`,
                    `2. **Global Setting:** ${globalConfig || '*(not set)*'}`,
                    `3. **Environment Variable (TODO_DB):** ${envPath || '*(not set)*'}`,
                    `4. **Config File:** ${configFileContent}`,
                    `5. **Default Path:** ${this.getDefaultDbPath()}`,
                    '',
                    `**Current Resolution:** Using ${source}`
                ].join('\n');

                await vscode.window.showInformationMessage(details, { modal: true });
            }
        }
    }

    public dispose(): void {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        this.stopFileWatch();
        this.statusBarItem.dispose();
    }
}

export function activate(context: vscode.ExtensionContext) {
    console.log('Todo CLI Extension is now active!');
    
    try {
        const todoStatusBar = new TodoStatusBar(context);
        context.subscriptions.push({
            dispose: () => todoStatusBar.dispose()
        });

        // Tree view (Explorer sidebar)
        class TodoTreeItem extends vscode.TreeItem {
            constructor(
                public readonly node:
                    | { kind: 'group'; group: 'priority' | 'due' | 'tags' }
                    | { kind: 'bucket'; group: 'priority' | 'due' | 'tags'; key: string }
                    | { kind: 'task'; task: Task },
                label: string,
                collapsibleState: vscode.TreeItemCollapsibleState
            ) {
                super(label, collapsibleState);
            }
        }

        class TodoTreeDataProvider implements vscode.TreeDataProvider<TodoTreeItem> {
            private _onDidChangeTreeData = new vscode.EventEmitter<TodoTreeItem | undefined | null | void>();
            readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

            constructor(private readonly statusBar: TodoStatusBar) {}

            refresh(): void {
                this._onDidChangeTreeData.fire();
            }

            getTreeItem(element: TodoTreeItem): vscode.TreeItem {
                return element;
            }

            async getChildren(element?: TodoTreeItem): Promise<TodoTreeItem[]> {
                const db = this.statusBar.loadTasks();
                if (!db) {
                    return [];
                }

                const pending = db.tasks.filter(t => !t.done);
                const today = new Date().toISOString().split('T')[0];

                if (!element) {
                    return [
                        new TodoTreeItem({ kind: 'group', group: 'priority' }, 'By Priority', vscode.TreeItemCollapsibleState.Collapsed),
                        new TodoTreeItem({ kind: 'group', group: 'due' }, 'By Due', vscode.TreeItemCollapsibleState.Collapsed),
                        new TodoTreeItem({ kind: 'group', group: 'tags' }, 'By Tag', vscode.TreeItemCollapsibleState.Collapsed),
                    ];
                }

                if (element.node.kind === 'group') {
                    const g = element.node.group;
                    if (g === 'priority') {
                        const buckets: Array<{ key: string; label: string; filter: (t: Task) => boolean }> = [
                            { key: 'high', label: 'High', filter: t => (t.priority || '').toLowerCase() === 'high' },
                            { key: 'med', label: 'Medium', filter: t => (t.priority || '').toLowerCase() === 'med' },
                            { key: 'low', label: 'Low', filter: t => (t.priority || '').toLowerCase() === 'low' },
                            { key: 'none', label: 'None', filter: t => !(t.priority || '').trim() },
                        ];
                        const out: TodoTreeItem[] = [];
                        for (const b of buckets) {
                            const count = pending.filter(b.filter).length;
                            if (count <= 0) continue;
                            out.push(
                                new TodoTreeItem(
                                    { kind: 'bucket', group: 'priority', key: b.key },
                                    `${b.label} (${count})`,
                                    vscode.TreeItemCollapsibleState.Collapsed
                                )
                            );
                        }
                        return out;
                    }

                    if (g === 'due') {
                        const classify = (t: Task): string => {
                            if (!t.due) return 'none';
                            if (t.due < today) return 'overdue';
                            if (t.due === today) return 'today';
                            // soon = next 3 days
                            const d = Date.parse(t.due);
                            const dtoday = Date.parse(today);
                            const days = Math.round((d - dtoday) / (1000 * 60 * 60 * 24));
                            if (days <= 3) return 'soon';
                            return 'upcoming';
                        };
                        const buckets: Array<{ key: string; label: string }> = [
                            { key: 'overdue', label: 'Overdue' },
                            { key: 'today', label: 'Today' },
                            { key: 'soon', label: 'Soon' },
                            { key: 'upcoming', label: 'Upcoming' },
                            { key: 'none', label: 'No Due Date' },
                        ];
                        const out: TodoTreeItem[] = [];
                        for (const b of buckets) {
                            const count = pending.filter(t => classify(t) === b.key).length;
                            if (count <= 0) continue;
                            out.push(
                                new TodoTreeItem(
                                    { kind: 'bucket', group: 'due', key: b.key },
                                    `${b.label} (${count})`,
                                    vscode.TreeItemCollapsibleState.Collapsed
                                )
                            );
                        }
                        return out;
                    }

                    // tags
                    const tagSet = new Set<string>();
                    for (const t of pending) {
                        for (const tg of t.tags || []) tagSet.add(tg);
                    }
                    return Array.from(tagSet)
                        .sort((a, b) => a.localeCompare(b))
                        .map(tag => {
                            const count = pending.filter(t => (t.tags || []).includes(tag)).length;
                            return new TodoTreeItem(
                                { kind: 'bucket', group: 'tags', key: tag },
                                `#${tag} (${count})`,
                                vscode.TreeItemCollapsibleState.Collapsed
                            );
                        });
                }

                if (element.node.kind === 'bucket') {
                    const b = element.node;

                    const byPriority = (t: Task) => {
                        const pri = (t.priority || '').toLowerCase();
                        if (b.key === 'none') return !pri;
                        return pri === b.key;
                    };
                    const byDue = (t: Task) => {
                        if (b.key === 'none') return !t.due;
                        if (!t.due) return false;
                        if (b.key === 'overdue') return t.due < today;
                        if (b.key === 'today') return t.due === today;
                        const d = Date.parse(t.due);
                        const dtoday = Date.parse(today);
                        const days = Math.round((d - dtoday) / (1000 * 60 * 60 * 24));
                        if (b.key === 'soon') return days > 0 && days <= 3;
                        if (b.key === 'upcoming') return days > 3;
                        return false;
                    };
                    const byTag = (t: Task) => (t.tags || []).includes(b.key);

                    const filtered = pending.filter(t => {
                        if (b.group === 'priority') return byPriority(t);
                        if (b.group === 'due') return byDue(t);
                        return byTag(t);
                    });

                    return filtered
                        .sort((a, c) => a.id - c.id)
                        .map(task => {
                            const item = new TodoTreeItem(
                                { kind: 'task', task },
                                task.text,
                                vscode.TreeItemCollapsibleState.None
                            );
                            item.description = `#${task.id}` + (task.due ? ` • ${task.due}` : '');
                            item.iconPath = new vscode.ThemeIcon('checklist');
                            item.command = {
                                command: 'todo-cli.tree.openTask',
                                title: 'Show Task Details',
                                arguments: [task],
                            };
                            return item;
                        });
                }

                return [];
            }
        }

        const provider = new TodoTreeDataProvider(todoStatusBar);
        todoTreeProvider = provider;
        context.subscriptions.push(vscode.window.registerTreeDataProvider('todo-cli.todosView', provider));

        context.subscriptions.push(
            vscode.commands.registerCommand('todo-cli.tree.openTask', async (task: Task) => {
                const action = await vscode.window.showQuickPick(
                    [
                        { label: 'Toggle Done', key: 'toggle' },
                        { label: 'Edit', key: 'edit' },
                        { label: 'Delete', key: 'delete' },
                        { label: 'Change Priority', key: 'priority' },
                        { label: 'Add Tag', key: 'tag' },
                    ],
                    { placeHolder: `#${task.id}: ${task.text}` }
                );
                if (!action) return;

                const nowIso = () => new Date().toISOString();

                if (action.key === 'toggle') {
                    todoStatusBar.updateDatabase(db => {
                        const t = db.tasks.find(x => x.id === task.id);
                        if (!t) return;
                        t.done = !t.done;
                        t.done_at = t.done ? nowIso() : '';
                    });
                } else if (action.key === 'edit') {
                    const text = await vscode.window.showInputBox({ prompt: 'Edit task text', value: task.text });
                    if (text === undefined) return;
                    todoStatusBar.updateDatabase(db => {
                        const t = db.tasks.find(x => x.id === task.id);
                        if (!t) return;
                        t.text = text.trim();
                    });
                } else if (action.key === 'delete') {
                    const confirm = await vscode.window.showWarningMessage(`Delete task #${task.id}?`, { modal: true }, 'Delete');
                    if (confirm !== 'Delete') return;
                    todoStatusBar.updateDatabase(db => {
                        db.tasks = db.tasks.filter(x => x.id !== task.id);
                    });
                } else if (action.key === 'priority') {
                    const choice = await vscode.window.showQuickPick(
                        ['high', 'med', 'low', '(none)'],
                        { placeHolder: `Priority for #${task.id}` }
                    );
                    if (!choice) return;
                    const value = choice === '(none)' ? '' : choice;
                    todoStatusBar.updateDatabase(db => {
                        const t = db.tasks.find(x => x.id === task.id);
                        if (!t) return;
                        t.priority = value;
                    });
                } else if (action.key === 'tag') {
                    const tagInput = await vscode.window.showInputBox({ prompt: 'Add tag(s) (comma/space separated)' });
                    if (!tagInput) return;
                    const tags = tagInput.split(/[, ]+/).map(s => s.trim()).filter(Boolean);
                    if (!tags.length) return;
                    todoStatusBar.updateDatabase(db => {
                        const t = db.tasks.find(x => x.id === task.id);
                        if (!t) return;
                        const existing = new Set((t.tags || []).map(x => x.trim()).filter(Boolean));
                        for (const tg of tags) existing.add(tg);
                        t.tags = Array.from(existing).sort();
                    });
                }

                provider.refresh();
                // status bar refresh happens via updateStatus() calls; force one here
                vscode.commands.executeCommand('todo-cli.refresh');
            })
        );
        
        // Check if we should create default database on first activation
        const isFirstActivation = context.globalState.get<boolean>('todo-cli.firstActivation', true);
        if (isFirstActivation) {
            // Try to create default database if it doesn't exist
            const dbPath = todoStatusBar.resolveDbPath();
            if (!fs.existsSync(dbPath)) {
                const created = todoStatusBar.initializeDefaultDatabase(dbPath);
                if (created) {
                    // Show notification after a short delay to let status bar initialize
                    setTimeout(() => {
                        vscode.window.showInformationMessage(
                            `✅ Todo CLI: Created default database at ${dbPath}`,
                            'Change Path', 'Open File'
                        ).then(selection => {
                            if (selection === 'Change Path') {
                                vscode.commands.executeCommand('todo-cli.configure');
                            } else if (selection === 'Open File') {
                                const fileUri = vscode.Uri.file(dbPath);
                                vscode.commands.executeCommand('vscode.open', fileUri);
                            }
                        });
                    }, 1000);
                }
            }
            context.globalState.update('todo-cli.firstActivation', false);
        }
        
        // Extension activated successfully
    } catch (error) {
        console.error('Failed to activate Todo CLI Extension:', error);
        vscode.window.showErrorMessage(`Todo CLI Extension failed to activate: ${error}`);
    }
}

export function deactivate() {}

