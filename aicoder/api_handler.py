"""
API request handling for AI Coder.
"""

import json
import time
import urllib.request
import urllib.error
import threading
from .terminal_manager import is_esc_pressed
from typing import List, Dict, Any

from . import config
from .utils import emsg
from .streaming_adapter import StreamingAdapter
from .api_client import APIClient


class APIHandlerMixin(APIClient):
    """Mixin class for API request handling."""

    def __init__(self):
        super().__init__(getattr(self, "animator", None), getattr(self, "stats", None))

    def _make_api_request(
        self,
        messages: List[Dict[str, Any]],
        disable_streaming_mode: bool = False,
        disable_tools: bool = False,
    ):
        """Sends a request to the OpenAI-compatible API.

        Args:
            messages: List of message dictionaries to send to the API
            disable_streaming_mode: If True, disables streaming mode (used for internal prompts
                                  that don't benefit from streaming, like summaries and autopilot decisions)
            disable_tools: If True, excludes tools from the request (used for decisions and summaries)
        """
        # Use streaming adapter if enabled and not disabled for this request
        if config.ENABLE_STREAMING and not disable_streaming_mode:
            # Initialize streaming adapter if not already done
            if not hasattr(self, "_streaming_adapter"):
                self._streaming_adapter = StreamingAdapter(
                    self, getattr(self, "animator", None)
                )
            return self._streaming_adapter.make_request(
                messages, disable_streaming_mode, disable_tools
            )

        # Original implementation for non-streaming
        # Update stats
        self.stats.api_requests += 1

        # Prepare API request data using shared functionality
        api_data = self._prepare_api_request_data(
            messages,
            stream=False,
            disable_tools=disable_tools,
            tool_manager=getattr(self, "tool_manager", None),
        )

        self.animator.start_animation("Working...")

        # Track API call time
        api_start_time = time.time()

        while True:
            try:
                # Check for user cancellation during animation
                if self.animator.check_user_cancel():
                    self.animator.stop_animation()
                    emsg(f"\nRequest cancelled by user.")
                    raise Exception("REQUEST_CANCELLED_BY_USER")

                # Validate tool definitions using shared functionality
                self._validate_tool_definitions(api_data)
                request_body = json.dumps(api_data).encode("utf-8")
            except TypeError as e:
                self.animator.stop_animation()
                emsg(f"\nError serializing data for API request: {e}")
                return None
            except Exception as e:
                if str(e) == "REQUEST_CANCELLED_BY_USER":
                    # Record time spent even on cancelled API calls
                    self._update_stats_on_failure(api_start_time)
                    return None
                self.animator.stop_animation()
                raise

            if config.DEBUG:
                if not disable_streaming_mode:
                    print(f"DEBUG: data length = {len(request_body)}")
                    try:
                        debug_data = json.loads(request_body.decode("utf-8"))
                        print(
                            f"DEBUG: API request data: {json.dumps(debug_data, indent=2)}"
                        )
                    except Exception as e:
                        print(f"DEBUG: Could not decode request body for debug: {e}")

            # Threading approach for API request with ESC cancellation support
            def api_request_worker(result_dict, stop_event):
                """Worker function to make the API request in a separate thread."""
                try:
                    # Validate JSON before sending
                    try:
                        json.loads(request_body.decode("utf-8"))
                    except json.JSONDecodeError as je:
                        raise ValueError(f"Invalid JSON in request body: {je}")

                    response_data = self._make_http_request(api_data, timeout=300)
                    result_dict["response"] = response_data
                    result_dict["success"] = True
                except Exception as e:
                    result_dict["error"] = e
                    result_dict["success"] = False

            # Dictionary to share results between threads
            result_dict = {}

            # Create and start the API request thread
            api_thread = threading.Thread(
                target=api_request_worker, args=(result_dict, None)
            )
            api_thread.daemon = True
            api_thread.start()

            # Monitor for ESC key press while waiting for API response
            try:
                # Wait for the thread to complete or for user cancellation
                while api_thread.is_alive():
                    time.sleep(0.1)  # Small delay to prevent busy-waiting

                    # Check for ESC keypress via centralized manager
                    if is_esc_pressed():
                        self.animator.stop_animation()
                        emsg(f"\nRequest cancelled by user (ESC).")
                        # Note: We can't actually terminate the API request thread,
                        # but we can ignore its result
                        return None

                # Thread has completed, get the result
                self.animator.stop_animation()

                # Wait for thread to finish and get result
                api_thread.join()

                if result_dict.get("success"):
                    self._update_stats_on_success(
                        api_start_time, result_dict["response"]
                    )

                    # Extract token usage information from the response
                    response = result_dict["response"]
                    if config.DEBUG:
                        print(f"DEBUG: API response keys: {list(response.keys())}")
                        if "usage" in response:
                            print(f"DEBUG: Usage data: {response['usage']}")
                        else:
                            print("DEBUG: No 'usage' key in response")
                            # Print the entire response structure to see what's there
                            print(f"DEBUG: Full response keys: {list(response.keys())}")

                    if "usage" in response:
                        usage = response["usage"]
                        # Extract prompt tokens (input) and completion tokens (output)
                        if "prompt_tokens" in usage:
                            self.stats.current_prompt_size = usage["prompt_tokens"]
                            self.stats.prompt_tokens += usage["prompt_tokens"]
                        if "completion_tokens" in usage:
                            self.stats.completion_tokens += usage["completion_tokens"]
                    else:
                        # Fallback: estimate tokens if usage information is not available
                        # This can happen with some API providers that don't include token usage
                        estimated_input_tokens = 0
                        estimated_output_tokens = 0
                        
                        # For input tokens, we need to access the message history
                        if hasattr(self, 'message_history') and self.message_history:
                            from .utils import estimate_messages_tokens
                            estimated_input_tokens = estimate_messages_tokens(self.message_history.messages)
                        
                        # Estimate output tokens from the response content
                        if "choices" in response and len(response["choices"]) > 0:
                            choice = response["choices"][0]
                            if "message" in choice and "content" in choice["message"]:
                                content = choice["message"]["content"]
                                if content:
                                    from .utils import estimate_tokens
                                    estimated_output_tokens = estimate_tokens(content)
                        
                        # Update stats with estimated values
                        self.stats.prompt_tokens += estimated_input_tokens
                        self.stats.completion_tokens += estimated_output_tokens
                        # Update current prompt size for auto-compaction (use estimated input tokens if available)
                        if estimated_input_tokens > 0:
                            self.stats.current_prompt_size = estimated_input_tokens

                    return response
                else:
                    # Record time spent even on failed API calls
                    self._update_stats_on_failure(api_start_time)
                    raise result_dict["error"]

            except Exception as e:
                self.animator.stop_animation()
                if str(e) == "REQUEST_CANCELLED_BY_USER":
                    # Record time spent even on cancelled API calls
                    self._update_stats_on_failure(api_start_time)
                    return None

                # Handle HTTP errors specifically
                if isinstance(e, urllib.error.HTTPError):
                    if self._handle_http_error(e):
                        continue
                    return None
                # Handle connection errors (Broken pipe, etc.)
                elif isinstance(e, urllib.error.URLError):
                    self._handle_connection_error(e)
                    return None
                else:
                    raise

