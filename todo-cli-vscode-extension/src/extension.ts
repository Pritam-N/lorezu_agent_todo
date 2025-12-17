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

class TodoStatusBar {
    private statusBarItem: vscode.StatusBarItem;
    private refreshTimer?: NodeJS.Timeout;
    private config: vscode.WorkspaceConfiguration;

    constructor(context: vscode.ExtensionContext) {
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

    private resolveDbPath(): string {
        // 1. Check VSCode config (workspace first, then global)
        const workspaceConfig = vscode.workspace.getConfiguration('todo-cli').get<string>('dbPath', '');
        const globalConfig = vscode.workspace.getConfiguration('todo-cli', null).get<string>('dbPath', '');
        
        // Prefer workspace setting over global
        const configPath = workspaceConfig || globalConfig;
        const configScope = workspaceConfig ? 'workspace' : (globalConfig ? 'global' : 'none');
        
        if (configPath) {
            const resolved = this.expandPath(configPath);
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
                        // Handle relative paths - try multiple resolution strategies
                        if (!path.isAbsolute(dbPath)) {
                            // Strategy 1: Relative to config directory
                            const relativeToConfig = path.resolve(configDir, dbPath);
                            if (fs.existsSync(relativeToConfig)) {
                                console.log(`[Todo CLI] Found relative to config dir: ${relativeToConfig}`);
                                return relativeToConfig;
                            }
                            
                            // Strategy 2: Relative to home directory
                            const relativeToHome = path.resolve(os.homedir(), dbPath);
                            if (fs.existsSync(relativeToHome)) {
                                console.log(`[Todo CLI] Found relative to home: ${relativeToHome}`);
                                return relativeToHome;
                            }
                            
                            // Strategy 3: Try in Documents/todo-cli (common default location)
                            const docsPath = path.join(os.homedir(), 'Documents', 'todo-cli', dbPath);
                            if (fs.existsSync(docsPath)) {
                                console.log(`[Todo CLI] Found in Documents/todo-cli: ${docsPath}`);
                                return docsPath;
                            }
                            
                            // Strategy 4: Expand and resolve (handles ~)
                            dbPath = this.expandPath(dbPath);
                            if (fs.existsSync(dbPath)) {
                                console.log(`[Todo CLI] Found after expansion: ${dbPath}`);
                                return dbPath;
                            }
                            
                            // If still not found, return the expanded path anyway (might be created later)
                            console.log(`[Todo CLI] Relative path not found, using: ${dbPath}`);
                            return dbPath;
                        } else {
                            // Absolute path - just expand ~
                            dbPath = this.expandPath(dbPath);
                            console.log(`[Todo CLI] Using absolute config path: ${dbPath}`);
                            return dbPath;
                        }
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

    private expandPath(filePath: string): string {
        // Expand ~ to home directory
        let expanded = filePath.replace(/^~/, os.homedir());
        // Resolve to absolute path
        return path.resolve(expanded);
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

    private loadTasks(): TodoDatabase | null {
        const dbPath = this.resolveDbPath();
        console.log(`[Todo CLI] Resolved DB path: ${dbPath}`);
        console.log(`[Todo CLI] Path exists: ${fs.existsSync(dbPath)}`);
        
        if (!fs.existsSync(dbPath)) {
            console.log(`[Todo CLI] Database file not found at: ${dbPath}`);
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
            console.log(`[Todo CLI] Loaded ${db.tasks.length} tasks from database`);
            return db;
        } catch (error) {
            console.error('[Todo CLI] Error loading todo database:', error);
            return null;
        }
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
                this.statusBarItem.text = '$(checklist) Todo: No database';
                this.statusBarItem.backgroundColor = undefined;
                this.statusBarItem.tooltip = `Todo database not found at:\n${dbPath}\n\nClick to configure.`;
                this.statusBarItem.show();
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
        } catch (error) {
            console.error('Todo CLI Extension Error:', error);
            this.statusBarItem.text = '$(error) Todo: Error';
            this.statusBarItem.tooltip = `Error loading todos: ${error}`;
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
            this.statusBarItem.show();
        }
    }

    private startAutoRefresh(): void {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        const interval = this.config.get<number>('refreshInterval', 5000);
        this.refreshTimer = setInterval(() => {
            this.updateStatus();
        }, interval);
    }

    private async openTodoList(): Promise<void> {
        const db = this.loadTasks();
        if (!db) {
            vscode.window.showInformationMessage('Todo database not found. Run "todo init" first.');
            return;
        }

        const stats = this.calculateStats(db);
        const pendingTasks = db.tasks.filter(t => !t.done);
        
        if (pendingTasks.length === 0) {
            vscode.window.showInformationMessage('No pending tasks! 🎉');
            return;
        }

        // Show quick pick with tasks
        const items = pendingTasks.map(task => ({
            label: `$(circle-outline) ${task.text}`,
            description: task.priority ? `Priority: ${task.priority}` : '',
            detail: task.due ? `Due: ${task.due}` : task.tags?.length ? `Tags: ${task.tags.join(', ')}` : '',
            task: task
        }));

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: `Select a task (${pendingTasks.length} pending)`,
            canPickMany: false
        });

        if (selected) {
            // Open terminal and run todo command
            const terminal = vscode.window.createTerminal('Todo CLI');
            terminal.sendText(`todo done ${selected.task.id}`);
            terminal.show();
        }
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
        
        // Extension activated successfully
    } catch (error) {
        console.error('Failed to activate Todo CLI Extension:', error);
        vscode.window.showErrorMessage(`Todo CLI Extension failed to activate: ${error}`);
    }
}

export function deactivate() {}

