# AI Coder Project-Specific Guidelines

## IMPORTANT

- **Prefer guard clauses/early exits** over nested if/else statements
- **Keep functions focused** - One main responsibility per function
- **Use Pythonic error handling** - `try/except` is idiomatic in Python (EAFP style)
- **Be specific with exceptions** - Catch only what you can handle
- **Use descriptive names** - Short is good, but clarity is better
- **Avoid deep nesting** - Flatten code through early returns and helper functions
- **CRITICAL: AVOID LAZY/LOCAL IMPORTS** python imports should be done at the top of the file

## Code Structure Guidelines

- **Keep methods short** - Methods should be under 50 lines, ideally under 30
- **Avoid repetitive code** - Extract common patterns into helper methods
- **Don't Repeat Yourself (DRY)** - If you copy-paste code, you need a helper method
- **Single responsibility** - Each method should do one thing well
- **Linear flow** - Prefer sequential guard clauses over nested logic
- **Early returns** - Exit as soon as possible rather than nesting deeper

## Python-Specific Best Practices

- **Use `try/except` for flow control** - Python's "EAFP" (Easier to Ask for Forgiveness than Permission) style is preferred
- **Specific exception handling** - Catch specific exceptions, not bare `except:`
- **Context managers** - Use `with` statements for resource management
- **Descriptive variable names** - `user_input` is better than `x`, `is_valid` is better than `flag`
- **Follow PEP 8** - Python's style guide for readable code
- **Type hints** - Use them for better code documentation and IDE support

## **CRITICAL**: Testing Requirements

**Always run tests with YOLO_MODE=1** - Tests with tool approvals will hang without it:

```bash
# Comprehensive testing method
bash run-tests.sh
```

## Project-Specific Context

This is the AI Coder project - a CLI tool that provides AI assistance with file operations and tool execution. You have access to the full codebase and should understand the project architecture when making changes.

### Project Knowledge
- **Architecture**: Modular design with tool_manager/, plugin_system/, and core components
- **Key Files**: app.py (main application), message_history.py (conversation management), streaming_adapter.py (response handling)
- **Testing**: **IMPORTANT:** CREATE TESTS FOR EVERY FEATURE
- **Code Quality**: Enforced with `ruff check . && ruff format .`

## Development References

- **Project Structure**: [docs/project_structure.md](docs/project_structure.md) - Complete directory overview
- **Development Workflow**: [docs/development_workflow.md](docs/development_workflow.md) - Coding standards
- **MCP Configuration**: [docs/mcp/configuration_guide.md](docs/mcp/configuration_guide.md) - Server setup
- **Plugin Development**: [docs/plugins/README.md](docs/plugins/README.md) - Extension patterns

## Project-Specific Behaviors

### Testing Protocol
- **Unit Tests**: Create tests in `tests/test_<feature_name>.py` using unittest
- **Network Access**: Blocked in tests - use mocks/stubs for external calls
- **Test Execution**: Always use `YOLO_MODE=1` for tests with tool interactions

### Code Patterns
- **File Operations**: Prefer `edit_file`/`write_file` over shell commands
- **Tool Batching**: Group multiple tool calls to reduce API requests
- **Error Handling**: Check for "File has been modified since it was last read" errors

### Important Warnings
- **Session Files**: Ignore session.json files - contain old contexts that cause confusion
- **JSON Framework**: Must use double quotes, escape double quotes within strings with backslash

## Working with This Codebase

When modifying AI Coder:
1. Understand the modular architecture
2. Follow existing patterns in similar files
3. Create comprehensive tests
4. Use the established tool system patterns
5. Consider plugin compatibility

The codebase emphasizes practical solutions, efficient operations, and maintainable patterns.

---

## Important Warnings

> **WARNING**: Ignore session.json files (or similar names like <something>session<something>.json) - they contain old chat contexts that will cause confusion. Do not read them.

> **WARNING**: JSON framework must be constructed with double-quotes. Double quotes within strings must be escaped with backslash, single quotes within strings will not be escaped.
