# Session Manager Plugin Summary

## Overview
The Session Manager plugin provides automatic session management for AI Coder, handling the saving, loading, and organization of conversation sessions with minimal user intervention.

## Key Features
- **Automatic Session Management**: Creates and manages sessions automatically
- **Auto-save on Exit**: Preserves your work without manual intervention
- **Session Organization**: Timestamped sessions with meaningful naming
- **Simple Commands**: Intuitive `/sessions` command interface
- **Project-based Storage**: Sessions stored with your project files
- **Compatibility**: Works alongside existing save/load functionality

## How It Works
1. **Startup**: Automatically loads the last session or creates a new one
2. **Usage**: Tracks conversation history in the background
3. **Exit**: Automatically saves the session to preserve your work
4. **Management**: Use `/sessions` commands for additional control

## Session Storage
- **Default Location**: `./.aicoder/sessions/` in your current project directory
- **Environment Override**: `AICODER_SESSIONS_DIR` for custom location
- **File Naming**: `session_YYYY-MM-DD_HH-MM-SS__<name>.json`
- **Tracking**: `session_current.json` tracks the active session

## Available Commands
- `/sessions` - List all sessions
- `/sessions load <name>` - Load a specific session
- `/sessions save` - Manually save current session
- `/sessions new [name]` - Create new session
- `/sessions delete <name>` - Delete a session
- `/sessions rename <name>` - Rename current session
- `/sessions info` - Show session details

## Session Naming Convention
- **Default**: `session_2025-01-15_14-30-22__unnamed.json`
- **After Rename**: `session_2025-01-15_14-30-22__My_Project.json`
- **Sanitization**: Special characters converted to underscores

## Benefits
- No need to remember to save conversations
- Easy to organize and find previous work
- Project-specific session management
- Seamless integration with existing workflow
- Transparent operation with clear status feedback

## Technical Details
- Uses standard JSON format compatible with `/save` and `/load`
- Automatic directory creation if missing
- File-based session tracking for reliability
- Simple conflict handling (last write wins)
- Clean user interface with no file extensions shown

## Limitations
- Sessions are project-specific by default
- No advanced conflict resolution for simultaneous access
- Rename only works on current session (by design)
- Requires write access to session directory