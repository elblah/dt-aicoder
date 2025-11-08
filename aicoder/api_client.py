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

_tools_definitions_token_est_cache = {}
_messages_token_est_cache = {}


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
            "model": config.get_api_model(),
            "messages": messages,
        }

        # Add streaming parameters if enabled
        if stream:
            api_data["stream"] = True
            api_data["stream_options"] = {"include_usage": True}

        # Temperature settings
        if "TEMPERATURE" in os.environ or "PLAN_TEMPERATURE" in os.environ:
            api_data["temperature"] = config.get_temperature()

        # Top-p settings
        if (
            "TOP_P" in os.environ or "PLAN_TOP_P" in os.environ
        ) and config.get_top_p() != 1.0:
            api_data["top_p"] = config.get_top_p()

        # Top-k settings
        if (
            "TOP_K" in os.environ or "PLAN_TOP_K" in os.environ
        ) and config.get_top_k() != 0:
            api_data["top_k"] = config.get_top_k()

        # Repetition penalty settings
        if (
            "REPETITION_PENALTY" in os.environ
            or "PLAN_REPETITION_PENALTY" in os.environ
        ) and config.get_repetition_penalty() != 1.0:
            api_data["repetition_penalty"] = config.get_repetition_penalty()

        # Max tokens
        if config.get_max_tokens() is not None:
            api_data["max_tokens"] = config.get_max_tokens()

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
        # Use centralized request preparation with caching
        request_body = self._prepare_and_cache_request(api_data)

        api_key = config.get_api_key()
        api_endpoint = config.get_api_endpoint()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": os.environ.get("HTTP_USER_AGENT", "Mozilla/5.0"),
            "Referrer": "localhost",
        }

        if "openrouter.ai" in api_endpoint:
            headers["HTTP-Referer"] = "https://github.com/elblah/dt-aicoder"
            headers["X-Title"] = "dt-aicoder"

        req = urllib.request.Request(
            api_endpoint,
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
        if not self.stats:
            return

        self.stats.api_success += 1
        # Record time spent on API call
        self.stats.api_time_spent += time.time() - api_start_time

        # Check if we should force token estimation instead of using API usage data
        import aicoder.config as config

        if not config.TRUST_USAGE_INFO_PROMPT_TOKENS:
            # Always use fallback estimation when not trusting usage data
            self._process_token_fallback(response)
            return

        # Use API usage data if available and not forced to estimate
        if "usage" not in response or not response["usage"]:
            # No usage data at all - use fallback
            self._process_token_fallback(response)
            return

        usage = response["usage"]

        # Track usage information for future cost calculations
        self.stats.usage_infos.append({"time": time.time(), "usage": usage})

        # Check if usage data seems reasonable
        prompt_tokens = usage.get("prompt_tokens", 0)
        if prompt_tokens > 0:
            # Good usage data - use it
            self.stats.current_prompt_size = prompt_tokens
            self.stats.current_prompt_size_estimated = False
            self.stats.prompt_tokens += prompt_tokens
        else:
            # Bad or zero usage data - use fallback
            self._process_token_fallback(response)

        if "completion_tokens" in usage:
            completion_tokens = usage.get("completion_tokens", 0)
            self.stats.completion_tokens += completion_tokens

    def _process_token_fallback(self, response: Dict[str, Any]):
        """Handle token estimation fallback logic."""
        estimated_input_tokens = 0
        estimated_output_tokens = 0

        # Use the cached accurate value from the actual request
        from .utils import estimate_tokens_from_last_api_request

        cached_estimate = estimate_tokens_from_last_api_request()

        # Always re-estimate total context size using message history
        if hasattr(self, "message_history") and self.message_history:
            self.message_history.estimate_context()
            estimated_input_tokens = self.message_history.stats.current_prompt_size
        else:
            # Fallback to cached value only
            if cached_estimate is not None:
                estimated_input_tokens = cached_estimate
            else:
                estimated_input_tokens = 0

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
            self.stats.current_prompt_size_estimated = True

        # Reset retry counter on successful API call
        self.retry_handler.reset_retry_counter()

    def _estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in a text string using utility function."""
        from .utils import estimate_tokens

        return estimate_tokens(text)

    def _estimate_tools_definitions_tokens(self, api_data):
        """
        Estimate the tools definitions tokens and cache it
        """
        if "tools" not in api_data:
            return 0

        from .utils import estimate_tokens, cache_tools_definitions_tokens_estimation

        tools_definitions = api_data["tools"]
        tools_definitions_json = json.dumps(tools_definitions, separators=(",", ":"))

        hash_tdef = hash(tools_definitions_json)
        if hash_tdef in _tools_definitions_token_est_cache:
            tokens_estimation = _tools_definitions_token_est_cache[hash_tdef]
        else:
            tokens_estimation = estimate_tokens(tools_definitions_json)
            _tools_definitions_token_est_cache[hash_tdef] = tokens_estimation

        cache_tools_definitions_tokens_estimation(tokens_estimation)

        return tokens_estimation

    def _estimate_messages_tokens_light(self, api_data):
        """
        Estimate messages tokens
        """
        if "messages" not in api_data:
            return 0

        from .utils import estimate_tokens

        stoken = 0
        for msg in api_data["messages"]:
            id_msg = id(msg)
            if id_msg in _messages_token_est_cache:
                stoken += _messages_token_est_cache[id_msg]
            else:
                msg_json = json.dumps(msg, separators=(",", ":"))
                msg_estimation = estimate_tokens(msg_json)
                _messages_token_est_cache[id_msg] = msg_estimation
                stoken += msg_estimation
        return stoken

    def _prepare_and_cache_request(self, api_data: Dict[str, Any]) -> bytes:
        """
        Centralized function to prepare API request for sending.
        - Caches request string for accurate token estimation
        - Returns encoded request body ready for HTTP request

        All API request types should use this function for consistency.
        """
        from .utils import cache_api_request_for_estimation

        tokens_tools_defs = self._estimate_tools_definitions_tokens(api_data)
        messages_tokens = self._estimate_messages_tokens_light(api_data)
        estimated_tokens = messages_tokens + tokens_tools_defs
        cache_api_request_for_estimation(estimated_tokens)

        request_string = json.dumps(api_data, separators=(",", ":"))

        return request_string.encode("utf-8")

    def _estimate_messages_tokens(self, messages: List[Dict]) -> int:
        """Estimate total tokens for a list of messages using utility function."""
        from .utils import estimate_messages_tokens

        return estimate_messages_tokens(messages)

    def _update_stats_on_failure(self, api_start_time: float):
        """Update statistics on failed API call."""
        if self.stats:
            # Record time spent even on failed API calls
            self.stats.api_time_spent += time.time() - api_start_time
            # Increment error counter
            self.stats.api_errors += 1
            # Preserve context size estimation - don't reset it on failures
            # The context size should persist across reconnections to maintain
            # proper session state and auto-compaction behavior
