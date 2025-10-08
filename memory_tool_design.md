# Memory Tool Implementation Plan

## Overview

Design and implement a memory tool for AI Coder that allows persistent storage and retrieval of notes between sessions, supporting both project-specific and global memory scopes.

## Architecture Analysis

Based on AI Coder's existing patterns:
- **Global storage**: `~/.config/aicoder/` (used for plugins, MCP tools)
- **Project storage**: `.aicoder/` (already used by session manager plugin)
- **Tool system**: Internal tools in `aicoder/tool_manager/internal_tools/`
- **Auto-approval**: Available for seamless user experience

## Proposed Hybrid Memory System

### Dual-Scope Architecture

#### Primary: Project-Specific Memory (`./.aicoder/memory/`)
- **Purpose**: Project-specific knowledge, architecture decisions, build configurations
- **Benefits**: Context isolation, Git integration, portability, team sharing
- **Use Cases**: 
  - Architecture decisions specific to codebase
  - Build configurations and debugging solutions
  - Project-specific user preferences
  - Relevant code snippets and solutions

#### Secondary: Global Memory (`~/.config/aicoder/memory/`)
- **Purpose**: Personal preferences, cross-project knowledge, reusable patterns
- **Benefits**: Personal growth accumulation, tool configurations, generic solutions
- **Use Cases**:
  - Personal coding preferences and patterns
  - Generic debugging approaches
  - Favorite command aliases and snippets
  - Cross-project reusable solutions

## Memory Tool API Design

### Core Functions
```python
memory_create(name, content, tags=[], scope="project")  # Create note
memory_read(name, scope="project")                      # Read specific note
memory_list(search="", tags=[], scope="both")           # List/filter notes
memory_edit(name, content, scope="project")             # Update existing note
memory_delete(name, scope="project")                    # Remove note
memory_search(query, scope="both")                      # Full-text search
```

### Smart Resolution Logic
1. **Project-First**: Always search project memory first
2. **Global Fallback**: Fall back to global memory if not found locally
3. **Scope-Aware**: Tools know which scope they're operating in
4. **Explicit Override**: Users can specify scope explicitly

## Directory Structure

```
project-directory/
├── .aicoder/
│   ├── memory/
│   │   ├── architecture_decisions.json
│   │   ├── build_issues.json
│   │   └── index.json
│   └── sessions/
│       └── ...

~/.config/aicoder/
├── memory/
│   ├── personal_preferences.json
│   ├── reusable_snippets.json
│   └── index.json
├── plugins/
└── mcp_tools.json
```

## Implementation Strategy

### Phase 1: Core Memory Operations
- Create `memory_create.py`, `memory_read.py`, `memory_list.py` tools
- Implement dual-scope storage (project + global)
- JSON-based storage with indexing for quick lookups
- Auto-approved tool definitions for seamless UX

### Phase 2: Enhanced Features
- Search functionality with `memory_search.py`
- Tag system for categorization
- Backup/restore capabilities
- Smart resolution logic implementation

### Phase 3: Integration Features
- Automatic context summaries saved to memory
- Smart suggestions based on existing notes
- Export/import capabilities
- Git integration options for project memory

## Technical Implementation Details

### Tool Structure
Each memory tool will follow AI Coder's internal tool pattern:
```python
# memory_create.py
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "approval_excludes_arguments": False,
    "description": "Creates a new memory note with optional tags and scope.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Unique name for the note"},
            "content": {"type": "string", "description": "Note content"},
            "tags": {"type": "array", "description": "Optional tags for categorization"},
            "scope": {"type": "string", "enum": ["project", "global"], "description": "Storage scope"}
        },
        "required": ["name", "content"],
        "additionalProperties": False,
    },
}

def execute_memory_create(name: str, content: str, stats, tags: list = None, scope: str = "project") -> str:
    # Implementation
```

### Storage Format
```json
{
  "name": "api_key_rotation",
  "content": "Remember to rotate API keys every 90 days...",
  "tags": ["security", "maintenance"],
  "created_at": "2025-10-08T03:07:11Z",
  "updated_at": "2025-10-08T03:07:11Z",
  "scope": "project"
}
```

## Benefits

### For Users
- **Session Persistence**: Notes survive AI session restarts
- **Context Retention**: Remember important decisions and configurations
- **Quick Reference**: Access frequently used information without file hunting
- **Knowledge Building**: Accumulate project-specific insights over time
- **Reduced Repetition**: Avoid re-solving the same problems across sessions

### For Development Workflow
- **Project Memory**: Becomes part of project's knowledge base
- **Team Collaboration**: Share useful project insights via Git
- **Personal Growth**: Global memory captures programming evolution
- **Context Awareness**: AI remembers project-specific details

## Git Integration Strategy

### Project Memory
- `.aicoder/memory/` can be committed (optional)
- Teams can share useful project insights
- Sensitive notes can be excluded via `.gitignore`

### Global Memory
- Remains personal and private
- Never committed to version control
- Purely for personal knowledge accumulation

## Success Metrics

- Tool adoption rate and usage frequency
- User feedback on memory persistence benefits
- Reduction in repeated problem-solving scenarios
- Improved context retention across sessions
- Team collaboration improvements (for project memory)

## Next Steps

1. **Phase 1 Implementation**: Core memory operations with dual-scope support
2. **Testing**: Comprehensive test coverage for all memory operations
3. **Documentation**: User guide and API reference
4. **Integration**: Seamless integration with existing AI Coder workflow
5. **Iteration**: User feedback and feature enhancements

This hybrid approach provides the best of both worlds - project-specific context isolation combined with personal knowledge accumulation, following AI Coder's existing architectural patterns while delivering significant value to users.