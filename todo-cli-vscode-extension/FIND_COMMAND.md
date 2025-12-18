# How to Find "Configure Database Path" Command

## If Command Doesn't Appear

### Step 1: Verify Extension is Installed

1. **Open Extensions view:**
   - Click Extensions icon in sidebar (`Cmd+Shift+X` / `Ctrl+Shift+X`)
   - Or: View → Extensions

2. **Search for:**
   ```
   Todo CLI Status
   ```

3. **Check if installed:**
   - Should show "Todo CLI Status" extension
   - Should be **enabled** (not disabled)

### Step 2: Reload Window

After installing/updating:
1. Press `Cmd+Shift+P` / `Ctrl+Shift+P`
2. Type: `Developer: Reload Window`
3. Press Enter
4. Wait for window to reload

### Step 3: Search for Command

**Method A - Full command name:**
1. Press `Cmd+Shift+P` / `Ctrl+Shift+P`
2. Type exactly: `Todo CLI: Configure Database Path`
3. Should appear in dropdown

**Method B - Partial search:**
1. Press `Cmd+Shift+P` / `Ctrl+Shift+P`
2. Type: `Todo CLI` (then space)
3. All Todo CLI commands will appear
4. Select "Configure Database Path"

**Method C - By category:**
1. Press `Cmd+Shift+P` / `Ctrl+Shift+P`
2. Type: `@ext:todo-cli-status`
3. Shows all commands from this extension

**Method D - Right-click status bar:**
1. Look at **bottom right** of Cursor window
2. Find the Todo status bar item (shows todo count)
3. **Right-click** on it
4. Select "Configure Database Path" from context menu

### Step 4: Check Extension Activation

1. **Open Output panel:**
   - View → Output
   - Or: `Cmd+Shift+U` / `Ctrl+Shift+U`

2. **Select dropdown:**
   - Choose "Log (Extension Host)"

3. **Look for:**
   ```
   Todo CLI Extension is now active!
   ```

4. **If not there:**
   - Extension might not be activating
   - Check for errors in the log

### Step 5: Verify Command Registration

1. **Open Developer Tools:**
   - Help → Toggle Developer Tools
   - Or: `Cmd+Option+I` / `Ctrl+Shift+I`

2. **Go to Console tab**

3. **Type:**
   ```javascript
   vscode.commands.getCommands().then(commands => console.log(commands.filter(c => c.includes('todo-cli-status'))))
   ```

4. **Should see:**
   - `todo-cli-status.configure`
   - `todo-cli-status.refresh`
   - `todo-cli-status.openList`
   - etc.

## Alternative: Use Right-Click Menu

**Easiest method if command doesn't appear:**

1. **Find status bar item** (bottom right)
   - Shows: `$(checklist) X/Y` or similar
   - Or: `Todo: Loading...`

2. **Right-click** on it

3. **Select:** "Configure Database Path"

4. **Choose:** "Set Workspace Path"

5. **Enter path** or browse

## Still Not Working?

### Reinstall Extension:

1. **Uninstall:**
   - Extensions → Search "Todo CLI Status"
   - Click gear icon → Uninstall

2. **Reload window**

3. **Reinstall:**
   - Install from VSIX file again
   - Or use the updated VSIX

4. **Reload window again**

### Check Extension Version:

Make sure you have the latest VSIX:
- File: `todo-cli-status-*.vsix`
 - Rebuild with: `npx --yes @vscode/vsce package --allow-missing-repository`

### Manual Configuration:

If commands still don't work, configure manually:

1. **Open workspace settings:**
   - `Cmd+Shift+P` → `Preferences: Open Workspace Settings (JSON)`

2. **Add:**
   ```json
   {
     "todo-cli.dbPath": "./todos.json"
   }
   ```

3. **Save file**

4. **Status bar should update automatically**

## Quick Test

To verify extension is working:

1. **Check status bar** (bottom right)
   - Should show Todo count or "No database"

2. **Right-click status bar**
   - Should show context menu with Todo CLI options

3. **Command Palette:**
   - Type: `Todo CLI`
   - Should show at least 5 commands

If none of these work, the extension may not be properly installed.

