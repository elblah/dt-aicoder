# Tiered Cost Display Plugin

This plugin extends the cost display functionality to handle models with tiered pricing based on context length. It displays cost information for both the last request and accumulated total costs.

## Features

- Displays cost information above prompts when tokens are present
- Automatically detects model and applies appropriate pricing
- Supports tiered pricing for Qwen models based on context length
- Configurable enable/disable option
- Configurable file path for saving cost data
- Automatic saving of usage data on exit

## Usage

To use this plugin, simply load it with the AI Coder application.

## Configuration

The plugin can be configured using environment variables:

### Basic Configuration
- `TIERED_COST_PLUGIN_ENABLED` - Enable or disable the plugin (default: true)
- `TIERED_COST_DATA_FILE` - Path to save cost data (default: ./tiered_cost_data.txt)

### Fixed Pricing Overrides
- `INPUT_TOKEN_COST` - Fixed cost per 1 million input tokens (overrides all model configurations)
- `OUTPUT_TOKEN_COST` - Fixed cost per 1 million output tokens (overrides all model configurations)

When both `INPUT_TOKEN_COST` and `OUTPUT_TOKEN_COST` are set, they take precedence over all model-specific pricing configurations and disable multitier support. This provides a simple way to set fixed pricing for any model without dealing with complex tier configurations.

Examples:
```bash
# Basic configuration
TIERED_COST_PLUGIN_ENABLED=true TIERED_COST_DATA_FILE=./my_costs.txt python -m aicoder

# Fixed pricing overrides (no multitier support)
INPUT_TOKEN_COST=0.50 OUTPUT_TOKEN_COST=2.00 python -m aicoder

# Combined configuration
TIERED_COST_PLUGIN_ENABLED=true INPUT_TOKEN_COST=1.00 OUTPUT_TOKEN_COST=5.00 python -m aicoder
```

## Output Format

The plugin displays cost information in the following format:
```
💰 [model-name] Last Request: 0.01 input / 0.00 output = 0.01 total (12K prompt tokens, Tier 1)
💰 [model-name] Total Costs: 0.05 input / 0.03 output = 0.08 total
```

## Automatic Cost Data Saving

When the application exits, the plugin automatically saves the total costs to the configured file with a timestamp:
```
2023-10-15 14:30:22 - [model-name] Total Costs: 0.05 input / 0.03 output = 0.08 total
```

Each session exit will append a new line to the file, creating a history of your cost usage.