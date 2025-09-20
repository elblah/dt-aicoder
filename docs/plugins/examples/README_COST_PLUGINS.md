# Cost Tracking Plugins

This directory contains several plugins for tracking and displaying API usage costs. These plugins are organized into two categories:

- **stable**: Plugins that have been tested and are working properly
- **unstable**: Plugins that are provided as examples but may not have been fully tested

## Stable Plugin

### 17_tiered_cost_display_plugin.py
Enhanced version of the cost display plugin with support for tiered pricing.
- Handles models with context-length-based pricing (like Qwen)
- Automatically determines the correct pricing tier based on prompt token count
- Same display format as the original plugin

## Unstable Plugins

The following cost-related plugins are in the unstable folder:

### 05_cost_tracking_plugin.py
Basic cost tracking with simple per-million-token pricing.
- Tracks cumulative costs across all API calls
- Adds `/cost` command to view cost information
- Uses fixed pricing (Anthropic Claude 3.5 Sonnet as default)

### 16_cost_display_plugin.py
Displays cost information above prompts in a user-friendly format.
- Shows costs automatically when prompts contain ">"
- Format: `💰 [model-name] Cost: 0.04 input / 0.03 output = 0.07 total`
- Supports multiple model types with simple pricing

### 18_tiered_cost_tracking_plugin.py
Enhanced version of the cost tracking plugin with support for tiered pricing.
- Tracks costs with tiered pricing support
- Adds `/cost` command with detailed cost information
- Maintains request history for detailed analysis

## Tiered Pricing Support

Some models like Qwen have different pricing based on context length:

- **0-32K tokens**: Tier 1 pricing
- **32K-128K tokens**: Tier 2 pricing  
- **128K-32768K tokens**: Tier 3 pricing
- **32768K+ tokens**: Tier 4 pricing

The tiered plugins automatically determine the correct pricing tier based on the number of input tokens in each request.

## Usage

To use any of these plugins, copy them from their respective directories (stable or unstable) to your plugins directory and ensure they're loaded by the application.

For the display plugins, costs will automatically appear above prompts that contain ">". 

For the tracking plugins, use the `/cost` command to view cost information.

## Customization

You can customize the pricing models by modifying the `MODELS_PRICES` dictionary in each plugin file. Add new models or adjust pricing as needed for your specific API provider.