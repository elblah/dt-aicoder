"""
Tiered Cost Display Plugin

This plugin extends the cost display functionality to handle models with tiered pricing
based on context length. It displays cost information for both the last request and
accumulated total costs:
"💰 [model-name] Last Request: 0.01 input / 0.00 output = 0.01 total (12K prompt tokens, Tier 1)"
"💰 [model-name] Total Costs: 0.05 input / 0.03 output = 0.08 total"

The plugin automatically detects tiered pricing models and calculates costs based on
the appropriate pricing tier determined by context length.

Enhanced Features:
- Configurable enable/disable option
- Configurable file path for saving cost data
- Automatic saving of usage data on exit
- Environment variable overrides for fixed pricing (disables multitier support)

Environment Variable Overrides:
- INPUT_TOKEN_COST: Fixed cost per 1 million input tokens (overrides all model configurations)
- OUTPUT_TOKEN_COST: Fixed cost per 1 million output tokens (overrides all model configurations)

When both environment variables are set, they take precedence over all model-specific
pricing configurations and disable multitier support, providing simple fixed pricing.
"""

import os
import functools
import atexit
from datetime import datetime, timedelta
from aicoder.api_handler import APIHandlerMixin

# Plugin configuration
PLUGIN_ENABLED = os.environ.get("TIERED_COST_PLUGIN_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)
COST_DATA_FILE = os.environ.get("TIERED_COST_DATA_FILE", "./.tiered_cost_data.txt")

# Environment variable override configuration (fixed pricing, no multitier support)
INPUT_TOKEN_COST_ENV = os.environ.get("INPUT_TOKEN_COST")
OUTPUT_TOKEN_COST_ENV = os.environ.get("OUTPUT_TOKEN_COST")

# Model pricing with tiered support
MODELS_PRICES = {
    # OpenAI
    "gpt-5-nano": {"INPUT": 0.05, "OUTPUT": 0.40},
    "openai": {"INPUT": 0.05, "OUTPUT": 0.40},
    # Qwen with tiered pricing
    "qwen3-coder-plus": {
        "tiers": [
            {"max_tokens": 32768, "INPUT": 1.00, "OUTPUT": 5.00},  # 0-32K
            {"max_tokens": 131072, "INPUT": 1.80, "OUTPUT": 9.00},  # 32K-128K
            {"max_tokens": 262144, "INPUT": 3.00, "OUTPUT": 15.00},  # 128K-256K
            {"max_tokens": float("inf"), "INPUT": 6.00, "OUTPUT": 60.00},  # 256K+
        ]
    },
    "qwen3-coder-flash": {
        "tiers": [
            {"max_tokens": 32768, "INPUT": 0.3, "OUTPUT": 1.50},  # 0-32K
            {"max_tokens": 131072, "INPUT": 0.5, "OUTPUT": 2.50},  # 32K-128K
            {"max_tokens": 262144, "INPUT": 0.8, "OUTPUT": 4.00},  # 128K-256K
            {"max_tokens": float("inf"), "INPUT": 1.6, "OUTPUT": 9.6},  # 256K+
        ]
    },
    # Google models
    "gemini-2.5-pro": {
        "tiers": [
            {"max_tokens": 200000, "INPUT": 1.25, "OUTPUT": 10.0},  # 0-200K
            {"max_tokens": float("inf"), "INPUT": 2.50, "OUTPUT": 15.0},  # 200K+
        ]
    },
    "gemini-2.5-flash": {"INPUT": 0.30, "OUTPUT": 2.50},
    # Cerebras
    "qwen-3-coder-480b": {"INPUT": 2.00, "OUTPUT": 2.00},
    # Z.AI
    "glm-4.5": {"INPUT": 0.33, "OUTPUT": 1.32},
    # Default fallback
    "default": {"INPUT": 2.00, "OUTPUT": 2.00},
}

# Store last request token information
_last_request_tokens = {"prompt_tokens": 0, "completion_tokens": 0}

# Store accumulated costs only (tokens and requests come from stats object)
_accumulated_costs = {
    "input_cost": 0.0,
    "output_cost": 0.0,
    "total_cost": 0.0,
}


def get_model_name() -> str:
    """Get the model name from the same source as /model command."""
    # Read from aicoder.config.API_MODEL to match the /model command behavior
    try:
        import aicoder.config

        return aicoder.config.API_MODEL
    except (ImportError, AttributeError):
        # Fallback to environment variables if config is not available
        model = (
            os.environ.get("OPENAI_MODEL")
            or os.environ.get("MODEL")
            or os.environ.get("AI_MODEL")
            or "default"
        )
        return model


def get_pricing_tier(model_pricing, prompt_tokens: int) -> tuple[dict, int]:
    """Determine the appropriate pricing tier based on prompt token count.

    Returns:
        Tuple of (pricing_tier, tier_index)
    """
    # Check if this is environment variable override pricing (no multitier support)
    if INPUT_TOKEN_COST_ENV and OUTPUT_TOKEN_COST_ENV:
        # For environment variable overrides, return the pricing as-is with tier index 0
        return model_pricing, 0

    if "tiers" not in model_pricing:
        return model_pricing, 0

    tiers = model_pricing["tiers"]
    for i, tier in enumerate(tiers):
        if prompt_tokens <= tier["max_tokens"]:
            return tier, i + 1
    # If no tier matched, return the last (highest) tier
    return tiers[-1], len(tiers)


def get_model_pricing(model_name: str) -> dict:
    """Get pricing for a specific model, with fallback to default.

    Environment variable overrides (INPUT_TOKEN_COST and OUTPUT_TOKEN_COST) take precedence
    and provide fixed pricing without multitier support.
    """
    # Check for environment variable overrides first (fixed pricing, no multitier)
    if INPUT_TOKEN_COST_ENV and OUTPUT_TOKEN_COST_ENV:
        try:
            input_cost = float(INPUT_TOKEN_COST_ENV)
            output_cost = float(OUTPUT_TOKEN_COST_ENV)
            return {"INPUT": input_cost, "OUTPUT": output_cost}
        except ValueError:
            # If conversion fails, fall back to regular pricing
            pass

    # Try exact match first
    if model_name in MODELS_PRICES:
        return MODELS_PRICES[model_name]

    # Try partial match (useful for versioned models)
    for model_key in MODELS_PRICES:
        if model_key in model_name:
            return MODELS_PRICES[model_key]

    # Fallback to default pricing
    return MODELS_PRICES["default"]


def calculate_cost(
    prompt_tokens: int, completion_tokens: int, model_name: str = None
) -> tuple[float, float, float, dict, int]:
    """Calculate the cost based on prompt and completion tokens.

    Returns:
        Tuple of (input_cost, output_cost, total_cost, pricing_tier, tier_index)
    """
    if model_name is None:
        model_name = get_model_name()

    model_pricing = get_model_pricing(model_name)
    pricing_tier, tier_index = get_pricing_tier(model_pricing, prompt_tokens)

    input_cost = (prompt_tokens / 1_000_000) * pricing_tier["INPUT"]
    output_cost = (completion_tokens / 1_000_000) * pricing_tier["OUTPUT"]
    total_cost = input_cost + output_cost
    return input_cost, output_cost, total_cost, pricing_tier, tier_index


def format_token_count(tokens: int) -> str:
    """Format token count in a readable way (e.g., 45K instead of 45234)."""
    if tokens >= 1_000_000:
        return f"{tokens // 1_000_000}M"
    elif tokens >= 1_000:
        return f"{tokens // 1_000}K"
    else:
        return str(tokens)


def format_cost_display(
    input_cost: float,
    output_cost: float,
    total_cost: float,
    model_name: str,
    prompt_tokens: int = 0,
    tier_index: int = 0,
    has_tiers: bool = False,
    display_type: str = "last",
) -> str:
    """Format the cost display string with optional tier information (rounded for screen display)."""
    if display_type == "last":
        base_display = f"[{model_name}] Last Request: {input_cost:.2f} input / {output_cost:.2f} output = {total_cost:.2f} total"
        # Add token and tier information if applicable
        if prompt_tokens > 0 and has_tiers and tier_index > 0:
            return f"{base_display} ({format_token_count(prompt_tokens)} prompt tokens, Tier {tier_index})"
        elif prompt_tokens > 0:
            return f"{base_display} ({format_token_count(prompt_tokens)} prompt tokens)"
        else:
            return base_display
    else:  # total display
        return f"[{model_name}] Total Costs: {input_cost:.2f} input / {output_cost:.2f} output = {total_cost:.2f} total"


def format_cost_for_file(
    input_cost: float,
    output_cost: float,
    total_cost: float,
    model_name: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    requests: int = 0,
    session_start: datetime = None,
    api_time_spent: float = 0.0,
) -> str:
    """Format the cost for file storage with full precision (no rounding) and comprehensive session info."""
    avg_cost_per_request = total_cost / requests if requests > 0 else 0
    avg_input_tokens = prompt_tokens / requests if requests > 0 else 0
    avg_output_tokens = completion_tokens / requests if requests > 0 else 0
    
    # Calculate session duration
    session_duration = ""
    if session_start:
        duration = datetime.now() - session_start
        session_duration = str(timedelta(seconds=int(duration.total_seconds())))
    
    # Calculate TPS (tokens per second) based on API call duration - using output tokens only
    tps = 0
    if api_time_spent > 0:
        tps = completion_tokens / api_time_spent
    
    return (f"[{model_name}] Total Costs: {input_cost:.6f} input / {output_cost:.6f} output = {total_cost:.6f} total "
            f"({prompt_tokens} input tokens, {completion_tokens} output tokens, {requests} requests, "
            f"avg: {avg_cost_per_request:.6f}/request, {avg_input_tokens:.0f} input tokens/request, {avg_output_tokens:.0f} output tokens/request"
            f"{f', duration: {session_duration}' if session_duration else ''}"
            f"{f', TPS: {tps:.1f}' if tps > 0 else ''})")


def save_cost_data():
    """Save the accumulated cost data to a file with timestamp only if there were actual API requests."""
    if not PLUGIN_ENABLED:
        return

    # Get stats instance
    if _stats_instance is None:
        _try_get_stats_instance()
    
    # Only save if there were actual tokens processed (either input or output tokens > 0)
    if _stats_instance is None or (_stats_instance.prompt_tokens <= 0 and _stats_instance.completion_tokens <= 0):
        if os.environ.get("DEBUG", "0") == "1":
            print("ℹ️  No costs to save (no tokens processed)")
        return

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(COST_DATA_FILE), exist_ok=True)

        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Format the total costs line with full precision for file storage
        model_name = get_model_name()
        session_start = datetime.fromtimestamp(_stats_instance.session_start_time)
        api_time_spent = getattr(_stats_instance, 'api_time_spent', 0.0)
        total_cost_display = format_cost_for_file(
            _accumulated_costs["input_cost"],
            _accumulated_costs["output_cost"],
            _accumulated_costs["total_cost"],
            model_name,
            _stats_instance.prompt_tokens,
            _stats_instance.completion_tokens,
            _stats_instance.api_requests,
            session_start,
            api_time_spent,
        )

        # Create the line to save
        line = f"{timestamp} - {total_cost_display}\n"

        # Append to file
        with open(COST_DATA_FILE, "a") as f:
            f.write(line)

        if os.environ.get("DEBUG", "0") == "1":
            print(f"✅ Cost data saved to {COST_DATA_FILE}")
    except Exception as e:
        if os.environ.get("DEBUG", "0") == "1":
            print(f"⚠️  Failed to save cost data: {e}")


# Register the save function to run on exit
atexit.register(save_cost_data)

# Store reference to stats instance
_stats_instance = None

def on_before_user_prompt():
    """Called before user prompt is displayed - show cost information."""
    if not PLUGIN_ENABLED:
        return

    # Try to get stats instance if we don't have it yet
    if _stats_instance is None:
        _try_get_stats_instance()

    # Only display cost if we have a stats instance and tokens
    if _stats_instance is not None:
        # Check for current_prompt_size first (new field), then fall back to cumulative prompt_tokens
        has_current_prompt_size = (
            hasattr(_stats_instance, "current_prompt_size")
            and _stats_instance.current_prompt_size > 0
        )
        has_prompt_tokens = _stats_instance.prompt_tokens > 0

        if (
            has_current_prompt_size
            or has_prompt_tokens
            or _stats_instance.completion_tokens > 0
        ):
            model_name = get_model_name()
            # Use current_prompt_size for the last request cost calculation when available
            current_prompt_size = getattr(_stats_instance, "current_prompt_size", 0)
            input_cost, output_cost, total_cost, pricing_tier, tier_index = (
                calculate_cost(
                    _last_request_tokens["prompt_tokens"]
                    or current_prompt_size
                    or _stats_instance.prompt_tokens,  # Fallback to cumulative for backward compatibility
                    _last_request_tokens["completion_tokens"]
                    or _stats_instance.completion_tokens,
                    model_name,
                )
            )

            # Check if model has tiers
            model_pricing = get_model_pricing(model_name)
            has_tiers = "tiers" in model_pricing and len(model_pricing["tiers"]) > 1

            # Only show cost if it's greater than zero
            if total_cost > 0:
                # Display last request cost
                last_cost_display = format_cost_display(
                    input_cost,
                    output_cost,
                    total_cost,
                    model_name,
                    _last_request_tokens["prompt_tokens"]
                    or _stats_instance.prompt_tokens,
                    tier_index,
                    has_tiers,
                    "last",
                )

                # Display accumulated costs
                total_cost_display = format_cost_display(
                    _accumulated_costs["input_cost"],
                    _accumulated_costs["output_cost"],
                    _accumulated_costs["total_cost"],
                    model_name,
                    0,
                    0,
                    False,
                    "total",
                )

                # Print both cost displays in a noticeable way (yellow color with money emoji)
                print(
                    f"\n\033[93m💰 {last_cost_display}\033[0m"
                )  # Yellow color for visibility
                print(
                    f"\033[93m💰 {total_cost_display}\033[0m"
                )  # Yellow color for visibility
            elif total_cost == 0:
                # Model price not found
                print(
                    f"\n\033[93m💰 Model price not found for [{model_name}]\033[0m"
                )


def _try_get_stats_instance():
    """Try to get the stats instance from the global namespace."""
    global _stats_instance

    # Try to find stats instance in common places
    import gc
    
    # Import stats class safely
    try:
        from aicoder.stats import Stats
    except ImportError:
        # In plugin context, might need different import
        try:
            import aicoder.stats as stats_module
            Stats = stats_module.Stats
        except ImportError:
            # Can't find stats class, skip
            return

    # Look for Stats instances in garbage collector
    for obj in gc.get_objects():
        if isinstance(obj, Stats):
            _stats_instance = obj
            return


# No longer monkey-patching input function - using event hooks instead

# Also track token usage from API responses

# Store original method
_original_make_api_request = APIHandlerMixin._make_api_request


# Create wrapped version
@functools.wraps(_original_make_api_request)
def token_tracking_make_api_request(
    self, messages, disable_streaming_mode=False, disable_tools=False
):
    """Track token usage from API requests and accumulate costs."""
    global _last_request_tokens, _accumulated_costs

    # Call original method
    response = _original_make_api_request(
        self, messages, disable_streaming_mode, disable_tools
    )

    # Only track costs if plugin is enabled
    if PLUGIN_ENABLED and response and isinstance(response, dict):
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        if prompt_tokens > 0 or completion_tokens > 0:
            # Store for cost display
            _last_request_tokens["prompt_tokens"] = prompt_tokens
            _last_request_tokens["completion_tokens"] = completion_tokens

            # Calculate and accumulate costs
            model_name = get_model_name()
            input_cost, output_cost, total_cost, _, _ = calculate_cost(
                prompt_tokens, completion_tokens, model_name
            )

            # Update accumulated costs only (tokens come from stats object)
            _accumulated_costs["input_cost"] += input_cost
            _accumulated_costs["output_cost"] += output_cost
            _accumulated_costs["total_cost"] += total_cost

    return response


# Monkey patch the class only if plugin is enabled
if PLUGIN_ENABLED:
    APIHandlerMixin._make_api_request = token_tracking_make_api_request

# Only show plugin loading messages in debug mode
if os.environ.get("DEBUG", "0") == "1":
    if PLUGIN_ENABLED:
        print("✅ Tiered cost display plugin loaded")
        print("   - Shows cost information above prompts when tokens are present")
        print("   - Automatically detects model and applies appropriate pricing")
        print("   - Supports tiered pricing for Qwen models based on context length")
        print("   - Supports environment variable overrides for fixed pricing:")
        print("     - Set INPUT_TOKEN_COST=<cost_per_1M_tokens> for input token cost")
        print("     - Set OUTPUT_TOKEN_COST=<cost_per_1M_tokens> for output token cost")
        print(
            "     - Environment overrides take precedence and disable multitier support"
        )
        print(
            "   - Format: 💰 [model-name] Last Request: 0.01 input / 0.00 output = 0.01 total (12K prompt tokens, Tier 1)"
        )
        print(
            "            💰 [model-name] Total Costs: 0.05 input / 0.03 output = 0.08 total"
        )
        print(f"   - Cost data will be saved to: {COST_DATA_FILE}")

        # Show if environment variable overrides are active
        if INPUT_TOKEN_COST_ENV and OUTPUT_TOKEN_COST_ENV:
            print(
                f"   - Using environment variable overrides: INPUT_TOKEN_COST={INPUT_TOKEN_COST_ENV}, OUTPUT_TOKEN_COST={OUTPUT_TOKEN_COST_ENV}"
            )
    else:
        print("⚠️  Tiered cost display plugin is disabled")
        print("   - Set TIERED_COST_PLUGIN_ENABLED=true to enable")
        print("   - Set TIERED_COST_DATA_FILE to configure the save path")
        print(
            "   - Set INPUT_TOKEN_COST and OUTPUT_TOKEN_COST for fixed pricing overrides"
        )
