"""
Retry utilities for API requests with common retry logic.
"""

import urllib.error

from .config import (
    RED,
    YELLOW,
    RESET,
    ENABLE_EXPONENTIAL_WAIT_RETRY,
    RETRY_INITIAL_DELAY,
    RETRY_MAX_DELAY,
    RETRY_FIXED_DELAY,
    RETRY_MAX_ATTEMPTS,
)
from .utils import cancellable_sleep


class _APIRetryHandlerSingleton:
    """Singleton implementation for API retry handler."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, animator, stats=None):
        if not self._initialized:
            self.animator = animator
            self.stats = stats
            self.retry_attempt_count = 0
            self._initialized = True


class APIRetryHandler(_APIRetryHandlerSingleton):
    """Common retry handler for API requests.
    
    This is implemented as a singleton to ensure all parts of the application
    use the same retry handler instance, preventing multiple instances from
    having different retry counter states.
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
        if base_delay is None:
            base_delay = RETRY_INITIAL_DELAY

        if ENABLE_EXPONENTIAL_WAIT_RETRY:
            # Exponential backoff: 2, 4, 8, 16, 32, 64, 64, 64, ...
            delay = min(base_delay * (2**self.retry_attempt_count), RETRY_MAX_DELAY)
        else:
            # Fixed delay
            delay = RETRY_FIXED_DELAY

        return delay

    def should_retry_error(self, e: urllib.error.HTTPError) -> tuple[bool, int, str]:
        """
        Determine if an HTTP error should be retried.

        Args:
            e: The HTTPError exception

        Returns:
            tuple: (should_retry, retry_sleep_seconds, error_type)
        """
        error_content = ""
        try:
            error_content = e.read().decode()
        except Exception:
            pass

        # Check if this error should be retried
        base_delay = RETRY_INITIAL_DELAY
        error_type = "Server"

        # Check for specific error codes that should be retried
        if e.code in [502, 429, 524, 500, 503, 504]:
            should_retry = True

            # Special case: 500 error that contains "429 Too Many Requests" in the content
            if e.code == 500 and "429 Too Many Requests" in error_content:
                error_type = "Rate limiting"
                base_delay = 10  # Longer base delay for rate limiting

            # Special case: Any error that contains rate limiting keywords
            elif any(
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
            print(f"\n{RED}API Error: {e.code} {e.reason}\n{error_content}{RESET}")
        except Exception:
            print(f"\n{RED}API Error: {e.code} {e.reason}{RESET}")

        should_retry, retry_sleep_secs, error_type = self.should_retry_error(e)

        if should_retry:
            # Check if we've exceeded maximum retry attempts (if configured)
            if RETRY_MAX_ATTEMPTS > 0 and self.retry_attempt_count >= RETRY_MAX_ATTEMPTS:
                print(
                    f"{RED}    --- Maximum retry attempts ({RETRY_MAX_ATTEMPTS}) exceeded. Giving up.{RESET}"
                )
                return False  # Don't retry, max attempts reached
            
            print(
                f"{YELLOW}    --- {error_type} error detected. Retrying in {retry_sleep_secs} secs... (Press ESC to cancel){RESET}"
            )
            # Increment retry attempt counter for exponential backoff
            self.retry_attempt_count += 1
            # Use cancellable sleep to allow user to cancel retries
            if not cancellable_sleep(retry_sleep_secs, self.animator):
                self.animator.stop_animation()
                print(f"\n{RED}Retry cancelled by user (ESC).{RESET}")
                return False  # Don't retry, user cancelled
            return True  # Retry the request
        elif e.code == 401:
            # 401 - Unauthorized (likely expired token)
            print(
                f"{RED}Authentication failed. Please check your API key/token.{RESET}"
            )
            print(f"{YELLOW}If using OAuth, you may need to refresh your token.{RESET}")
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
            f"\n{RED}Connection Error: {str(e.reason) if hasattr(e, 'reason') else str(e)}{RESET}"
        )
        print(
            f"{YELLOW}This may be due to network issues or an expired authentication token.{RESET}"
        )
        print(
            f"{YELLOW}Please check your connection and authentication credentials.{RESET}"
        )
