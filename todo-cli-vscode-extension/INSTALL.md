# Installing the VSIX Extension in Cursor

## Method 1: Using Command Palette (Recommended)

1. **Open Cursor**

2. **Open Command Palette:**
   - Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
   - Or: View → Command Palette

3. **Install from VSIX:**
   - Type: `Extensions: Install from VSIX...`
   - Select it from the dropdown

4. **Select the VSIX file:**
   - Navigate to: `todo-cli-vscode-extension/todo-cli-status-0.1.0.vsix`
   - Click "Install"

5. **Reload Cursor:**
   - You'll see a notification to reload
   - Click "Reload" or press `Cmd+R` / `Ctrl+R`

## Method 2: Using Terminal/Command Line

1. **Open Terminal in Cursor:**
   - Terminal → New Terminal
   - Or: `` Ctrl+` `` (backtick)

2. **Install using command:**
   ```bash
   cursor --install-extension todo-cli-status-0.1.0.vsix
   ```

   Or with full path:
   ```bash
   cursor --install-extension /Users/pritaman/Documents/Projects/lorezu_agent_todo/todo-cli-vscode-extension/todo-cli-status-0.1.0.vsix
   ```

3. **Reload Cursor** when prompted

## Method 3: Drag and Drop (if supported)

1. **Open Extensions view:**
   - Click the Extensions icon in the sidebar (or `Cmd+Shift+X` / `Ctrl+Shift+X`)

2. **Drag the VSIX file:**
   - Drag `todo-cli-status-0.1.0.vsix` into the Extensions view
   - Cursor should prompt to install

## Verify Installation

1. **Check Extensions:**
   - Go to Extensions (`Cmd+Shift+X` / `Ctrl+Shift+X`)
   - Search for "Todo CLI Status"
   - You should see it listed as installed

2. **Check Status Bar:**
   - Look at the **bottom right** of Cursor's status bar
   - You should see: `$(checklist) Todo: Loading...` or your todo stats

3. **Test Commands:**
   - Press `Cmd+Shift+P` / `Ctrl+Shift+P`
   - Type: `Todo CLI: Refresh Todo Status`
   - The command should appear

## Troubleshooting

### Extension not showing in status bar?

1. **Check if it's enabled:**
   - Extensions → Search "Todo CLI Status"
   - Make sure it's enabled (not disabled)

2. **Check Output logs:**
   - View → Output
   - Select "Log (Extension Host)"
   - Look for "Todo CLI Extension is now active!"

3. **Reload Cursor:**
   - `Cmd+Shift+P` → "Developer: Reload Window"

4. **Check Developer Console:**
   - Help → Toggle Developer Tools
   - Check Console tab for errors

### Extension not installing?

1. **Check VSIX file exists:**
   ```bash
   ls -lh todo-cli-status-0.1.0.vsix
   ```

2. **Try reinstalling:**
   - Uninstall first: Extensions → Todo CLI Status → Uninstall
   - Then reinstall using Method 1 or 2

3. **Check Cursor version:**
   - Help → About
   - Make sure you're on a recent version (extension requires Cursor/VSCode 1.74+)

## After Installation

The extension will:
- ✅ Show todo stats in the status bar (bottom right)
- ✅ Auto-refresh every 5 seconds
- ✅ Allow clicking to view tasks
- ✅ Work with your existing todo-cli database

**First time setup:**
- If you see "Todo: No database", create some todos:
  ```bash
  todo init
  todo add "My first task"
  ```
- The status bar will update automatically!

