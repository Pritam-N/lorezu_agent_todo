# How to Set Workspace Database Path

## Method 1: Using the Extension Command (Easiest)

### Step-by-Step:

1. **Open your workspace/folder in Cursor**
   - File → Open Folder (or `Cmd+O` / `Ctrl+O`)
   - Select your project folder

2. **Right-click on the Todo status bar item** (bottom right)
   - Look for the status bar item showing your todo count
   - Right-click on it

3. **Select "Configure Database Path"**
   - This opens the configuration menu

4. **Choose "Set Workspace Path"**
   - Select the option: `$(folder-opened) Set Workspace Path`
   - Description: "Set database path for this workspace only"

5. **Enter or browse for the path**
   - **Option A - Type path:**
     - Enter the path to your `todos.json` file
     - Examples:
       - `./todos.json` (in workspace root)
       - `~/Documents/my-project/todos.json` (absolute path)
       - `../shared-todos.json` (relative to workspace)
   
   - **Option B - Browse:**
     - Choose "Browse for File" first
     - Select "Workspace" scope
     - Use file picker to select `todos.json`

6. **Done!**
   - The extension will save the setting to `.vscode/settings.json`
   - Status bar will update automatically

---

## Method 2: Using Command Palette

### Step-by-Step:

1. **Open Command Palette**
   - Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
   - Or: View → Command Palette

2. **Type and select:**
   ```
   Todo CLI: Configure Database Path
   ```
   
   **If it doesn't appear:**
   - Try typing just: `Todo CLI` (then space)
   - Or: `@ext:todo-cli-status`
   - Or use Method 1 (right-click) instead

3. **Choose "Set Workspace Path"**
   - Select: `$(folder-opened) Set Workspace Path`

4. **Enter the path**
   - Type the path to your `todos.json` file
   - Or choose "Browse for File" → "Workspace"

5. **Done!**

**Note:** If the command doesn't appear, see [FIND_COMMAND.md](FIND_COMMAND.md) for troubleshooting.

---

## Method 3: Direct JSON Editing (Advanced)

### Step-by-Step:

1. **Open workspace settings**
   - Press `Cmd+Shift+P` / `Ctrl+Shift+P`
   - Type: `Preferences: Open Workspace Settings (JSON)`
   - Or create/edit `.vscode/settings.json` in your workspace root

2. **Add the setting:**
   ```json
   {
     "todo-cli.dbPath": "path/to/your/todos.json"
   }
   ```

3. **Examples:**

   **Relative to workspace root:**
   ```json
   {
     "todo-cli.dbPath": "./todos.json"
   }
   ```

   **Absolute path:**
   ```json
   {
     "todo-cli.dbPath": "~/Documents/my-project/todos.json"
   }
   ```

   **In a subdirectory:**
   ```json
   {
     "todo-cli.dbPath": "./data/todos.json"
   }
   ```

4. **Save the file**
   - The extension will detect the change automatically

---

## Method 4: Using Settings UI

### Step-by-Step:

1. **Open Settings**
   - Press `Cmd+,` (Mac) or `Ctrl+,` (Windows/Linux)
   - Or: Code → Preferences → Settings

2. **Search for:**
   ```
   todo-cli.dbPath
   ```

3. **Click the edit icon** (pencil) next to the setting
   - Choose "Edit in settings.json"
   - Or use the dropdown to select "Workspace" tab

4. **Enter the path**
   - Type your database path
   - Make sure you're editing the **Workspace** tab (not User)

5. **Save**

---

## Verify It's Working

### Check Current Path:

1. **Right-click status bar** → "Show Current Path"
   - Should show: "Using workspace setting"

2. **Or Command Palette:**
   ```
   Todo CLI: Show Current Database Path
   ```
   - Look for "Current Resolution: Using workspace setting"

3. **Check the file:**
   - Look for `.vscode/settings.json` in your workspace
   - Should contain: `"todo-cli.dbPath": "your-path"`

---

## Common Path Examples

### Project-specific todos (recommended):
```json
{
  "todo-cli.dbPath": "./todos.json"
}
```
Stores todos in your project root.

### Shared todos across projects:
```json
{
  "todo-cli.dbPath": "~/Documents/shared-todos.json"
}
```

### Todos in a data folder:
```json
{
  "todo-cli.dbPath": "./data/todos.json"
}
```

### Absolute path:
```json
{
  "todo-cli.dbPath": "/Users/yourname/projects/myproject/todos.json"
}
```

---

## Troubleshooting

### Workspace setting not working?

1. **Check if workspace is open:**
   - File → Open Folder
   - You need a folder open (not just files)

2. **Check `.vscode/settings.json`:**
   - Should exist in workspace root
   - Should contain `todo-cli.dbPath`

3. **Reload window:**
   - `Cmd+Shift+P` → "Developer: Reload Window"

4. **Check status bar:**
   - Right-click → "Show Current Path"
   - Verify it says "Using workspace setting"

### Want to remove workspace setting?

1. **Right-click status bar** → "Configure Database Path"
2. **Choose:** "Clear Workspace Setting"
3. **Confirm removal**

Or edit `.vscode/settings.json` and remove the `todo-cli.dbPath` line.

---

## Quick Reference

| Action | Command |
|--------|---------|
| Configure Path | Right-click status bar → Configure Database Path |
| Show Current Path | Right-click status bar → Show Current Path |
| Open Settings | Right-click status bar → Open Settings |
| Command Palette | `Cmd+Shift+P` → "Todo CLI: Configure Database Path" |

---

## Example Workflow

1. **Open your project:** `File → Open Folder`
2. **Right-click Todo status bar** → "Configure Database Path"
3. **Select:** "Set Workspace Path"
4. **Enter:** `./todos.json` (or browse to select file)
5. **Done!** Your project now has its own todo database

The `.vscode/settings.json` file will be created automatically with:
```json
{
  "todo-cli.dbPath": "./todos.json"
}
```

