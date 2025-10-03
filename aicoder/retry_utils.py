"""
Retry utilities for API requests with common retry logic.
"""

import urllib.error

from .utils import cancellable_sleep

# Import config module for dynamic access to config values
from . import config


class _APIRetryHandlerSingleton:
    """Singleton implementation for API retry handler."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        # Allow bypassing singleton for testing by checking environment
        import os
        test_mode = os.environ.get('AICODER_TEST_MODE') == '1'
        if test_mode:
            # In test mode, create new instances instead of singleton
            print(f"DEBUG: APIRetryHandler.__new__ - Creating new instance (test_mode={test_mode})")
            return super().__new__(cls)
            
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, animator, stats=None):
        # Allow bypassing singleton initialization for testing
        import os
        if os.environ.get('AICODER_TEST_MODE') == '1' or not self._initialized:
            self.animator = animator
            self.stats = stats
            self.retry_attempt_count = 0
            if os.environ.get('AICODER_TEST_MODE') != '1':
                self._initialized = True


class APIRetryHandler(_APIRetryHandlerSingleton):
    """Common retry handler for API requests.
    
    This is implemented as a singleton to ensure all parts of the application
    use the same retry handler instance, preventing multiple instances from
    having different retry counter states.
    
    In test mode (AICODER_TEST_MODE=1), the singleton behavior is disabled.
    """
    pass

    def _calculate_retry_delay(self, base_delay: float = None) -> float:
        """
        Calculate retry delay with exponential backoff.

        Args:
            base_delay: Base delay for rate limiting errors (default: uses configured initial delay)

        Returns:
            float: Calculated delay in seconds
        """
        exponential_enabled = config.ENABLE_EXPONENTIAL_WAIT_RETRY
        fixed_delay_value = config.RETRY_FIXED_DELAY
        
        if exponential_enabled:
            # Exponential backoff: 2, 4, 8, 16, 32, 64, 64, 64, ...
            if base_delay is None:
                base_delay = config.RETRY_INITIAL_DELAY
            delay = min(base_delay * (2**self.retry_attempt_count), config.RETRY_MAX_DELAY)
        else:
            # Fixed delay - use the provided base_delay, or RETRY_FIXED_DELAY if base_delay was None
            delay = base_delay if base_delay is not None else fixed_delay_value

        return delay

    def should_retry_error(self, e: urllib.error.HTTPError, error_content: str = None) -> tuple[bool, int, str]:
        """
        Determine if an HTTP error should be retried.

        Args:
            e: The HTTPError exception
            error_content: Optional pre-read error content (to avoid double-reading)

        Returns:
            tuple: (should_retry, retry_sleep_seconds, error_type)
        """
        # If error_content is not provided, try to read it
        if error_content is None:
            error_content = ""
            try:
                error_content = e.read().decode()
            except Exception:
                pass

        # Check if this error should be retried
        base_delay = config.RETRY_INITIAL_DELAY
        error_type = "Server"

        # Check for specific error codes that should be retried
        if e.code in [502, 429, 524, 503, 504]:
            should_retry = True

            # Special case: Any error that contains rate limiting keywords
            if any(
                keyword in error_content.lower()
                for keyword in [
                    "too many requests",
                    "rate limit",
                    "rate limited",
                    "quota exceeded",
                ]
            ):
                error_type = "Rate limiting"
                base_delay = 10  # Longer base delay for rate limiting

            # Calculate the actual retry delay using exponential backoff or fixed delay
            retry_sleep_secs = self._calculate_retry_delay(base_delay)
            return should_retry, retry_sleep_secs, error_type

        # Special handling for 500 errors - only retry if they contain rate limiting information
        elif e.code == 500:
            # Special case: 500 error that contains "429 Too Many Requests" in the content
            if "429 Too Many Requests" in error_content:
                should_retry = True
                error_type = "Rate limiting"
                base_delay = 10  # Longer base delay for rate limiting
            # Special case: 500 error that contains other rate limiting keywords
            elif any(
                keyword in error_content.lower()
                for keyword in [
                    "too many requests",
                    "rate limit",
                    "rate limited",
                    "quota exceeded",
                ]
            ):
                should_retry = True
                error_type = "Rate limiting"
                base_delay = 10  # Longer base delay for rate limiting
            else:
                # 500 errors without rate limiting indicators should not be retried
                should_retry = False

            if should_retry:
                # Calculate the actual retry delay using exponential backoff or fixed delay
                retry_sleep_secs = self._calculate_retry_delay(base_delay)
                return should_retry, retry_sleep_secs, error_type

        return False, 0, "Unknown"

    def handle_http_error_with_retry(self, e: urllib.error.HTTPError) -> bool:
        """
        Handle HTTP errors with enhanced retry logic.

        Args:
            e: The HTTPError exception

        Returns:
            bool: True if the request should be retried, False if it should not
        """
        if self.stats:
            self.stats.api_errors += 1

        error_content = ""
        try:
            error_content = e.read().decode()
            print(f"\n{config.RED}API Error: {e.code} {e.reason}\n{error_content}{config.RESET}")
        except Exception:
            print(f"\n{config.RED}API Error: {e.code} {e.reason}{config.RESET}")

        should_retry, retry_sleep_secs, error_type = self.should_retry_error(e, error_content)

        if should_retry:
            # Check if we've exceeded maximum retry attempts (if configured)
            if config.RETRY_MAX_ATTEMPTS > 0 and self.retry_attempt_count >= config.RETRY_MAX_ATTEMPTS:
                print(
                    f"{config.RED}    --- Maximum retry attempts ({config.RETRY_MAX_ATTEMPTS}) exceeded. Giving up.{config.RESET}"
                )
                return False  # Don't retry, max attempts reached
            
            print(
                f"{config.YELLOW}    --- {error_type} error detected. Retrying in {retry_sleep_secs} secs... (Press ESC to cancel){config.RESET}"
            )
            # Increment retry attempt counter for exponential backoff
            self.retry_attempt_count += 1
            # Use cancellable sleep to allow user to cancel retries
            if not cancellable_sleep(retry_sleep_secs, self.animator):
                self.animator.stop_animation()
                print(f"\n{config.RED}Retry cancelled by user (ESC).{config.RESET}")
                return False  # Don't retry, user cancelled
            return True  # Retry the request
        elif e.code == 401:
            # 401 - Unauthorized (likely expired token)
            print(
                f"{config.RED}Authentication failed. Please check your API key/token.{config.RESET}"
            )
            print(f"{config.YELLOW}If using OAuth, you may need to refresh your token.{config.RESET}")
            return False  # Don't retry authentication errors

        return False  # Don't retry other errors

    def reset_retry_counter(self):
        """Reset the retry attempt counter. Call this after a successful request."""
        self.retry_attempt_count = 0

    def handle_connection_error(self, e: urllib.error.URLError) -> None:
        """
        Handle connection errors.

        Args:
            e: The URLError exception
        """
        if self.stats:
            self.stats.api_errors += 1
        print(
            f"\n{config.RED}Connection Error: {str(e.reason) if hasattr(e, 'reason') else str(e)}{config.RESET}"
        )
        print(
            f"{config.YELLOW}This may be due to network issues or an expired authentication token.{config.RESET}"
        )
        print(
            f"{config.YELLOW}Please check your connection and authentication credentials.{config.RESET}"
        )
