# AI Coder Development Workflow

This document outlines the development practices and workflows for contributing to AI Coder.

## Code Quality

### Linting and Formatting
```bash
# Run both linting and formatting
ruff check . && ruff format .
```

- Use `ruff` for both code linting and formatting
- Run this command before committing changes
- Ensures consistent code style across the project

### Batch Operations
- Batch related operations when practical to minimize API requests
- Group multiple tool calls in a single message when possible
- Consider performance implications of tool usage patterns

## Unit Testing Protocol

### Requirements
**MANDATORY**: Create unit tests in `tests/` directory for all new features:
- Name files as `test_<feature_name>.py`
- Test both positive and negative cases
- Include edge cases and error conditions

### Testing Requirements
**Always run tests with YOLO_MODE=1** - Tests with tool approvals will hang without it:

```bash
# For individual test files
AICODER_THEME=original YOLO_MODE=1 python tests/test_aicoder.py

# For unittest discover  
AICODER_THEME=original YOLO_MODE=1 python -m unittest discover

# Definitive test method - runs everything
bash run-tests.sh
```

**run-tests.sh** is the comprehensive method that runs all tests with proper environment setup.

## Network Access in Tests

**ALL NETWORK ACCESS IS BLOCKED IN TESTS**:
- External URLs are blocked, local connections allowed
- Use mocks/stubs for API responses
- Tests will fail with clear error messages if network access is attempted

## Tool Call Batching

When possible, send multiple tool calls in a single message to reduce API requests:

```json
[
  {"name": "read_file", "arguments": {"path": "config.py"}},
  {"name": "read_file", "arguments": {"path": "utils.py"}}
]
```

**IMPORTANT**: NEVER create invalid method names by concatenating tool names.

## Error Handling Guidelines

### File Modification Errors
When encountering "File has been modified since it was last read":
1. Call `read_file` to get current content
2. Then use `edit_file` or `write_file` with updated content

**Prevention**: Prefer `edit_file`/`write_file` over shell commands like `sed`

### General Error Handling
- Handle exceptions gracefully and provide meaningful error messages
- Use appropriate logging for debugging
- Consider edge cases and invalid inputs
- Test error paths in unit tests

## Development Best Practices

### Code Organization
- Follow the established module structure
- Keep functions focused and single-purpose
- Use clear, descriptive names for functions and variables
- Document complex logic with comments

### Performance Considerations
- Be mindful of token usage in API calls
- Optimize file operations and tool usage
- Consider caching where appropriate
- Test with realistic data sizes

### Plugin Development
- Follow the plugin system patterns in `plugin_system/`
- Use the existing tool interfaces in `tool_manager/`
- Test plugins thoroughly with various scenarios
- Document plugin capabilities and usage

## Release Process

1. **Testing**: Ensure all tests pass with `bash run-tests.sh`
2. **Code Quality**: Run `ruff check . && ruff format .`
3. **Documentation**: Update relevant documentation
4. **Review**: Peer review of significant changes
5. **Testing**: Final testing in realistic scenarios

## Related Documentation

- [Project Structure](project_structure.md) - Complete directory and file overview
- [MCP Configuration](mcp/configuration_guide.md) - MCP server setup
- [Plugin Development](plugins/README.md) - Plugin system usage
- [Examples and Best Practices](mcp/examples_and_best_practices.md) - Usage patterns
