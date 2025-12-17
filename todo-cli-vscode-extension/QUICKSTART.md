# Quick Start Guide

## How to Test the Extension

### Option 1: Run in Extension Development Host (Recommended)

1. **Open the extension folder in VSCode:**
   ```bash
   cd todo-cli-vscode-extension
   code .
   ```

2. **Install dependencies (if not already done):**
   ```bash
   npm install
   ```

3. **Compile the extension:**
   ```bash
   npm run compile
   ```

4. **Press F5** or go to Run > Start Debugging
   - This will open a new VSCode window (Extension Development Host)
   - The extension will be loaded automatically

5. **Look for the status bar item:**
   - Check the **bottom right** of the status bar
   - You should see something like: `$(checklist) 5/3` or `$(checklist) Todo: No database`
   - If you see "No database", that's normal if you haven't created todos yet

### Option 2: Install as Extension

1. **Package the extension:**
   ```bash
   npm install -g vsce
   vsce package
   ```
   This creates a `.vsix` file

2. **Install the .vsix file:**
   - In VSCode: Extensions > ... > Install from VSIX
   - Select the generated `.vsix` file

### Troubleshooting

**If you don't see the status bar item:**

1. **Check the Output panel:**
   - View > Output
   - Select "Log (Extension Host)" from the dropdown
   - Look for "Todo CLI Extension is now active!" message
   - Check for any error messages

2. **Check Developer Tools:**
   - Help > Toggle Developer Tools
   - Look in the Console tab for errors

3. **Try the command manually:**
   - Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
   - Type "Todo CLI: Refresh Todo Status"
   - Run it and check if the status bar appears

4. **Check if you have todos:**
   - The extension needs a todo database to show stats
   - Run `todo init` in terminal first if you haven't
   - Or create some todos: `todo add "Test task"`

5. **Reload the window:**
   - Press `Cmd+R` (Mac) or `Ctrl+R` (Windows/Linux) in the Extension Development Host window
   - Or use Command Palette: "Developer: Reload Window"

### Expected Behavior

- **Status bar shows:** `$(checklist) X/Y` where X is pending and Y is done
- **If overdue:** Red background
- **If due today/high priority:** Yellow background  
- **If all done:** Green background
- **If no database:** Gray text "Todo: No database"

### Test Commands

1. **Refresh manually:**
   - Command Palette > "Todo CLI: Refresh Todo Status"

2. **Open todo list:**
   - Click the status bar item
   - Or Command Palette > "Todo CLI: Open Todo List"

3. **Configure database path:**
   - Command Palette > "Todo CLI: Configure Todo Database Path"

### Create Test Todos

If you don't have todos yet, create some:

```bash
todo add "Test task 1" --p high
todo add "Test task 2" --p med --due 2025-12-20
todo add "Test task 3"
todo ls
```

Then check the status bar - it should update automatically!

