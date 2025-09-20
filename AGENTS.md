# Agent Development Notes

## ⚠️ CRITICAL: Always Run Tests with YOLO_MODE=1

**WARNING: Tests that trigger tool approvals will hang indefinitely without YOLO_MODE=1**

Many tests in this project will trigger approval prompts (`input()` calls) that cause the test to hang waiting for user input. **This is the #1 reason LLMs fail when running tests.**

### ALWAYS run tests with YOLO_MODE=1:
```bash
# For individual test files
AICODER_THEME=original YOLO_MODE=1 python tests/test_aicoder.py
AICODER_THEME=original YOLO_MODE=1 python tests/test_internal_tools.py
AICODER_THEME=original YOLO_MODE=1 python tests/test_tool_manager.py

# For unittest discover
AICODER_THEME=original YOLO_MODE=1 python -m unittest discover

# For any test that might involve tool execution
AICODER_THEME=original YOLO_MODE=1 python your_test_script.py
```

### Why This Matters:
- Tests that execute tools will trigger approval prompts
- Without `YOLO_MODE=1`, these tests hang on `input()` calls
- LLMs constantly fail because they don't know about this requirement
- **This is not optional - it's mandatory for any test that might use tools**

### When to Use YOLO_MODE=1:
- ✅ **Always use** for any test in the `tests/` directory
- ✅ **Always use** for any test that involves tool execution
- ✅ **Always use** when running individual test files
- ✅ **Always use** when using `python -m unittest`

### The test_runner.py handles this automatically:
```bash
# These are safe - they set YOLO_MODE=1 and AICODER_THEME=original internally
python test_runner.py --quick
python test_runner.py --full
```

**MEMORIZE THIS: If a test might run tools, it needs YOLO_MODE=1**

---

## API Request Constraints
When working with free-tier API accounts that have a **limit on the number of requests per day** (rather than token usage), it's crucial to minimize the number of API calls:

### Key Principles:
1. **Minimize API requests**: Each request counts against your daily limit
2. **Batch operations**: Combine multiple operations into single requests when possible
3. **Batch tool calls**: Send multiple tool calls in a single message rather than sequential calls
4. **Avoid micro-operations**: Don't make many small requests for tiny pieces of information
5. **Use comprehensive tools**: Prefer tools that return more information in one call

### Best Practices for Request-Limited Environments:
- **Read entire files** when you need to understand context, rather than making multiple small reads
- **Write complete updates** instead of incremental changes
- **Use directory listing** to understand project structure in one call
- **Prefer single comprehensive commands** over multiple targeted ones
- **Batch tool calls when appropriate** - send multiple operations in one request
- **Avoid grep and sed**: Avoid using `grep` and `sed` via `run_shell_command` as they create multiple API requests and increase costs
- **Prefer read_file**: Use `read_file` to read entire files instead of partial reads with grep/sed
- **Prefer edit_file/write_file**: Use `edit_file` or `write_file` for all file modifications instead of shell commands like `sed`

## Best Practices & Guidelines

### Batching Operations
- **Batch operations when practical** to minimize the number of requests
- Use single commands to process multiple files instead of separate requests
- Example: `ruff check .` instead of checking each file individually
- Example: `ruff format .` instead of formatting each file individually
- **Chain commands together** using `&&` or `;` to execute multiple operations in a single request
- Example: `ruff check . && ruff format . && python -m py_compile .` - This single command performs linting, formatting, and compilation checks
- Example: `ls -la && pwd && echo "Current directory listed"` - This single command performs multiple operations
- **In request-limited environments**: Prefer reading entire files rather than multiple small reads
- **Avoid grep/sed fragmentation**: Avoid using `grep` or `sed` to read or modify parts of files as this creates multiple API requests; prefer reading entire files with `read_file` and processing content programmatically

### Code Quality Tools
- **Ruff**: Use `ruff check .` to validate entire project syntax and style (much faster than python compilation)
- **Ruff Format**: Use `ruff format .` to automatically format code according to style guidelines

### Project Structure
The project has been refactored into a modular structure:

```
aicoder/
├── app.py                 # Main application (7.5KB)
├── stats.py              # Statistics tracking (2KB)
├── message_history.py    # Message history management
├── animator.py           # Animation handling
├── utils.py             # Utility functions
├── config.py            # Configuration
├── __main__.py           # Package entry point
├── __init__.py           # Package initialization

├── api_handler.py        # API request handling (7KB)
├── tool_call_executor.py # Tool call execution (0.5KB)
├── input_handler.py      # Input handling (2.5KB)
├── command_handlers.py  # Command processing (7KB)
├── streaming_adapter.py  # Streaming SSE response handler (14KB)
└── tool_manager/         # Tool management system (modular directory)
    ├── __init__.py
    ├── registry.py          # Tool discovery & definitions (15KB)
    ├── executor.py          # Tool execution logic (21KB)
    ├── manager.py           # Main coordinator (1.5KB)
    ├── approval_system.py   # User approval logic (6.5KB)
    └── internal_tools/      # Individual tool implementations
        ├── __init__.py
        ├── write_file.py        # Write file implementation (2KB)
        ├── read_file.py         # Read file implementation (0.5KB)
        ├── list_directory.py    # List directory implementation (0.5KB)
        ├── run_shell_command.py # Shell command implementation (4KB)
        ├── pwd.py              # Print working directory implementation (0.5KB)
        ├── grep.py             # Search text in files implementation (2KB)
        ├── glob.py             # Find files matching patterns implementation (2.7KB)
        └── __init__.py         # Package initialization
```

### Key Refactoring Benefits
1. **Reduced file sizes**: Main files are now ~7KB instead of ~30KB
2. **Clearer responsibilities**: Each module has a single, well-defined purpose
3. **Easier maintenance**: Changes are isolated to specific files
4. **Better testability**: Components can be tested independently
5. **Improved readability**: Related functionality is grouped together

### Tool Manager Structure
The tool manager was refactored from a single 50KB file to a directory structure:
- **Registry**: Handles what tools exist and their definitions
- **Executor**: Handles how to run tools and execution logic
- **Manager**: Coordinates both registry and executor
- **Approval System**: Handles user permissions and approvals
- **Internal Tools**: Each tool implementation in its own file

### Streaming Adapter Feature
A new pluggable streaming adapter has been added to support SSE (Server-Sent Events) streaming responses:

- **File**: `streaming_adapter.py` (13KB)
- **Activation**: Set `ENABLE_STREAMING=1` environment variable
- **Backward Compatibility**: Fully maintains existing functionality when disabled
- **Features**:
  - Real-time display of AI responses as they're generated
  - Streaming tool call processing
  - ESC key cancellation support
  - Fallback to regular mode if streaming fails
  - No changes to existing API or user interface
  - **Enhanced Compatibility**: Now supports Google's OpenAI-compatible endpoint with proper handling of empty tool call IDs
  - **Improved Formatting**: Character buffering system prevents excessive whitespace and formatting issues during streaming

#### Character Buffering Approach
The streaming adapter now implements a character buffering system to improve output formatting:

- **Buffering Mechanism**: All characters (including whitespace) are buffered until actual visible content is received
- **Whitespace Management**: Excessive whitespace and empty lines are filtered out at the end of streaming
- **Consistent Output**: Prevents gaps and extra spacing between messages
- **Performance**: Reduces unnecessary terminal output operations

This approach ensures that the output looks clean and professional while maintaining real-time streaming capabilities.

### Token Usage Tracking
The application now automatically tracks token usage from API responses:

- **Files Modified**: `stats.py`, `api_handler.py`, `streaming_adapter.py`
- **Features**:
  - Automatic extraction of prompt_tokens (input) and completion_tokens (output) from API responses
  - Works with both streaming and non-streaming requests
  - Usage information displayed in session statistics
  - No additional API requests needed - uses existing response data
  - Robust error handling for cases where token information is missing

### Performance Tips
- Use `ruff check .` for fast project-wide syntax validation (much faster than python compilation and catches most issues)
- Use `ruff format .` for automatic code formatting
- Batch file operations when beneficial
- Prefer directory-level operations over file-by-file operations
- **Chain commands with &&**: Combine multiple operations in a single shell command execution
- Example: `ruff check . && ruff format . && python -c "import aicoder; print('Import successful')"`
- **Use comprehensive commands**: Instead of multiple read-modify-write cycles, use a single command that does all the work
- **Avoid sequential validation steps**: Don't run ruff check, read results, run ruff format, read results, etc. as separate requests
- **Bad pattern**: `ruff check .` → read output → `ruff format .` → read output → `python -c "import aicoder; print('Import successful')"` → read output (3+ requests)
- **Good pattern**: `ruff check . && ruff format . && python -c "import aicoder; print('Import successful')"` (1 request)
- **Avoid unnecessary operations**: Don't use multiple small requests when one comprehensive request will suffice
- **Minimize debugging overhead**: Debug output should not generate additional API requests
- **Use native file tools**: Prefer `read_file`, `edit_file`, and `write_file` instead of shell commands like `grep` and `sed` for file operations

### Command Batching Techniques

To minimize API requests in request-limited environments, always look for opportunities to batch operations:

1. **Shell Command Chaining**: Use `&&` to execute multiple commands in sequence only if the previous command succeeds
   - Example: `ruff check . && ruff format . && python -c "import aicoder; print('Import successful')"`

2. **Shell Command Grouping**: Use `;` to execute multiple commands regardless of success/failure
   - Example: `ls -la; pwd; echo "Done"`

3. **Combined Validation**: Run all code quality checks in a single command
   - Example: `ruff check . && ruff format --check . && python -c "import aicoder; print('All checks passed')"`

4. **Directory-wide Operations**: Prefer operations that work on entire directories
   - Example: Use `list_directory` to understand project structure rather than multiple shell commands

5. **Single File Read/Write Cycles**: When modifying files, do all changes in one operation rather than multiple read-modify-write cycles

6. **Consider batching opportunities**: Look for opportunities to combine related operations into single requests when it improves efficiency.

7. **Tool Call Batching**: Send multiple tool calls in a single message rather than sequential calls
   - Example: Combine multiple `read_file` calls when checking several files:
     ```json
     [
       {"name": "read_file", "arguments": {"path": "config.py"}},
       {"name": "read_file", "arguments": {"path": "utils.py"}},
       {"name": "read_file", "arguments": {"path": "handlers.py"}},
       {"name": "read_file", "arguments": {"path": "models.py"}},
       {"name": "read_file", "arguments": {"path": "main.py"}}
     ]
     ```
   - This reduces the total number of API requests from 5 to 1
   - **NEVER create invalid method names** by concatenating tool names

8. **Avoid grep/sed**: Avoid using `grep` or `sed` for file operations as they fragment work across multiple API requests (already covered in performance tips)

### Timeout Management for Shell Commands

The `run_shell_command` tool now includes a `timeout` parameter (default: 30 seconds, configurable via `SHELL_COMMAND_TIMEOUT` environment variable) to prevent commands from hanging indefinitely:

- Use `timeout=N` where N is the number of seconds before the command is terminated
- Minimum timeout value is 1 second (no "no timeout" option to prevent lazy workarounds)
- When a command times out, a helpful error message suggests how to retry with a longer timeout
- Example: `run_shell_command(command="sleep 10", timeout=5)` will timeout after 5 seconds with retry instructions
- The default timeout can be configured globally using the `SHELL_COMMAND_TIMEOUT` environment variable

This feature improves the development experience by providing faster feedback and preventing long hangs.

### File Modification Best Practices

When working with files, follow these guidelines to avoid errors and minimize API requests:

1. **Use proper file tools**: Prefer `edit_file` and `write_file` over shell commands like `sed` for file modifications
   - **Correct**: `edit_file` for modifying existing files with precise content replacement
   - **Correct**: `write_file` for creating new files or completely replacing existing ones
   - **Avoid**: `sed`, `awk`, or other shell commands for file modifications when `edit_file`/`write_file` can be used

2. **Handle file modification conflicts**: If you receive an error like "File has been modified since it was last read", you must:
   - First call `read_file` to get the current file content
   - Then use `edit_file` or `write_file` with the current content
   - This happens when external tools (like `sed`) modify files between your read and write operations
   - **Important**: The error message means the file changed after you last read it, so you need to read it again before making changes

3. **Batch file operations**: When making multiple changes to the same file, combine them into a single `edit_file` call rather than multiple separate calls

4. **Use shell commands only when necessary**: Shell commands should only be used for operations that cannot be accomplished with the available file tools, such as:
   - Directory operations (`mkdir`, `rmdir`, `rm`)
   - System-level operations
   - **Avoid pattern matching**: Use `read_file` to read entire files and process content programmatically rather than using `grep` (covered elsewhere)

5. **Read entire files**: Instead of using `grep` to find specific content, use `read_file` to read the entire file and then search within the content programmatically (already covered in best practices)

### Testing Commands
```bash
# Check entire project syntax and style (fast)
ruff check .

# Format entire project automatically
ruff format .

# Check specific directory
ruff check aicoder/

# Test imports
python -c "from aicoder.tool_manager import MCPToolManager; print('Import successful')"

# Test streaming adapter
python -c "from aicoder.streaming_adapter import StreamingAdapter; print('Streaming adapter import successful')"

# Test token tracking
python -c "from aicoder.stats import Stats; s=Stats(); s.prompt_tokens=100; s.completion_tokens=200; s.print_stats()"

# Run comprehensive test suite (recommended)
python check_all.py

# Run quick core functionality test
python quick_test.py

# Combined validation (single request for multiple checks)
ruff check . && ruff format --check . && python check_all.py

# Run with specific temperature and top_p settings
TEMPERATURE=0.7 TOP_P=0.9 python -m aicoder
```

### Test Runner Script

A unified test runner is available to verify application functionality:

**`test_runner.py`** - Unified test suite with quick and comprehensive modes
   - Use `python test_runner.py --quick` for quick core functionality tests
   - Use `python test_runner.py --full` for comprehensive tests including syntax checking
   - Runs with YOLO_MODE=1 to prevent approval prompts that cause timeouts
   - Both modes verify core imports, internal tools, file operations, app instantiation, and tool manager

The test runner is designed to verify that the application is working correctly after changes or reverts. It automatically sets YOLO_MODE=1 to prevent interactive approval prompts that could cause tests to hang.



> **IMPORTANT**: Do not use pytest inside the current firejail environment as it's not properly configured. Testing should be done manually or through alternative methods.

### File Modification Error Handling

When you encounter an error message like:
```
Error: File /path/to/file.py has been modified since it was last read (mod time: 2025-09-03 04:46:24, last read: 2025-09-03 04:45:54)
```

**This means:** The file was modified by an external process after you last read it, and you need to read the current content before making changes.

**Solution:**
1. Call `read_file` to get the current file content
2. Then use `edit_file` or `write_file` with the updated content

**Prevention:**
- Prefer `edit_file` and `write_file` over shell commands like `sed` for file modifications
- If you must use shell commands, be aware that they can cause this conflict

### Environment Variables
```bash
# Enable streaming mode
ENABLE_STREAMING=1

# Enable debug mode
DEBUG=1

# API configuration
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-5-nano

# Model parameters
TEMPERATURE=0.7  # Control the randomness of responses (default: 0.0)
TOP_P=0.9        # Control diversity via nucleus sampling (only sent when set to non-default value)

# MCP tools configuration
MCP_TOOLS_CONF_PATH=/path/to/mcp_tools.json  # Override default MCP tools configuration file path

# Shell command timeout (default: 30 seconds)
SHELL_COMMAND_TIMEOUT=60
```

### Plugin Development

When developing plugins for AI Coder, follow these guidelines:

#### Plugin Location
Plugins should be created in the `docs/plugins/examples/<stable or unstable dir>` directory, with each plugin in its own subdirectory. This ensures proper organization and follows the project's structure. Stable plugins are tested plugins that works 100% so the user should be the one to create stable plugins. You can edit stable plugins if needed but usualy you will create plugins in the unstable dir like `docs/plugins/examples/unstable/<plugin_dir_name>`

#### Plugin Structure
Each plugin should include:
- A main Python file with the plugin implementation
- A `README.md` explaining the plugin's purpose and usage
- An `__init__.py` file with a brief description

#### Documentation Style
- **Focus on quality over quantity**: Write one excellent README.md file that covers all essential information
- **Ask before creating additional documentation files** - users prefer to request more information if needed
- **Test functionality first** before writing any documentation
- **Avoid creating multiple documentation files** without explicit permission
- **Respect user experience** - too many files can be overwhelming and clutter the project

> **WARNING**: you should ignore session.json files (or any files with a similar name like <something>session<something>.json) because they are probably contexts from older chats avoid reading (unless specifically asked to do so) them and if any tool like grep finds any information inside this kind of tile you should ignore. Reading them will cause confusion on your understanding.

> **WARNING**: JSON framework must be constructed with double-quotes. Double quotes within strings must be escaped with backslash, single quotes within strings will not be escaped.

