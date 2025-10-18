# Todo Plugin

This plugin provides todo list functionality for AI Coder with:
- `/todo` command for users to view and manage todos
- `update_plan` tool for the AI to track progress
- Memory storage for todo persistence during sessions

## Installation

1. Create the plugins directory if it doesn't exist:
   ```bash
   mkdir -p ~/.config/aicoder/plugins
   ```

2. Copy the plugin file:
   ```bash
   cp todo.py ~/.config/aicoder/plugins/
   ```

3. Run AI Coder - todo functionality will be available

## Usage

Once installed:
- Type `/todo` to view the current todo list
- Type `/todo update` to force a new todo list from the AI
- The AI will automatically use the update_plan tool when appropriate

To disable, remove the plugin file:
```bash
rm ~/.config/aicoder/plugins/todo.py
```