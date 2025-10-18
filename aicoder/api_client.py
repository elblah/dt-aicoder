"""
API Client for AI Coder - Shared functionality for both streaming and non-streaming requests.
This module provides a base class with common functionality to eliminate code duplication
between streaming and non-streaming API requests.
"""

import json
import time
import urllib.request
import urllib.error
import os
from typing import List, Dict, Any
from . import config
from . import retry_utils
from .terminal_manager import is_esc_pressed


class APIClient:
    """Base API client with shared functionality for both streaming and non-streaming requests."""

    def __init__(self, animator=None, stats=None):
        self.animator = animator
        self.stats = stats
        self.retry_handler = retry_utils.APIRetryHandler(animator, stats)

    def _prepare_api_request_data(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        disable_tools: bool = False,
        tool_manager=None,
    ) -> Dict[str, Any]:
        """Prepare the API request data with common parameters."""
        api_data = {
            "model": config.API_MODEL,
            "messages": messages,
        }

        # Add streaming parameters if enabled
        if stream:
            api_data["stream"] = True
            api_data["stream_options"] = {"include_usage": True}

        # Temperature settings
        if "TEMPERATURE" in os.environ:
            api_data["temperature"] = config.TEMPERATURE

        # Top-p settings
        if "TOP_P" in os.environ and config.TOP_P != 1.0:
            api_data["top_p"] = config.TOP_P

        # Top-k settings
        if "TOP_K" in os.environ and config.TOP_K != 0:
            api_data["top_k"] = config.TOP_K

        # Max tokens
        if config.MAX_TOKENS is not None:
            api_data["max_tokens"] = config.MAX_TOKENS

        # Tool settings
        if not disable_tools and tool_manager:
            api_data["tools"] = tool_manager.get_tool_definitions()

            # Set activeTools based on planning mode
            try:
                from .planning_mode import get_planning_mode

                planning_mode = get_planning_mode()
                if planning_mode.is_plan_mode_active():
                    api_data["activeTools"] = planning_mode.get_active_tools(
                        api_data["tools"]
                    )
            except ImportError:
                pass  # Planning mode not available

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
                            f"{config.RED} * Error: Malformed tool definition parameters: {e}{config.RESET}"
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

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.API_KEY}",
            "User-Agent": os.environ.get("HTTP_USER_AGENT", "Mozilla/5.0"),
            "Referrer": "localhost",
        }

        if "openrouter.ai" in config.API_ENDPOINT:
            headers["HTTP-Referer"] = "https://github.com/elblah/dt-aicoder"
            headers["X-Title"] = "dt-aicoder"

        req = urllib.request.Request(
            config.API_ENDPOINT,
            data=request_body,
            method="POST",
            headers=headers,
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _handle_user_cancellation(self) -> bool:
        """Check for user cancellation (ESC key press). Returns True if cancelled."""
        return is_esc_pressed()

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
            else:
                # Fallback: estimate tokens if usage information is not available
                # This can happen with some API providers that don't include token usage
                estimated_input_tokens = 0
                estimated_output_tokens = 0

                # For input tokens, we need to access the message history
                # We'll check if it's available as an instance attribute
                if hasattr(self, "message_history") and self.message_history:
                    estimated_input_tokens = self._estimate_messages_tokens(
                        self.message_history.messages
                    )
                # If we don't have access to message_history, we can't estimate input tokens

                # Estimate output tokens from the response content
                if "choices" in response and len(response["choices"]) > 0:
                    choice = response["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"]
                        if content:
                            estimated_output_tokens = self._estimate_tokens(content)

                # Update stats with estimated values
                self.stats.prompt_tokens += estimated_input_tokens
                self.stats.completion_tokens += estimated_output_tokens
                # Update current prompt size for auto-compaction (use estimated input tokens if available)
                if estimated_input_tokens > 0:
                    self.stats.current_prompt_size = estimated_input_tokens

        # Reset retry counter on successful API call
        self.retry_handler.reset_retry_counter()

    def _estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in a text string using utility function."""
        from .utils import estimate_tokens

        return estimate_tokens(text)

    def _estimate_messages_tokens(self, messages: List[Dict]) -> int:
        """Estimate total tokens for a list of messages using utility function."""
        from .utils import estimate_messages_tokens

        return estimate_messages_tokens(messages)

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
