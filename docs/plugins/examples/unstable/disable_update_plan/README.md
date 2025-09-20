# Disable update_plan Plugin

This plugin completely removes the `update_plan` tool from the tool registry, preventing the AI from seeing or using it. This saves API requests and costs for users who prefer to let the AI work without progress tracking.

## Benefits

- **Saves API requests**: Prevents the AI from calling update_plan, saving valuable request quota
- **Reduces costs**: No wasted money on progress tracking calls
- **Complete invisibility**: The tool is entirely hidden from the AI
- **Easy toggle**: Simply copy/remove the plugin file to enable/disable

## Installation

1. Create the plugins directory if it doesn't exist:
   ```bash
   mkdir -p ~/.config/aicoder/plugins
   ```

2. Copy the plugin file:
   ```bash
   cp disable_update_plan.py ~/.config/aicoder/plugins/
   ```

3. Run AI Coder - the update_plan tool will be completely hidden

## Usage

Once installed, the AI will never see or attempt to use the update_plan tool. All progress tracking functionality is removed, resulting in:

- Zero API requests for progress updates
- Maximum efficiency for cost-conscious users
- Clean, focused AI interactions

To re-enable progress tracking, simply remove the plugin file:
```bash
rm ~/.config/aicoder/plugins/disable_update_plan.py
```

## Why This Matters

For users with request-limited API accounts, every API call costs money. The update_plan tool, while useful for tracking progress, consumes valuable request quota without contributing to the core task completion. This plugin allows cost-conscious users to maximize their API efficiency.