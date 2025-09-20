# AI Coder

AI Coder is an AI-assisted coding tool with MCP (Model Context Protocol) support. It allows you to interact with AI models through a command-line interface and provides access to various tools for file system operations and command execution.

## Features

- Interactive chat with AI models
- MCP tool support for file operations and command execution
- User approval system for sensitive operations
- Session management (save/load)
- Memory compaction for long conversations
- Colorized output for better readability
- Streaming SSE support with optional logging (enabled by default, now with enhanced compatibility for Google's OpenAI-compatible endpoint)
- Low CPU and memory usage - significantly less than other AI coders
- Works exceptionally well with TMUX terminal multiplexer
- Zero external dependencies - no risk of dependency chain attacks
- Developed and optimized on Raspberry Pi 3B - uses less than 5% CPU most of the time

## Installation

### Automated Installation (Recommended)

```bash
git clone <repository-url>
cd aicoder
./install.sh
```

This will:
- Build and install the zipapp version
- Install launcher scripts to `~/.local/bin` (or custom location)
- Check for dependencies (firejail)
- Suggest stable plugins for installation

### As a UV Tool (Alternative)

If you have `uv` installed, you can also install AI Coder as a tool:

```bash
# Install from github repo
uv tool install git+https://github.com/elblah/dt-aicoder

# Or install from local directory
uv tool install . --editable

# Or after installation, run with:
uvx aicoder

```

Once installed as a uv tool, you can run AI Coder from anywhere with:
```bash
export OPENAI_API_KEY="your-api-key-here"
uvx aicoder
```

Note: The uv tool installation does not include the launcher scripts with sandboxing.
For the full experience with sandboxing, use the automated installation script above.

### From Source (Traditional)

```bash
git clone <repository-url>
cd aicoder
pip install -e .
```

### As a Zipapp

```bash
python build_zippapp.py
python aicoder.pyz
```

## Usage

Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

Run the tool:
```bash
python aicoder.py
```

Or if installed:
```bash
aicoder
```

## Running Tests

### ⚠️ CRITICAL: ALWAYS Run Tests with YOLO_MODE=1

**WARNING: Tests will HANG without YOLO_MODE=1 - This is the #1 cause of test failures**

Many tests trigger approval prompts that cause tests to hang indefinitely. **You must use YOLO_MODE=1 for individual test files.**

### ALWAYS use YOLO_MODE=1 for individual test files:
```bash
# Run all tests safely
YOLO_MODE=1 python -m unittest discover

# Run specific test file safely
YOLO_MODE=1 python tests/test_config.py
YOLO_MODE=1 python tests/test_aicoder.py
YOLO_MODE=1 python tests/test_tool_manager.py

# Run with verbose output safely
YOLO_MODE=1 python -m unittest discover -v
```

### Safe Test Runners (YOLO_MODE=1 handled automatically):
```bash
# These are SAFE - no need for YOLO_MODE=1
python test_runner.py --quick
python test_runner.py --full
python test_runner.py  # defaults to quick
```

**RULE: If running individual test files, ALWAYS use YOLO_MODE=1**

---

### Comprehensive Testing (Recommended)

For development and verification, use the comprehensive test script that runs all test suites:

```bash
# Run comprehensive test suite (SAFE - includes syntax checking, unit tests, and integration tests)
./run-tests.sh
```

The `run-tests.sh` script:
1. Runs Python's built-in unittest framework with full verbose output
2. Runs the comprehensive test runner (`test_runner.py --full`)
3. Checks both unit tests and integration tests
4. Automatically sets `YOLO_MODE=1` to prevent approval prompts
5. Provides clear pass/fail status for all test suites

**This is the recommended way to verify the entire application is working correctly.**

### Quick Test Script (Alternative)

A unified test runner is available that automatically handles YOLO_MODE=1:

```bash
# Run quick core functionality test (SAFE)
python test_runner.py --quick

# Run full comprehensive test suite (SAFE)
python test_runner.py --full

# Run quick test (default, SAFE)
python test_runner.py
```

### Traditional Unit Tests (⚠️ Requires YOLO_MODE=1)

AI Coder also uses Python's built-in unittest framework, but you **MUST use YOLO_MODE=1**:

```bash
# Run all tests (MUST use YOLO_MODE=1)
YOLO_MODE=1 python -m unittest discover

# Run tests with verbose output (MUST use YOLO_MODE=1)
YOLO_MODE=1 python -m unittest discover -v

# Run a specific test file (MUST use YOLO_MODE=1)
YOLO_MODE=1 python -m unittest tests.test_config

# Run a specific test class (MUST use YOLO_MODE=1)
YOLO_MODE=1 python -m unittest tests.test_config.TestConfig

# Run a specific test method (MUST use YOLO_MODE=1)
YOLO_MODE=1 python -m unittest tests.test_config.TestConfig.test_default_config_values
```

For more detailed information about running tests, see [tests/README.md](tests/README.md).

**REMINDER: The test_runner.py scripts automatically set YOLO_MODE=1 to prevent interactive approval prompts that could cause tests to hang. Individual test files do NOT handle this automatically.**

## Commands

- `/help` - Show available commands
- `/edit` or `/e` - Open editor to write a prompt
- `/memory` or `/m` - Edit conversation memory
- `/quit` or `/q` - Exit the application
- `/model` - Show or change the AI model
- `/new` - Start a new session
- `/save` [filename] - Save session to file
- `/load` [filename] - Load session from file
- `/stats` - Show session statistics
- `/retry` or `/r` - Retry the last API call
- `/yolo` [on/off] - Show or toggle YOLO mode (bypass all approvals)
- `/revoke_approvals` or `/ra` - Clear session approvals cache

## Configuration

AI Coder can be configured through environment variables:

- `OPENAI_API_KEY` - Your OpenAI API key
- `OPENAI_BASE_URL` - Base URL for the API (default: https://api.openai.com/v1)
- `OPENAI_MODEL` - Model to use (default: gpt-5-nano)
- `DEBUG` - Enable debug mode (set to 1 to enable)
- `YOLO_MODE` - Enable YOLO mode to bypass approvals (set to 1 to enable)
- `DISABLE_STREAMING` - Disable streaming SSE responses (set to 1 to disable, streaming is enabled by default)
- `STREAM_LOG_FILE` - Log all streaming SSE data to this file (when streaming is enabled)
- `TEMPERATURE` - Control the randomness of the AI's responses (default: 0.0)
- `TOP_P` - Control diversity via nucleus sampling (only sent to API when set to non-default value)
- `MCP_TOOLS_CONF_PATH` - Override default MCP tools configuration file path

## Themes

AI Coder supports dynamic color themes that can be applied at runtime:

- `default` - Standard color scheme
- `luna` - Purple-themed color scheme
- `sunset` - Orange/red-themed color scheme
- `ocean` - Blue-themed color scheme
- `forest` - Green-themed color scheme

Themes are applied dynamically and affect all colorized output including prompts, messages, and session save/load operations.

## Tool Parameters

The `run_shell_command` tool includes a `timeout` parameter (default: 30 seconds) to prevent commands from hanging indefinitely. When a command times out, a helpful error message suggests how to retry with a longer timeout.

## Built-in Tools

AI Coder includes several built-in tools to help the AI interact with the file system and execute commands:

- `write_file` - Write content to a file
- `read_file` - Read content from a file
- `edit_file` - Edit a file by replacing specific content
- `list_directory` - List contents of a directory
- `run_shell_command` - Execute shell commands
- `grep` - Search for text in files
- `glob` - Find files matching a pattern (supports ** for recursive matching)
- `pwd` - Get the current working directory
- `update_plan` - Track and display task progress to the user

### update_plan Tool

The `update_plan` tool allows the AI to display a task plan with progress tracking to the user. It shows a visual representation of what steps are pending, in progress, or completed.

Usage:
```json
{
  "name": "update_plan",
  "arguments": {
    "plan": [
      {"step": "Analyze requirements", "status": "completed"},
      {"step": "Implement feature", "status": "in_progress"},
      {"step": "Write tests", "status": "pending"}
    ],
    "explanation": "Working on implementing the new feature"
  }
}
```

Status values:
- `completed` - Step is finished (marked with ✅)
- `in_progress` - Step is currently being worked on (marked with ▶️)
- `pending` - Step is not yet started (marked with ❌)
