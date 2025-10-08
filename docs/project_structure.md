# AI Coder Project Structure

This document provides the complete project structure for AI Coder development.

## Directory Structure

```
aicoder/
├── AICODER.md                    # Main system prompt
├── __init__.py                   # (4.0K) Package initialization
├── __main__.py                   # (4.0K) Entry point
├── animator.py                   # (8.0K) Terminal animations
├── api_client.py                 # (8.0K) API client logic
├── api_handler.py                # (12K) API request handling
├── app.py                        # (24K) Main application class
├── command_handlers.py           # (12K) Command processing
├── config.py                     # (8.0K) Configuration management
├── file_tracker.py               # (4.0K) File change tracking
├── input_handler.py              # (4.0K) User input processing
├── message_history.py            # (24K) Message and memory management
├── retry_utils.py                # (12K) Retry logic
├── stats.py                      # (8.0K) Usage statistics
├── streaming_adapter.py          # (68K) Streaming response handling
├── tool_call_executor.py         # (4.0K) Tool execution
└── utils.py                      # (20K) Utility functions
└── plugin_system/                # Plugin system
    ├── __init__.py               # (4.0K)
    └── loader.py                 # (4.0K)
└── tool_manager/                 # Tool management system
    ├── __init__.py               # (4.0K)
    ├── approval_system.py        # (12K) Tool approval logic
    ├── executor.py               # (44K) Tool execution engine
    ├── manager.py                # (4.0K) Tool manager
    ├── registry.py               # (16K) Tool registration
    ├── validator.py              # (12K) Tool validation
    └── internal_tools/           # Built-in tools
        ├── __init__.py           # (4.0K)
        ├── edit_file.py          # (12K) File editing
        ├── glob.py               # (4.0K) File pattern matching
        ├── grep.py               # (4.0K) Text search
        ├── list_directory.py     # (4.0K) Directory listing
        ├── pwd.py                # (4.0K) Current directory
        ├── read_file.py          # (4.0K) File reading
        ├── run_shell_command.py  # (4.0K) Shell commands
        └── write_file.py         # (4.0K) File writing
```

## File Size Indicators

The file sizes in parentheses are approximate and help identify the most significant components:

- **Large components**: `streaming_adapter.py` (68K), `app.py` (24K), `message_history.py` (24K), `utils.py` (20K)
- **Core systems**: `api_handler.py` (12K), `tool_manager/executor.py` (44K), `tool_manager/registry.py` (16K)
- **Supporting modules**: Most other files are 4-12K, representing focused functionality

## Key Architectural Patterns

1. **Modular Design**: Clear separation between core functionality, tool management, and plugin system
2. **Mixin Pattern**: `app.py` uses multiple mixins for different capabilities
3. **Tool System**: Internal tools follow a consistent pattern in `tool_manager/internal_tools/`
4. **Plugin Architecture**: Extensible system for adding new capabilities
5. **Message Management**: Sophisticated conversation history with compaction

## Development Notes

- The main entry point is through `app.py` which coordinates all subsystems
- Tool management is centralized in the `tool_manager/` directory
- Plugin system allows for extending functionality without core modifications
- Message history includes advanced features like auto-compaction and session management