# Integrated Plan Plugin

This plugin provides task planning functionality for AI Coder with:
- `/plan` command for users to view and manage plans
- `update_plan` tool for the AI to track progress
- Memory storage for plan persistence during sessions

## Installation

1. Create the plugins directory if it doesn't exist:
   ```bash
   mkdir -p ~/.config/aicoder/plugins
   ```

2. Copy the plugin file:
   ```bash
   cp plan.py ~/.config/aicoder/plugins/
   ```

3. Run AI Coder - plan functionality will be available

## Usage

Once installed:
- Type `/plan` to view the current plan
- Type `/plan update` to force a new plan from the AI
- The AI will automatically use the update_plan tool when appropriate

To disable, remove the plugin file:
```bash
rm ~/.config/aicoder/plugins/plan.py
```