# Agent Development Notes

## **CRITICAL**: Always Run Tests with YOLO_MODE=1 and AICODER_THEME=original

**WARNING: Tests that trigger tool approvals will hang indefinitely without YOLO_MODE=1**

Many tests in this project will trigger approval prompts (`input()` calls) that cause the test to hang waiting for user input. **This is the #1 reason LLMs fail when running tests.**

### ALWAYS run tests with YOLO_MODE=1:
```bash
# For individual test files
AICODER_THEME=original YOLO_MODE=1 python tests/test_aicoder.py

# For unittest discover
AICODER_THEME=original YOLO_MODE=1 python -m unittest discover

# For any test that might involve tool execution
AICODER_THEME=original YOLO_MODE=1 python your_test_script.py
```

**MEMORIZE THIS: If a test might run tools, it needs YOLO_MODE=1**

---

## Project Structure

```
aicoder/
├── AICODER.md
├── __init__.py           # (4.0K)
├── __main__.py           # (4.0K)
├── animator.py           # (8.0K)
├── api_client.py         # (8.0K)
├── api_handler.py        # (12K)
├── app.py                # (24K)
├── command_handlers.py   # (12K)
├── config.py             # (8.0K)
├── file_tracker.py       # (4.0K)
├── input_handler.py      # (4.0K)
├── message_history.py    # (24K)
├── retry_utils.py        # (12K)
├── stats.py              # (8.0K)
├── streaming_adapter.py  # (68K)
├── tool_call_executor.py # (4.0K)
├── utils.py              # (20K)
└── plugin_system/        # Plugin system
    ├── __init__.py       # (4.0K)
    └── loader.py         # (4.0K)
└── tool_manager/         # Tool management system (modular directory)
    ├── __init__.py       # (4.0K)
    ├── approval_system.py # (12K)
    ├── executor.py       # (44K)
    ├── manager.py        # (4.0K)
    ├── registry.py       # (16K)
    ├── validator.py      # (12K)
    └── internal_tools/   # Individual tool implementations
        ├── __init__.py   # (4.0K)
        ├── edit_file.py  # (12K)
        ├── glob.py       # (4.0K)
        ├── grep.py       # (4.0K)
        ├── list_directory.py # (4.0K)
        ├── pwd.py        # (4.0K)
        ├── read_file.py  # (4.0K)
        ├── run_shell_command.py # (4.0K)
        └── write_file.py # (4.0K)
```

### Tool Manager Structure
- **Registry**: Handles what tools exist and their definitions
- **Executor**: Handles how to run tools and execution logic
- **Manager**: Coordinates both registry and executor
- **Approval System**: Handles user permissions and approvals
- **Internal Tools**: Each tool implementation in its own file

---

## ⚠️ CRITICAL: Network Access Blocked in Tests

**ALL NETWORK ACCESS IS BLOCKED IN TESTS** to protect API quota and ensure reliable, fast execution.

- External URLs are blocked, local connections allowed
- Use mocks/stubs for API responses, not real network calls
- Tests will fail with clear error messages if network access is attempted

---

## CRITICAL: Use run-tests.sh as the Definitive Test Method

**`run-tests.sh`** is the definitive and comprehensive method for running ALL tests in the project:

- **Complete test coverage**: Runs both the comprehensive test suite (`test_runner.py --full`) AND all individual unit tests (`python -m unittest discover`)
- **Single command execution**: Executes all tests in one go, taking less than 30 seconds
- **All-inclusive**: Includes syntax checks, imports, functionality tests, and unit tests
- **Consistent environment**: Automatically sets YOLO_MODE=1 and other necessary environment variables

**ALWAYS use `run-tests.sh` as the definitive method** to ensure complete test coverage before committing changes or verifying functionality.

```bash
# This is the definitive test method - runs everything
bash run-tests.sh
```

---

## CRITICAL: Unit Test Creation Protocol

**MANDATORY PROTOCOL: When implementing features, ALWAYS create proper unit tests in the `tests/` directory.**

**When you create any functionality that might be useful to test in the future:**
- ✅ **ALWAYS** create a `unittest` test file in the `tests/` directory
- ✅ Use standard Python `unittest` framework (NOT pytest)
- ✅ Name test files as `test_<feature_name>.py`
- ✅ Place them in the `tests/` directory
- ✅ Test both positive and negative cases
- ✅ Include edge cases and error conditions

**This is not optional - it's mandatory for every feature implementation.**

---

## Project-Specific Features

### Batching Operations
- **Batch operations when practical** to minimize the number of requests
- Example: `ruff check . && ruff format . && python -m py_compile .` - This single command performs linting, formatting, and compilation checks

### Code Quality Tools
- **Ruff**: Use `ruff check .` to validate entire project syntax and style (much faster than python compilation)
- **Ruff Format**: Use `ruff format .` to automatically format code according to style guidelines

### Streaming Adapter Feature
Support SSE (Server-Sent Events) streaming responses:

- **File**: `streaming_adapter.py`
- **Features**:
  - Real-time display of AI responses as they're generated
  - Streaming tool call processing
  - ESC key cancellation support
  - Fallback to regular mode if streaming fails
  - **Improved Formatting**: Character buffering system prevents excessive whitespace during streaming

### Token Usage Tracking
The application automatically tracks token usage from API responses:

- **Files Modified**: `stats.py`, `api_handler.py`, `streaming_adapter.py`
- **Features**:
  - Automatic extraction of prompt_tokens (input) and completion_tokens (output) from API responses
  - Works with both streaming and non-streaming requests
  - Usage information displayed in session statistics

### Tool Call Batching
When possible, send multiple tool calls in a single message rather than sequential calls:

```json
[
  {"name": "read_file", "arguments": {"path": "config.py"}},
  {"name": "read_file", "arguments": {"path": "utils.py"}},
  {"name": "read_file", "arguments": {"path": "main.py"}}
]
```
- This reduces the total number of API requests from 3 to 1
- **NEVER create invalid method names** by concatenating tool names

---

## Environment Variables

```bash
# Enable debug mode
DEBUG=1

# API configuration
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-5-nano

# MCP tools configuration
MCP_TOOLS_CONF_PATH=/path/to/mcp_tools.json

# Shell command timeout (default: 30 seconds)
SHELL_COMMAND_TIMEOUT=60
```

---

## File Modification Error Handling

When you encounter an error message like:
```
Error: File /path/to/file.py has been modified since it was last read
```

**Solution:**
1. Call `read_file` to get the current file content
2. Then use `edit_file` or `write_file` with the updated content

**Prevention:**
- Prefer `edit_file` and `write_file` over shell commands like `sed`
- Shell commands can cause modification conflicts

---

## Plugin Development

### Plugin Location
Plugins should be created in `docs/plugins/examples/<stable or unstable dir>` directory, with each plugin in its own subdirectory.

### Plugin Structure
Each plugin should include:
- A main Python file with the plugin implementation
- A `README.md` explaining the plugin's purpose and usage
- An `__init__.py` file with a brief description

### Documentation Style
- **Focus on quality over quantity**: Write one excellent README.md file
- **Test functionality first** before writing documentation
- **Avoid creating multiple documentation files** without explicit permission

> **WARNING**: you should ignore session.json files (or any files with a similar name like <something>session<something>.json) because they are probably contexts from older chats avoid reading them and if any tool like grep finds any information inside this kind of tile you should ignore. Reading them will cause confusion on your understanding.

> **WARNING**: JSON framework must be constructed with double-quotes. Double quotes within strings must be escaped with backslash, single quotes within strings will not be escaped.