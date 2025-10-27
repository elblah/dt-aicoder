"""
Auto Retry Plugin

This plugin provides automatic retry functionality for API errors, specifically
designed to handle the case where you get "500 Internal Server Error" with
"429 Too Many Requests" content, as well as other common API errors.

Features:
- Automatic retry for 500 errors containing 429 content (your specific case)
- Automatic retry for common HTTP errors (502, 503, 504, 429)
- Automatic retry for rate limiting errors regardless of HTTP code
- Configurable retry delays and counts
- ESC key support to cancel retries
- User-friendly error messages

Configuration:
Set these environment variables to customize retry behavior:
- AUTO_RETRY_ENABLED=1      # Enable the plugin (default: enabled when loaded)
- AUTO_RETRY_DELAY=5       # Delay between retries in seconds (default: 5)
- AUTO_RETRY_MAX_RETRIES=3  # Maximum number of retries (default: 3)
"""

import os
import time
import functools
from typing import Dict, Any, List


def patched_make_api_request(original_method):
    """Patch for _make_api_request to add enhanced retry logic."""

    @functools.wraps(original_method)
    def wrapper(
        self,
        messages: List[Dict[str, Any]],
        disable_streaming_mode: bool = False,
        disable_tools: bool = False,
    ):
        # Get configuration from environment variables
        retry_delay = int(os.environ.get("AUTO_RETRY_DELAY", "5"))
        max_retries = int(os.environ.get("AUTO_RETRY_MAX_RETRIES", "3"))

        attempt = 0

        while True:
            try:
                # Try the original API request
                return original_method(
                    self, messages, disable_streaming_mode, disable_tools
                )
            except Exception as e:
                attempt += 1

                # Check if we should retry this error
                should_retry = False
                error_content = ""
                retry_delay_for_this_attempt = retry_delay

                # Get error content if it's an HTTP error
                if hasattr(e, "read"):
                    try:
                        error_content = e.read().decode()
                    except (AttributeError, UnicodeDecodeError, OSError):
                        error_content = str(e)
                else:
                    error_content = str(e)

                # Check for specific error conditions that should be retried
                if hasattr(e, "code"):
                    # HTTP error with code
                    if e.code in [502, 503, 504, 429, 500]:
                        should_retry = True

                    # Special case: 500 error with 429 content (your specific case)
                    if e.code == 500 and "429 Too Many Requests" in error_content:
                        should_retry = True
                        retry_delay_for_this_attempt = (
                            10  # Longer delay for rate limiting
                        )

                # Check for rate limiting keywords in any error
                rate_limiting_keywords = [
                    "too many requests",
                    "rate limit",
                    "rate limited",
                    "quota exceeded",
                    "429",
                    "api rate",
                    "request limit",
                ]
                if any(
                    keyword.lower() in error_content.lower()
                    for keyword in rate_limiting_keywords
                ):
                    should_retry = True
                    retry_delay_for_this_attempt = 10  # Longer delay for rate limiting

                # Check if we've exceeded max retries
                if attempt > max_retries:
                    should_retry = False

                if should_retry:
                    # Log the retry attempt
                    error_type = (
                        "Rate limiting"
                        if any(
                            keyword.lower() in error_content.lower()
                            for keyword in rate_limiting_keywords
                        )
                        else "Server"
                    )
                    print(
                        f"*** {error_type} error detected. Retrying in {retry_delay_for_this_attempt}s (attempt {attempt}/{max_retries}) (Press ESC to cancel)"
                    )

                    # Try to use cancellable sleep if available
                    try:
                        from aicoder.utils import cancellable_sleep

                        if not cancellable_sleep(
                            retry_delay_for_this_attempt,
                            getattr(self, "animator", None),
                        ):
                            print("\n Retry cancelled by user (ESC).")
                            return None
                    except ImportError:
                        # Fall back to regular sleep
                        time.sleep(retry_delay_for_this_attempt)

                    continue
                else:
                    # Don't retry - re-raise the exception
                    raise

    return wrapper


def install_auto_retry_plugin():
    """Install the auto retry plugin by patching the API handler."""
    try:
        # Import the API handler class
        from aicoder.api_handler import APIHandlerMixin

        # Check if we've already patched
        if hasattr(APIHandlerMixin._make_api_request, "_auto_retry_patched"):
            print("[✓] Auto retry plugin already installed")
            return True

        # Store reference to original method
        original_method = APIHandlerMixin._make_api_request

        # Create patched method
        patched_method = patched_make_api_request(original_method)
        patched_method._auto_retry_patched = True
        patched_method._original_method = original_method

        # Apply the patch
        APIHandlerMixin._make_api_request = patched_method

        print("[✓] Auto retry plugin installed successfully")
        print("   Features:")
        print("   - Automatic retry for 500 errors containing 429 content")
        print("   - Automatic retry for HTTP errors: 502, 503, 504, 429, 500")
        print("   - Automatic retry for rate limiting errors")
        print("   - ESC key support to cancel retries")
        print("   - Configurable retry delays and counts")
        print()
        print("   Configuration environment variables:")
        print("   - AUTO_RETRY_DELAY=5       # Delay between retries in seconds")
        print("   - AUTO_RETRY_MAX_RETRIES=3  # Maximum number of retries")

        return True

    except ImportError as e:
        # This is expected when running outside of AI Coder
        print(f"[i] Auto retry plugin loaded (API handler not available: {e})")
        return True
    except Exception as e:
        print(f"[X] Failed to install auto retry plugin: {e}")
        return False


# Install the plugin when loaded
if install_auto_retry_plugin():
    print("[✓] Auto retry plugin loaded")
else:
    print("[X] Auto retry plugin failed to load")
