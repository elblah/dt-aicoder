# Environment Variable Override Feature Summary

## Overview

The tiered cost display plugin has been enhanced to support environment variable overrides for input and output token costs. This feature allows users to set fixed pricing that overrides all model-specific configurations and disables multitier support.

## Changes Made

### 1. Plugin Configuration (`tiered_cost_display_plugin.py`)

#### New Environment Variables Added:
- `INPUT_TOKEN_COST`: Fixed cost per 1 million input tokens
- `OUTPUT_TOKEN_COST`: Fixed cost per 1 million output tokens

#### Modified Functions:

**`get_model_pricing()` function:**
- Added check for environment variable overrides at the beginning
- If both `INPUT_TOKEN_COST` and `OUTPUT_TOKEN_COST` are set, creates a simple pricing dictionary
- Falls back to original logic if environment variables are not set or invalid

**`get_pricing_tier()` function:**
- Added check for environment variable overrides
- Returns tier index 0 when environment overrides are active (no multitier support)

#### Enhanced Debug Output:
- Added information about environment variable override support
- Shows active overrides when DEBUG mode is enabled

### 2. Documentation (`README.md`)

#### New Sections Added:
- **Fixed Pricing Overrides**: Detailed explanation of the new environment variables
- **Usage Examples**: Multiple examples showing how to use the overrides
- **Behavior Explanation**: Clear description of how overrides take precedence and disable multitier support

#### Updated Configuration Section:
- Separated basic configuration from fixed pricing overrides
- Added comprehensive examples for different use cases

### 3. Testing

#### New Test Files Created:
- **`test_env_overrides.py`**: Comprehensive unit tests for the new functionality
- **`demo_env_overrides.py`**: Demonstration script showing how the feature works

#### Test Coverage:
- ✅ Default behavior without environment variables
- ✅ Environment variable overrides taking precedence
- ✅ Multitier support being disabled when overrides are active
- ✅ Fallback to default pricing with invalid environment variables
- ✅ Cost calculation accuracy with overrides

## Usage Examples

### Basic Fixed Pricing
```bash
# Set fixed pricing for all models
INPUT_TOKEN_COST=0.50 OUTPUT_TOKEN_COST=2.00 python -m aicoder
```

### Combined with Plugin Configuration
```bash
# Enable plugin with custom save path and fixed pricing
TIERED_COST_PLUGIN_ENABLED=true \
TIERED_COST_DATA_FILE=./my_costs.txt \
INPUT_TOKEN_COST=1.00 \
OUTPUT_TOKEN_COST=5.00 \
python -m aicoder
```

### Debug Mode with Overrides
```bash
# See debug information with environment overrides
DEBUG=1 INPUT_TOKEN_COST=0.75 OUTPUT_TOKEN_COST=3.50 python -m aicoder
```

## Behavior

### When Environment Variables Are Set:
1. **Priority**: Environment variables take precedence over all model-specific pricing
2. **Multitier Support**: Disabled - all models use the same fixed pricing
3. **Tier Display**: No tier information shown in cost display (tier index = 0)
4. **Fallback**: Invalid values fall back to default pricing

### When Environment Variables Are Not Set:
1. **Priority**: Uses original model-specific pricing configurations
2. **Multitier Support**: Enabled for models that support it (e.g., Qwen models)
3. **Tier Display**: Shows tier information when applicable
4. **Fallback**: Uses default pricing for unknown models

## Cost Calculation

### With Environment Overrides:
```
INPUT_TOKEN_COST=1.25 OUTPUT_TOKEN_COST=5.00
For 1M input tokens + 0.5M output tokens:
- Input cost: (1,000,000 / 1,000,000) * 1.25 = $1.25
- Output cost: (500,000 / 1,000,000) * 5.00 = $2.50
- Total cost: $3.75
```

### Without Environment Overrides (Original Behavior):
```
For gpt-5-nano with 1M input tokens + 0.5M output tokens:
- Input cost: (1,000,000 / 1,000,000) * 0.05 = $0.05
- Output cost: (500,000 / 1,000,000) * 0.40 = $0.20
- Total cost: $0.25
```

## Output Format Comparison

### With Environment Overrides:
```
💰 [model-name] Last Request: 1.25 input / 2.50 output = 3.75 total (1M prompt tokens)
💰 [model-name] Total Costs: 1.25 input / 2.50 output = 3.75 total
```

### Without Environment Overrides (with multitier):
```
💰 [model-name] Last Request: 0.05 input / 0.20 output = 0.25 total (1M prompt tokens, Tier 2)
💰 [model-name] Total Costs: 0.05 input / 0.20 output = 0.25 total
```

## Backward Compatibility

The changes are fully backward compatible:
- Existing functionality remains unchanged when environment variables are not set
- All original features continue to work as before
- No breaking changes to existing API or configuration
- Original multitier pricing is preserved for supported models

## Testing Verification

All tests pass successfully:
- ✅ 5 unit tests covering all scenarios
- ✅ Demonstration script shows expected behavior
- ✅ Real-world testing with environment variables works correctly
- ✅ Fallback behavior works with invalid values
- ✅ Debug output correctly shows override status