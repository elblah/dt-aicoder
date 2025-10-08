# AI Coder Documentation

This directory contains comprehensive documentation for AI Coder development and usage.

## Core Documentation

### [Project Structure](project_structure.md)
Complete directory overview with file sizes and architectural patterns. Essential for understanding the codebase organization.

### [Development Workflow](development_workflow.md)
Development practices, coding standards, testing requirements, and contribution guidelines.

## MCP (Model Context Protocol) Documentation

### [MCP Configuration Guide](mcp/configuration_guide.md)
Setting up and configuring MCP servers for external tool integration.

### [MCP Examples and Best Practices](mcp/examples_and_best_practices.md)
Real-world examples and recommended patterns for MCP usage.

### [MCP Summary](mcp/SUMMARY.md)
Quick overview of MCP capabilities and setup.

## Plugin System Documentation

### [Plugin Development Guide](plugins/README.md)
Creating and developing plugins for AI Coder extension.

### [Plugin Examples](plugins/examples/)
Example implementations demonstrating various plugin capabilities:
- **Stable plugins**: Production-ready examples
- **Unstable plugins**: Experimental features

### [Cost Plugin Examples](plugins/examples/README_COST_PLUGINS.md)
Examples for cost tracking and management plugins.

## Additional Resources

### [Extras](extras/)
Configuration examples and templates:
- API provider configurations (OpenAI, Gemini, Cerebras, etc.)
- MCP tools configuration examples
- Startup scripts

## Quick Links for Developers

- **Testing Requirements**: See [Development Workflow](development_workflow.md#testing-requirements)
- **Code Quality**: See [Development Workflow](development_workflow.md#code-quality)
- **Error Handling**: See [Development Workflow](development_workflow.md#error-handling-guidelines)
- **Architecture**: See [Project Structure](project_structure.md#key-architectural-patterns)

## Documentation Structure

```
docs/
├── project_structure.md      # Complete project overview
├── development_workflow.md   # Development practices
├── mcp/                     # MCP protocol documentation
├── plugins/                 # Plugin system documentation
└── extras/                  # Configuration examples
```

For questions or contributions, refer to the development workflow guidelines.