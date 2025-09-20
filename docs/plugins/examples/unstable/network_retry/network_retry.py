"""
Network Retry Plugin

This plugin enhances AI Coder's network error handling by implementing configurable
retry logic for different types of network errors. It can automatically retry
failed API requests based on error codes, with different strategies for different
types of errors.

Features:
- Configurable retry counts for different HTTP error codes
- Infinite retry for specific errors (like 502 Bad Gateway)
- Exponential backoff with jitter
- Detailed logging of retry attempts
- Easy configuration via environment variables

Configuration:
Set these environment variables to customize retry behavior:
- NETWORK_RETRY_500=N     # Number of retries for 500 errors (default: 3)
- NETWORK_RETRY_502=-1    # Number of retries for 502 errors (-1 = infinite)
- NETWORK_RETRY_503=5     # Number of retries for 503 errors (default: 3)
- NETWORK_RETRY_504=3     # Number of retries for 504 errors (default: 3)
- NETWORK_RETRY_DEFAULT=3 # Default retry count for other errors (default: 3)
- NETWORK_RETRY_DELAY=1   # Initial delay in seconds (default: 1.0)
- NETWORK_RETRY_MAX_DELAY=60  # Maximum delay in seconds (default: 60.0)
"""

import os
import time
import random
import functools
from typing import Dict

# Default configuration
DEFAULT_RETRY_CONFIG = {
    500: 3,  # Internal Server Error
    502: -1,  # Bad Gateway (infinite retry)
    503: 3,  # Service Unavailable
    504: 3,  # Gateway Timeout
    "default": 3,
}

DEFAULT_DELAY_CONFIG = {"initial": 1.0, "max": 60.0, "multiplier": 2.0, "jitter": 0.1}


def get_retry_config() -> Dict[int, int]:
    """Get retry configuration from environment variables."""
    config = DEFAULT_RETRY_CONFIG.copy()

    # Override with environment variables
    for key, default_value in DEFAULT_RETRY_CONFIG.items():
        env_key = (
            f"NETWORK_RETRY_{key}"
            if isinstance(key, int)
            else f"NETWORK_RETRY_{key.upper()}"
        )
        env_value = os.environ.get(env_key)
        if env_value is not None:
            try:
                config[key] = int(env_value)
            except ValueError:
                print(f"⚠️  Invalid value for {env_key}, using default: {default_value}")

    return config


def get_delay_config() -> Dict[str, float]:
    """Get delay configuration from environment variables."""
    config = DEFAULT_DELAY_CONFIG.copy()

    # Override with environment variables
    env_mappings = {
        "NETWORK_RETRY_DELAY": "initial",
        "NETWORK_RETRY_MAX_DELAY": "max",
        "NETWORK_RETRY_MULTIPLIER": "multiplier",
        "NETWORK_RETRY_JITTER": "jitter",
    }

    for env_key, config_key in env_mappings.items():
        env_value = os.environ.get(env_key)
        if env_value is not None:
            try:
                config[config_key] = float(env_value)
            except ValueError:
                print(
                    f"⚠️  Invalid value for {env_key}, using default: {config[config_key]}"
                )

    return config


def apply_jitter(delay: float, jitter: float) -> float:
    """Apply jitter to delay to prevent thundering herd problem."""
    jitter_amount = delay * jitter
    return delay + random.uniform(-jitter_amount, jitter_amount)


def should_retry(error_code: int, attempt: int, retry_config: Dict[int, int]) -> bool:
    """Determine if we should retry based on error code and attempt count."""
    # Check specific error code config
    if error_code in retry_config:
        max_retries = retry_config[error_code]
        # -1 means infinite retry
        if max_retries == -1:
            return True
        return attempt < max_retries

    # Check default config
    max_retries = retry_config.get("default", 3)
    if max_retries == -1:
        return True
    return attempt < max_retries


def calculate_delay(attempt: int, delay_config: Dict[str, float]) -> float:
    """Calculate delay with exponential backoff."""
    initial = delay_config["initial"]
    max_delay = delay_config["max"]
    multiplier = delay_config["multiplier"]
    jitter = delay_config["jitter"]

    delay = min(initial * (multiplier**attempt), max_delay)
    return apply_jitter(delay, jitter)


def patched_make_api_request(original_method):
    """Patch for _make_api_request to add retry logic."""

    @functools.wraps(original_method)
    def wrapper(self, messages, disable_streaming_mode=False, disable_tools=False):
        # Get configuration
        retry_config = get_retry_config()
        delay_config = get_delay_config()

        attempt = 0
        # last_error = None

        while True:
            try:
                # Try the original API request
                return original_method(
                    self, messages, disable_streaming_mode, disable_tools
                )
            except Exception as e:
                # last_error = e

                # Check if this is an HTTP error we should handle
                error_code = None
                if hasattr(e, "code"):
                    error_code = e.code
                elif "500" in str(e):
                    error_code = 500
                elif "502" in str(e):
                    error_code = 502
                elif "503" in str(e):
                    error_code = 503
                elif "504" in str(e):
                    error_code = 504

                # Determine if we should retry
                if error_code and should_retry(error_code, attempt, retry_config):
                    attempt += 1

                    # Calculate delay
                    delay = calculate_delay(attempt - 1, delay_config)

                    # Log retry attempt
                    error_name = f"HTTP {error_code}" if error_code else "Network Error"
                    max_retries = retry_config.get(
                        error_code, retry_config.get("default", 3)
                    )
                    retry_info = (
                        "infinite retries"
                        if max_retries == -1
                        else f"{max_retries} max retries"
                    )

                    print(
                        f"🔄 {error_name} - Retrying in {delay:.1f}s (attempt {attempt}, {retry_info}) (Press ESC to cancel)"
                    )
                    print(f"   Error details: {str(e)[:100]}...")

                    # Try to import cancellable_sleep, fall back to time.sleep if not available
                    try:
                        from aicoder.utils import cancellable_sleep

                        # Use cancellable sleep to allow user to cancel retries
                        if not cancellable_sleep(
                            delay, getattr(self, "animator", None)
                        ):
                            print("\n Retry cancelled by user (ESC).")
                            return None
                    except ImportError:
                        # Fall back to regular sleep if cancellable_sleep is not available
                        time.sleep(delay)

                    continue
                else:
                    # Don't retry - re-raise the exception
                    raise

    return wrapper


def install_network_retry_plugin():
    """Install the network retry plugin by patching the API handler."""
    try:
        # Import the API handler class
        from aicoder.api_handler import APIHandlerMixin

        # Check if we've already patched
        if hasattr(APIHandlerMixin._make_api_request, "_network_retry_patched"):
            print("✅ Network retry plugin already installed")
            return True

        # Store reference to original method
        original_method = APIHandlerMixin._make_api_request

        # Create patched method
        patched_method = patched_make_api_request(original_method)
        patched_method._network_retry_patched = True
        patched_method._original_method = original_method

        # Apply the patch
        APIHandlerMixin._make_api_request = patched_method

        print("✅ Network retry plugin installed successfully")
        print("   Features:")
        print("   - Automatic retry for HTTP 500, 502, 503, 504 errors")
        print("   - Infinite retry for 502 Bad Gateway errors")
        print("   - Exponential backoff with jitter")
        print("   - Configurable via environment variables")
        print("   - Detailed retry logging")
        print("   - ESC key support to cancel retries")
        print()
        print("   Configuration environment variables:")
        print("   - NETWORK_RETRY_500=N     # Retries for 500 errors (default: 3)")
        print("   - NETWORK_RETRY_502=-1    # Retries for 502 errors (-1 = infinite)")
        print("   - NETWORK_RETRY_503=N     # Retries for 503 errors (default: 3)")
        print("   - NETWORK_RETRY_504=N     # Retries for 504 errors (default: 3)")
        print("   - NETWORK_RETRY_DEFAULT=N # Default retry count (default: 3)")
        print("   - NETWORK_RETRY_DELAY=S   # Initial delay in seconds (default: 1.0)")
        print("   - NETWORK_RETRY_MAX_DELAY=S # Max delay in seconds (default: 60.0)")

        return True

    except Exception as e:
        print(f"❌ Failed to install network retry plugin: {e}")
        return False


# Install the plugin when loaded
if install_network_retry_plugin():
    print("✅ Network retry plugin loaded")
else:
    print("❌ Network retry plugin failed to load")
