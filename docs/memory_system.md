# Memory System for AI Coder

The memory system provides persistent storage of project-specific knowledge, decisions, and solutions that survive across AI Coder sessions.

## Features

- **Project-scoped memory**: Each project has its own memory database in `.aicoder/memory.db`
- **Simple SQLite backend**: Reliable, fast, and requires no external dependencies
- **Full-text search**: Find relevant notes quickly
- **Tag system**: Organize notes with custom tags
- **Auto-save**: Automatically capture important decisions
- **Plugin extensible**: Easy to extend with custom backends

## Usage

### Memory Tool Operations

The memory system provides a single `memory` tool with multiple operations:

#### Create a Note
```python
memory(operation="create", name="api_setup", content="Use OAuth2 with JWT tokens", tags=["api", "auth"])
```

#### Update a Note

```python
memory(operation="update", name="api_setup", content="Use OAuth2 with refresh tokens", tags=["api", "auth", "updated"])
```

#### Read a Note
```python
memory(operation="read", name="api_setup")
```

#### Search Notes
```python
memory(operation="search", query="authentication", limit=10)
```

#### List All Notes
```python
memory(operation="list", limit=20, sort_by="updated_at")
```

#### Get Statistics
```python
memory(operation="stats")
```

#### Delete a Note
```python
memory(operation="delete", name="old_note")
```

#### Auto-save Decision
```python
memory(operation="auto_save", name="debug_session_001", 
       context="API calls were failing with timeout errors", 
       content="Increased timeout from 30s to 60s in config.yaml",
       tags=["debugging", "api"])
```

## Storage

Memory notes are stored in SQLite database at:
```
project_directory/
├── .aicoder/
│   ├── memory.db          # Main memory database
│   └── memory.db-wal     # Write-ahead log (SQLite)
```

### Database Schema

```sql
CREATE TABLE notes (
    name TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    tags TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Plugin Development

The memory system is designed to be easily extensible through monkey-patching:

### Simple Example

```python
# ~/.config/aicoder/plugins/memory_enhancement.py
import aicoder.memory

# Store original method
original_create = aicoder.memory.ProjectMemory.create

def enhanced_create(self, name, content, tags=None):
    # Add custom logic
    print(f"Creating note: {name}")
    
    # Call original
    result = original_create(self, name, content, tags)
    
    # Additional logic
    if "important" in content.lower():
        print("⚠️  Important note created!")
    
    return result

# Monkey patch
aicoder.memory.ProjectMemory.create = enhanced_create
```

### Cloud Sync Example

See `docs/plugins/examples/unstable/memory_cloud_sync/memory_cloud_sync.py` for a complete example of adding cloud synchronization.

## Best Practices

### Naming Conventions
- Use descriptive names: `api_setup`, `debug_session_001`, `architecture_decision`
- Include timestamps for auto-saved items: `decision_20251021_182158`
- Use consistent prefixes for related notes: `build_`, `debug_`, `config_`

### Tag Usage
- Use consistent tag names: `api`, `database`, `debugging`, `security`
- Tag by category: `component:auth`, `type:bugfix`, `priority:high`
- Use auto-generated tags: `auto-saved`, `decision`, `solution`

### Content Guidelines
- Be specific and include context
- Include code examples when relevant
- Note the date and reasoning for decisions
- Include "what didn't work" as well as solutions

## Performance

- **Database size**: Optimized for thousands of notes
- **Search speed**: Fast text matching with indexes
- **Concurrent access**: Safe for multiple AI Coder instances
- **Backup**: Simply copy `.aicoder/memory.db`

## Troubleshooting

### Database Corruption
If the memory database becomes corrupted:
```bash
# Backup current database
cp .aicoder/memory.db .aicoder/memory.db.backup

# Create new database (old data will be lost)
rm .aicoder/memory.db
```

### Large Databases
For projects with many notes:
- Use specific search queries rather than listing all notes
- Clean up old notes with `memory(operation="delete", name="old_note")`
- Use tags to organize and filter notes

### Performance Issues
- Database indexes are automatically maintained
- Search uses `LIKE` matching for simplicity
- Consider using tags for better organization

## Integration with AI Coder

The memory system integrates automatically with AI Coder:
- Initialized at startup in `app.py`
- Available as `self.project_memory` in the main application
- Auto-approved tool for seamless AI assistance
- Statistics tracked in the main stats system

## Future Enhancements

Potential improvements for future versions:
- Full-text search with FTS5
- Memory export/import functionality
- Memory analytics and insights
- Collaborative memory sharing
- Version history for notes
- Automatic memory cleanup and archiving