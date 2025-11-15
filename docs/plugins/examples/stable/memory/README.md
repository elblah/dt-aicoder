# Memory Plugin

This plugin provides a project memory management system that allows AI Coder to store and retrieve project-specific knowledge across sessions.

## Features

- **Persistent Storage**: SQLite-based storage in `.aicoder/memory.db`
- **AI Integration**: Memory tool available for AI to use automatically
- **User Commands**: `/memory` and `/m` commands for manual management
- **Search & Organization**: Tag-based categorization and full-text search
- **Statistics**: Track usage and access patterns

## Installation

Since this plugin is in the firejail-protected project directory, you need to install it manually:

```bash
# Copy the plugin to your user plugins directory
cp /home/blah/poc/aicoder/v2/docs/plugins/examples/stable/memory/memory.py ~/.config/aicoder/plugins/

# Restart AI Coder to load the plugin
```

## Usage

### User Commands

- `/memory` - Show memory system status
- `/memory help` - Show help
- `/memory list` - List all memory notes
- `/memory search <query>` - Search memory notes
- `/memory stats` - Show memory statistics

### AI Tool Usage

The AI can use the `memory` tool with these operations:

- **create**: Store new information
- **read**: Retrieve stored information  
- **search**: Find relevant information
- **list**: Browse all stored notes
- **delete**: Remove memory notes
- **stats**: Get system statistics
- **auto_save**: Automatically save decisions

## Example AI Usage

```python
# Store a project decision
{
    "name": "memory",
    "arguments": {
        "operation": "create",
        "name": "api_authentication_decision",
        "content": "Decided to use JWT tokens for API authentication instead of session cookies for better scalability",
        "tags": ["architecture", "api", "security", "decision"]
    }
}

# Search for API-related information
{
    "name": "memory", 
    "arguments": {
        "operation": "search",
        "query": "api authentication",
        "limit": 5
    }
}

# Auto-save a decision
{
    "name": "memory",
    "arguments": {
        "operation": "auto_save",
        "context": "Changed database schema to add user_roles table for RBAC implementation"
    }
}
```

## Storage

Memory is stored per project in:
```
<project_root>/.aicoder/memory.db
```

The database contains a single `notes` table with:
- `name`: Primary key (note identifier)
- `content`: Note content
- `tags`: Comma-separated tags
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `access_count`: Number of times accessed
- `last_accessed`: Last access timestamp

## Migration from Core

This plugin replaces the core memory functionality. To migrate:

1. Install this plugin
2. Remove the memory command from core (if needed)
3. The plugin maintains full compatibility with existing memory data

## Benefits

- **Reduced Core Size**: Memory functionality moved to optional plugin
- **Modularity**: Clear separation of concerns
- **Maintainability**: Easier to update and extend memory features
- **User Choice**: Can be disabled if not needed

## Testing Results

All tests pass:
- ✅ ProjectMemory class functionality
- ✅ execute_memory function  
- ✅ Tool definition structure
- ✅ Integration with plugin system
- ✅ Tag preservation during updates
- ✅ Auto-save naming behavior  
- ✅ Tag management (create, preserve, update, clear)
- ✅ Access counter increments correctly
- ✅ Storage size with explanatory notes

## Issues Fixed

### 1. Tag Preservation ✅
- **Problem**: Tags were lost during updates
- **Fix**: Preserve existing tags when no new tags provided
- **Result**: Updates now maintain metadata correctly

### 2. Access Counter ✅  
- **Problem**: Access count wasn't incrementing
- **Fix**: Added missing commit() after UPDATE statement
- **Result**: Now correctly tracks all note reads

### 3. Auto-save Naming ✅
- **Problem**: Always generated names instead of using provided ones
- **Fix**: Added optional name parameter with fallback to generated ID
- **Result**: Respects user-provided names while maintaining auto-save convenience

Ready for installation and use. All identified issues have been resolved.