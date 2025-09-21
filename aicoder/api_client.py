"""
API Client for AI Coder - Shared functionality for both streaming and non-streaming requests.
This module provides a base class with common functionality to eliminate code duplication
between streaming and non-streaming API requests.
"""

import json
import time
import select
import termios
import sys
import urllib.request
import urllib.error
import os
from typing import List, Dict, Any

# Handle both relative and absolute imports
try:
    from .config import (
        DEBUG,
        RED,
        YELLOW,
        RESET,
        API_MODEL,
        API_ENDPOINT,
        API_KEY,
        TEMPERATURE,
        TOP_P,
        MAX_TOKENS,
    )
    from .retry_utils import APIRetryHandler
except ImportError:
    # Fallback for testing or when running as main module
    try:
        from config import (
            DEBUG,
            RED,
            YELLOW,
            RESET,
            API_MODEL,
            API_ENDPOINT,
            API_KEY,
            TEMPERATURE,
            TOP_P,
            MAX_TOKENS,
        )
        import retry_utils

        APIRetryHandler = retry_utils.APIRetryHandler
    except ImportError:
        # Mock for testing
        import sys
        import types

        # Create mock config
        mock_config = types.ModuleType("config")
        mock_config.DEBUG = False
        mock_config.RED = RED
        mock_config.YELLOW = YELLOW
        mock_config.RESET = RESET
        mock_config.API_MODEL = "test-model"
        mock_config.API_ENDPOINT = "https://api.test.com/v1/chat/completions"
        mock_config.API_KEY = "test-key"
        mock_config.TEMPERATURE = 0.7
        mock_config.TOP_P = 1.0
        mock_config.MAX_TOKENS = None
        sys.modules["config"] = mock_config

        # Create mock retry_utils
        mock_retry_utils = types.ModuleType("retry_utils")

        class MockAPIRetryHandler:
            def __init__(self, animator, stats=None):
                pass

        mock_retry_utils.APIRetryHandler = MockAPIRetryHandler
        sys.modules["retry_utils"] = mock_retry_utils

        # Assign to globals
        DEBUG = mock_config.DEBUG
        RED = mock_config.RED
        YELLOW = mock_config.YELLOW
        RESET = mock_config.RESET
        API_MODEL = mock_config.API_MODEL
        API_ENDPOINT = mock_config.API_ENDPOINT
        API_KEY = mock_config.API_KEY
        TEMPERATURE = mock_config.TEMPERATURE
        TOP_P = mock_config.TOP_P
        MAX_TOKENS = mock_config.MAX_TOKENS
        APIRetryHandler = MockAPIRetryHandler


class APIClient:
    """Base API client with shared functionality for both streaming and non-streaming requests."""

    def __init__(self, animator=None, stats=None):
        self.animator = animator
        self.stats = stats
        self.retry_handler = APIRetryHandler(animator, stats)

    def _prepare_api_request_data(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        disable_tools: bool = False,
        tool_manager=None,
    ) -> Dict[str, Any]:
        """Prepare the API request data with common parameters."""
        api_data = {
            "model": API_MODEL,
            "messages": messages,
        }

        # Add streaming parameters if enabled
        if stream:
            api_data["stream"] = True
            api_data["stream_options"] = {"include_usage": True}

        # Temperature settings
        if "TEMPERATURE" in os.environ:
            api_data["temperature"] = TEMPERATURE

        # Top-p settings
        if "TOP_P" in os.environ and TOP_P != 1.0:
            api_data["top_p"] = TOP_P

        # Max tokens
        if MAX_TOKENS is not None:
            api_data["max_tokens"] = MAX_TOKENS

        # Tool settings
        if not disable_tools and tool_manager:
            # Check if this is a summary request (don't include tools for summaries)
            is_summary_request = any(
                m.get("role") == "system" and "summary" in m.get("content", "").lower()
                for m in messages
            )

            if not is_summary_request:
                api_data["tools"] = tool_manager.get_tool_definitions()
                api_data["tool_choice"] = "auto"

        return api_data

    def _validate_tool_definitions(self, api_data: Dict[str, Any]):
        """Validate that all tool calls have properly formatted arguments."""
        if "tools" in api_data:
            for tool_def in api_data["tools"]:
                if "function" in tool_def and "parameters" in tool_def["function"]:
                    # Ensure parameters is a valid JSON object
                    try:
                        json.dumps(tool_def["function"]["parameters"])
                    except Exception as e:
                        print(
                            f"{RED} * Error: Malformed tool definition parameters: {e}{RESET}"
                        )
                        # Fix the parameters by providing a default valid structure
                        tool_def["function"]["parameters"] = {
                            "type": "object",
                            "properties": {},
                        }

    def _make_http_request(
        self, api_data: Dict[str, Any], timeout: int = 300
    ) -> Dict[str, Any]:
        """Make the actual HTTP request to the API."""
        request_body = json.dumps(api_data).encode("utf-8")

        req = urllib.request.Request(
            API_ENDPOINT,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
                "User-Agent": os.environ.get("HTTP_USER_AGENT", "Mozilla/5.0"),
                "Referrer": "localhost",
                "HTTP-Referer": "https://github.com/elblah/dt-aicoder",
                "X-Title": "dt-aicoder",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _handle_user_cancellation(self) -> bool:
        """Check for user cancellation (ESC key press). Returns True if cancelled."""
        try:
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                key = sys.stdin.read(1)
                # Check for ESC key (ASCII 27)
                if ord(key) == 27:
                    return True
        except IOError:
            # No input available
            pass
        return False

    def _setup_terminal_for_input(self):
        """Set up terminal for non-blocking input reading."""
        return termios.tcgetattr(sys.stdin)

    def _restore_terminal(self, old_settings):
        """Restore terminal settings."""
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except Exception:
            # If we can't restore terminal settings, that's okay
            pass

    def _update_stats_on_success(self, api_start_time: float, response: Dict[str, Any]):
        """Update statistics on successful API call."""
        if self.stats:
            self.stats.api_success += 1
            # Record time spent on API call
            self.stats.api_time_spent += time.time() - api_start_time

            # Extract token usage information from the response
            if "usage" in response:
                usage = response["usage"]
                # Extract prompt tokens (input) and completion tokens (output)
                if "prompt_tokens" in usage:
                    # Track current prompt size for auto-compaction decisions
                    self.stats.current_prompt_size = usage["prompt_tokens"]
                    # Accumulate prompt tokens for session statistics
                    self.stats.prompt_tokens += usage["prompt_tokens"]
                if "completion_tokens" in usage:
                    # Accumulate completion tokens for session statistics
                    self.stats.completion_tokens += usage["completion_tokens"]

        # Reset retry counter on successful API call
        self.retry_handler.reset_retry_counter()

    def _update_stats_on_failure(self, api_start_time: float):
        """Update statistics on failed API call."""
        if self.stats:
            # Record time spent even on failed API calls
            self.stats.api_time_spent += time.time() - api_start_time

    def _handle_http_error(self, e: urllib.error.HTTPError) -> bool:
        """Handle HTTP errors with retry logic. Returns True if should retry."""
        if isinstance(e, urllib.error.HTTPError):
            return self.retry_handler.handle_http_error_with_retry(e)
        return False

    def _handle_connection_error(self, e: urllib.error.URLError):
        """Handle connection errors."""
        if isinstance(e, urllib.error.URLError):
            self.retry_handler.handle_connection_error(e)
