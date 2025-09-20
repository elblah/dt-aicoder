# Session Manager Plugin

This plugin provides automatic session management for AI Coder, automatically saving and loading conversation sessions.

## Features

- Automatic session management with timestamped sessions
- Auto-save on exit and manual save capability
- Session loading and creation
- Session renaming and deletion
- Compatible with existing `/save` and `/load` commands

## Installation

1. Copy the `session_manager` directory to your AI Coder plugins directory:
   ```bash
   cp -r session_manager ~/.config/aicoder/plugins/
   ```

2. Run AI Coder - the session manager will be automatically available

## How It Works

The plugin automatically manages your conversation sessions:

1. **On startup**: Loads the last session or creates a new one
2. **During use**: Tracks your conversation automatically
3. **On exit**: Automatically saves the current session
4. **Manual control**: Use `/sessions` commands for additional control

Sessions are stored in `.aicoder/sessions/` in your current project directory by default.

## Usage

The plugin adds the `/sessions` command with the following subcommands:

### List Sessions
```
/sessions
/sessions list
/sessions ls
```
Lists all available sessions with their names.

### Load Session
```
/sessions load <session_name>
```
Load a specific session by name (without .json extension).

### Save Session
```
/sessions save
```
Manually save the current session.

### Create New Session
```
/sessions new [session_name]
```
Create a new session. If no name is provided, creates an "unnamed" session.

### Delete Session
```
/sessions delete <session_name>
```
Delete a specific session.

### Rename Current Session
```
/sessions rename <new_name>
```
Rename the currently loaded session.

### Show Session Info
```
/sessions info
```
Show detailed information about the current session.

## Example Output

```
✅ Loaded session: session_2025-01-15_14-30-22__Defining_AICoder_Journey

...

📋 Available Sessions:
============================================================
session_2025-01-15_14-30-22__Defining_AICoder_Journey (current)
session_2025-01-14_10-15-30__unnamed
session_2025-01-13_09-45-15__Project_Planning
```

## Session Naming

Sessions are automatically named with the format:
- `session_YYYY-MM-DD_HH-MM-SS__<name>.json`

Default sessions use "unnamed" until renamed:
- `session_2025-01-15_14-30-22__unnamed.json`

After renaming:
- `session_2025-01-15_14-30-22__My_Project_Name.json`

## Configuration

### Session Directory
By default, sessions are stored in:
```
./.aicoder/sessions/
```

You can override this location with the `AICODER_SESSIONS_DIR` environment variable:
```bash
export AICODER_SESSIONS_DIR=/path/to/your/sessions
```

## Benefits

- **Automatic management**: No need to manually save/load sessions
- **Transparent operation**: You're always aware of which session you're using
- **Project-based**: Sessions stored with your project
- **Compatible**: Works alongside existing `/save` and `/load` commands
- **Simple naming**: Easy to identify sessions by name and date
- **No file extensions**: Clean, user-friendly session names

## How Session Loading Works

1. On startup, the plugin looks for `.aicoder/sessions/session_current.json`
2. If found, it loads the session referenced in that file
3. If not found, it creates a new session
4. The `session_current.json` file tracks which session is active

## Limitations

- Sessions are project-specific (stored in current directory)
- No automatic conflict resolution for simultaneous access
- Manual session management commands affect only the current session context