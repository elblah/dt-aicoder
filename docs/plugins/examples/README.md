# AI Coder Plugin Examples

This directory contains example plugins that demonstrate various ways to extend AI Coder functionality. Plugins are organized into two categories:

- **stable**: Plugins that have been tested and are working properly
- **unstable**: Plugins that are provided as examples but may not have been fully tested

## Stable Plugins

### theme.py
Customizes AI Coder's color scheme with support for popular terminal themes.

### 15_notify_prompt_sound.py
Plays a sound notification when the AI needs your attention.

### 17_tiered_cost_display_plugin.py
Displays cost information with support for tiered pricing models.

## Unstable Plugins

The following plugins are in the unstable folder and are provided as examples:

### 01_logging_plugin.py
Logs all tool executions with timestamps and details.

### 02_auto_approve_plugin.py
Automatically approves safe operations like reading files or listing directories.

### 03_custom_command_plugin.py
Adds a new `/plugins` command to list all loaded plugins.

### 04_export_history_plugin.py
Adds a `/export` command to save conversation history to a JSON file.

### 05_cost_tracking_plugin.py
Tracks API usage costs based on token consumption and shows real-time costs during API calls. Adds a `/cost` command to display cost information.

### 06_session_backup_plugin.py
Automatically backs up the session every N messages or at regular intervals. Adds a `/backup` command to manually trigger a backup.

### 07_web_search_plugin.py
Adds web search capability using DuckDuckGo. The AI can call the `web_search` tool to find information online.

### 08_file_watcher_plugin.py
Watches for file changes in the current directory and notifies the AI about important changes. Useful for development workflows.

### 09_context_summary_plugin.py
Automatically generates context summaries when the conversation becomes very long to help maintain focus and reduce token usage.

### 10_attention_notification_plugin.py
Sends desktop notifications, plays sounds, and highlights terminal output when the AI needs your attention (approval prompts, user input needed, etc.). Adds a `/notify_test` command to test notifications.

### 11_code_quality_guardian.py
Automatically monitors code quality by running linters and formatters on files modified during AI-assisted development. Provides real-time feedback and can automatically fix formatting issues. Adds `/quality` and `/format` commands, plus a `quality_check` tool for the AI.

### 12_jujutsu_version_control.py
Integrates AI Coder with Jujutsu (jj), a Git-compatible VCS. Automatically initializes repositories, commits changes with AI-generated messages, and maintains complete history of AI interactions. Adds `/jj` command for version control operations including easy rollback capabilities.

### 13_lsp_integration.py
Integrates Language Server Protocol (LSP) servers for real-time code analysis, error detection, and suggestions. Automatically detects project types and launches appropriate language servers (Python: ruff/pyright, JavaScript/TypeScript, JSON). Provides real-time diagnostics and notifies the AI of code issues. Adds `/lsp` command for server management.

### 14_theme_customization.py
Customizes AI Coder's color scheme with support for popular terminal themes (Catppuccin, Gruvbox, Monokai, Dracula, etc.) and custom color definitions. Supports both 256-color and true color modes. Adds `/theme` command for theme management. Set AICODER_THEME environment variable for persistent themes.

### 16_cost_display_plugin.py
Displays cost information above prompts in a user-friendly format.

### 18_tiered_cost_tracking_plugin.py
Enhanced version of the cost tracking plugin with support for tiered pricing.

## Installation

To use any of these examples:

1. Create the plugins directory:
   ```bash
   mkdir -p ~/.config/aicoder/plugins
   ```

2. Copy the desired plugin from either the stable or unstable directory:
   ```bash
   cp docs/examples/stable/theme.py ~/.config/aicoder/plugins/
   ```

3. Run AI Coder - the plugin will be loaded automatically!

## Creating Your Own Plugins

Feel free to use these examples as templates for your own plugins. The plugin system is designed to be simple and powerful - you can modify any part of AI Coder's behavior by directly manipulating classes and methods.