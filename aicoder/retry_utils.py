"""
Retry utilities for API requests with common retry logic.
"""

import os
import re
import urllib.error
from datetime import datetime
from pathlib import Path

from .utils import cancellable_sleep, wmsg, emsg
from .api.errors import APIErrors

# Import config module for dynamic access to config values
from . import config


class ShouldRetryException(Exception):
    """Exception to signal that a request should be retried."""

    def __init__(self, exception):
        self.original_exception = exception
        super().__init__("Request should be retried")


class ConnectionDroppedException(Exception):
    """Custom exception for connection dropped errors that should be retried."""

    pass


class _APIRetryHandlerSingleton:
    """Singleton implementation for API retry handler."""

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        # Allow bypassing singleton for testing by checking environment
        import os

        test_mode = os.environ.get("AICODER_TEST_MODE") == "1"
        if test_mode:
            # In test mode, create new instances instead of singleton
            print(
                f"DEBUG: APIRetryHandler.__new__ - Creating new instance (test_mode={test_mode})"
            )
            return super().__new__(cls)

        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, animator, stats=None):
        # Allow bypassing singleton initialization for testing
        import os

        if os.environ.get("AICODER_TEST_MODE") == "1" or not self._initialized:
            self.animator = animator
            self.stats = stats
            self.retry_attempt_count = 0
            self._regex_cache = {}  # Cache for compiled regex patterns
            if os.environ.get("AICODER_TEST_MODE") != "1":
                self._initialized = True


class APIRetryHandler(_APIRetryHandlerSingleton):
    """Common retry handler for API requests.

    This is implemented as a singleton to ensure all parts of the application
    use the same retry handler instance, preventing multiple instances from
    having different retry counter states.

    In test mode (AICODER_TEST_MODE=1), the singleton behavior is disabled.
    """

    def _check_retry_patterns(
        self, error_content: str, http_code: int = None
    ) -> tuple[str, str]:
        """Check if error matches retry_yes.conf or retry_no.conf patterns.

        Logic:
        1. If matches retry_no.conf → return ("no", pattern)
        2. If matches retry_yes.conf → return ("yes", pattern)
        3. If neither matches → return ("none", "")

        Always reloads the config files to pick up changes dynamically.
        All patterns are case-insensitive.

        Args:
            error_content: The error message/content to check
            http_code: Optional HTTP status code to include in check

        Returns:
            tuple: (decision, matched_pattern) where decision is "yes", "no", or "none"
        """
        # Check for global config files
        config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser(
            "~/.config"
        )
        retry_no_path = Path(config_home) / "aicoder" / "retry_no.conf"
        retry_yes_path = Path(config_home) / "aicoder" / "retry_yes.conf"

        # Combine error content with HTTP code for matching
        full_error_text = error_content
        if http_code is not None:
            full_error_text = f"HTTP {http_code}: {error_content}"

        # Check if retry patterns are disabled (for testing)
        if os.environ.get("DISABLE_RETRY_PATTERNS", "0") == "1":
            return "none", ""

        # FIRST: Check retry_no.conf (highest precedence)
        if retry_no_path.exists():
            try:
                with open(retry_no_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith("#"):
                            try:
                                # Use cached compiled regex if available
                                if line not in self._regex_cache:
                                    self._regex_cache[line] = re.compile(
                                        line, re.IGNORECASE
                                    )

                                if self._regex_cache[line].search(full_error_text):
                                    return "no", line
                            except re.error as e:
                                emsg(
                                    f"Warning: Invalid regex pattern in retry_no.conf line {line_num}: '{line}' - {e}"
                                )

            except Exception as e:
                emsg(f"Warning: Failed to read retry_no.conf: {e}")

        # SECOND: Check retry_yes.conf
        if retry_yes_path.exists():
            try:
                with open(retry_yes_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith("#"):
                            try:
                                # Use cached compiled regex if available
                                if line not in self._regex_cache:
                                    self._regex_cache[line] = re.compile(
                                        line, re.IGNORECASE
                                    )

                                if self._regex_cache[line].search(full_error_text):
                                    return "yes", line
                            except re.error as e:
                                emsg(
                                    f"Warning: Invalid regex pattern in retry_yes.conf line {line_num}: '{line}' - {e}"
                                )

            except Exception as e:
                emsg(f"Warning: Failed to read retry_yes.conf: {e}")

        # THIRD: No patterns matched
        return "none", ""

    def _calculate_retry_delay(self) -> float:
        """
        Calculate retry delay with exponential backoff.
        Uses exponential backoff: 2, 4, 8, 16, 32, 64 (capped at 64)



        Returns:
            float: Calculated delay in seconds
        """
        # Always use exponential backoff starting from 2 seconds
        delay = min(2.0 * (2**self.retry_attempt_count), 64.0)
        return delay

    def should_retry_error(
        self, e: urllib.error.HTTPError, error_content: str = None
    ) -> tuple[bool, int, str]:
        """
        Determine if an HTTP error should be retried.

        Logic:
        1. If matches retry_no.conf → NEVER retry
        2. If matches retry_yes.conf → ALWAYS retry
        3. Otherwise use default retry logic

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

        # FIRST: Check retry_yes.conf and retry_no.conf patterns
        decision, matched_pattern = self._check_retry_patterns(error_content, e.code)

        if decision == "no":
            # retry_no.conf matched - NEVER retry
            return False, 0, f"retry_no.conf pattern: {matched_pattern}"
        elif decision == "yes":
            # retry_yes.conf matched - ALWAYS retry
            retry_sleep_secs = self._calculate_retry_delay()
            return True, retry_sleep_secs, f"retry_yes.conf pattern: {matched_pattern}"

        # SECOND: Fall back to default retry logic
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

            # Calculate the actual retry delay using exponential backoff or fixed delay
            retry_sleep_secs = self._calculate_retry_delay()
            return should_retry, retry_sleep_secs, error_type

        # Special handling for 500 errors - only retry if they contain rate limiting information
        elif e.code == 500:
            # Special case: 500 error that contains "429 Too Many Requests" in the content
            if "429 Too Many Requests" in error_content:
                should_retry = True
                error_type = "Rate limiting"
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
            else:
                # 500 errors without rate limiting indicators should not be retried
                should_retry = False

            if should_retry:
                # Calculate the actual retry delay using exponential backoff or fixed delay
                retry_sleep_secs = self._calculate_retry_delay()
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
            emsg(f"\nAPI Error: {e.code} {e.reason}\n{error_content}")
        except Exception:
            emsg(f"\nAPI Error: {e.code} {e.reason}")

        should_retry, retry_sleep_secs, error_type = self.should_retry_error(
            e, error_content
        )

        if should_retry:
            # Check if we've exceeded maximum retry attempts (if configured)
            if (
                config.RETRY_MAX_ATTEMPTS > 0
                and self.retry_attempt_count >= config.RETRY_MAX_ATTEMPTS
            ):
                emsg(
                    f"    --- Maximum retry attempts ({config.RETRY_MAX_ATTEMPTS}) exceeded. Giving up."
                )
                return False  # Don't retry, max attempts reached

            APIErrors.print(
                APIErrors.RETRY_ERROR,
                error_type=error_type,
                retry_sleep_secs=retry_sleep_secs,
            )
            # Increment retry attempt counter for exponential backoff
            self.retry_attempt_count += 1
            # Use cancellable sleep to allow user to cancel retries
            if not cancellable_sleep(retry_sleep_secs, self.animator):
                self.animator.stop_animation()
                emsg("\nRetry cancelled by user (ESC).")
                return False  # Don't retry, user cancelled
            return True  # Retry the request
        elif e.code == 401:
            # 401 - Unauthorized (likely expired token)
            emsg("Authentication failed. Please check your API key/token.")
            wmsg("If using OAuth, you may need to refresh your token.")
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
        emsg(f"\nConnection Error: {str(e.reason) if hasattr(e, 'reason') else str(e)}")
        wmsg("This may be due to network issues or an expired authentication token.")
        wmsg("Please check your connection and authentication credentials.")

    def handle_connection_drop_error(self, error_message: str) -> bool:
        """
        Handle connection drop errors with retry logic.

        Args:
            error_message: The error message from the connection drop

        Returns:
            bool: True if the request should be retried, False if it should not
        """
        if self.stats:
            self.stats.api_errors += 1

        # FIRST: Check retry_yes.conf and retry_no.conf patterns
        decision, matched_pattern = self._check_retry_patterns(error_message)

        if decision == "no":
            # retry_no.conf matched - NEVER retry
            return False
        elif decision == "yes":
            # retry_yes.conf matched - ALWAYS retry
            error_type = f"retry_yes.conf pattern: {matched_pattern}"
        else:
            # SECOND: Fall back to default connection drop indicators
            should_retry = any(
                keyword in error_message.lower()
                for keyword in [
                    "connection dropped by server",
                    "eof detected",
                    "connection reset",
                    "broken pipe",
                    "server closed the connection",
                    "connection unexpectedly",
                ]
            )

            if not should_retry:
                return False  # Don't retry other errors

            error_type = "Connection dropped"

        # Calculate the actual retry delay using exponential backoff or fixed delay
        retry_sleep_secs = self._calculate_retry_delay()

        # Check if we've exceeded maximum retry attempts (if configured)
        if (
            config.RETRY_MAX_ATTEMPTS > 0
            and self.retry_attempt_count >= config.RETRY_MAX_ATTEMPTS
        ):
            emsg(
                f"    --- Maximum retry attempts ({config.RETRY_MAX_ATTEMPTS}) exceeded. Giving up."
            )
            return False  # Don't retry, max attempts reached

        APIErrors.print(
            APIErrors.RETRY_ERROR_WITH_CANCEL,
            error_type=error_type,
            retry_sleep_secs=retry_sleep_secs,
        )
        # Increment retry attempt counter for exponential backoff
        self.retry_attempt_count += 1
        # Use cancellable sleep to allow user to cancel retries
        if not cancellable_sleep(retry_sleep_secs, self.animator):
            self.animator.stop_animation()
            emsg("\nRetry cancelled by user (ESC).")
            return False  # Don't retry, user cancelled
        return True  # Retry the request


def format_connection_error(
    code: int,
    reason: str,
    body: str,
    will_retry: bool,
    pattern_info: str = None,
    delay: float = None,
) -> str:
    """THE single place to format all HTTP error messages.

    Args:
        code: HTTP status code
        reason: HTTP reason phrase
        body: Response body content
        will_retry: Whether the request will be retried
        pattern_info: Which pattern matched (e.g., "retry_yes.conf: rate limit")
        delay: Retry delay in seconds (if will_retry is True)

    Returns:
        Formatted error message string
    """
    # Get body truncation length from environment or use default
    truncate_length = int(os.environ.get("ERROR_BODY_TRUNCATE_LENGTH", "500"))

    # Truncate body if too long
    if len(body) > truncate_length:
        body = body[:truncate_length] + "... (truncated)"

    # Build the error message
    error_msg = f"\nCONNECTION ERROR:\nHTTP {code}: {reason}"

    if body.strip():
        error_msg += f"\n{body}"

    if will_retry:
        retry_info = "Will retry"
        if pattern_info:
            retry_info += f' (matched "{pattern_info}")'
        if delay:
            timestamp = datetime.now().strftime("%H:%M:%S")
            retry_info += f"... waiting {int(delay)} seconds... {timestamp}"
        error_msg += f"\n{retry_info}"
    else:
        retry_info = "Will not retry"
        if pattern_info:
            retry_info += f' (matched "{pattern_info}")'
        error_msg += f"\n{retry_info}"

    return error_msg


def handle_request_error(exception):
    """
    THE single place for ALL request error detection and handling.
    Throws ShouldRetryException if retry should be done, does nothing if no retry.
    """
    # Use singleton pattern
    from .animator import get_animator
    from .stats import get_stats

    animator = get_animator()
    stats = get_stats()

    retry_handler = APIRetryHandler(animator, stats)

    # Convert exception to text
    if isinstance(exception, urllib.error.HTTPError):
        error_text = f"HTTP {exception.code}: {exception.reason}"
        try:
            body = exception.read().decode()
            if body.strip():
                error_text += f"\n{body}"
        except Exception:
            pass

        # Check patterns
        decision, pattern = retry_handler._check_retry_patterns(body, exception.code)
        match_text = body

    elif isinstance(exception, urllib.error.URLError):
        error_text = (
            str(exception.reason) if hasattr(exception, "reason") else str(exception)
        )
        decision, pattern = retry_handler._check_retry_patterns(error_text)
        match_text = error_text
        body = ""  # Ensure body is defined for consistency

    else:
        # Handle all other exception types (including ConnectionDroppedException)
        error_text = str(exception)
        decision, pattern = retry_handler._check_retry_patterns(error_text)
        match_text = error_text
        body = ""  # Ensure body is defined for consistency

    # Check for ESC cancellation before proceeding
    from .terminal_manager import is_esc_pressed

    if is_esc_pressed():
        emsg("\nRequest cancelled by user (ESC).")
        return False

    # Debug
    if os.environ.get("AICODER_REGEX_DEBUG", "0") == "1":
        print(f'🔍 Regex matching text: "{match_text}"')
        print(f"🔍 Decision: {decision}, Pattern: {pattern}")

    # Never retry
    if decision == "no":
        emsg(
            f'\nCONNECTION ERROR:\n{error_text}\nWill not retry (matched "retry_no.conf: {pattern}")'
        )
        return False

    # Should retry
    if decision == "yes" or (
        isinstance(exception, urllib.error.HTTPError)
        and retry_handler.should_retry_error(exception, body)[0]
    ):
        delay = retry_handler._calculate_retry_delay()
        pattern_info = (
            f"retry_yes.conf: {pattern}" if decision == "yes" else "default: retryable"
        )

        if isinstance(exception, urllib.error.HTTPError):
            emsg(
                format_connection_error(
                    exception.code, exception.reason, body, True, pattern_info, delay
                )
            )
        else:
            timestamp = datetime.now().strftime("%H:%M:%S")
            emsg(
                f'CONNECTION ERROR:\n{error_text}\nWill retry (matched "{pattern_info}")... waiting {int(delay)} seconds... {timestamp}'
            )

        retry_handler.retry_attempt_count += 1
        if cancellable_sleep(delay, animator):
            raise ShouldRetryException(exception)
        else:
            emsg("\nRetry cancelled by user (ESC).")
            return False

    # No retry
    emsg(f"\nCONNECTION ERROR:\n{error_text}\nWill not retry")
    return False
