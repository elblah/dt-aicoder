"""
Streaming adapter for AI Coder to handle SSE streaming responses.
This module provides a pluggable adapter that can handle both streaming
and regular API responses without breaking existing functionality.
"""

import json
import time
import socket
import urllib.request
import urllib.error
import threading
import os
from typing import List, Dict, Any, Optional

from . import config
from .animator import Animator
from .api_client import APIClient
from .api.errors import APIErrors
from .retry_utils import (
    ConnectionDroppedException,
    ShouldRetryException,
    handle_request_error,
)
from .streaming_colorizer import MarkdownColorizer
from .terminal_manager import is_esc_pressed
from .utils import estimate_messages_tokens, wmsg, emsg, imsg, dmsg


class StreamingAdapter(APIClient):
    """Adapter to handle both streaming and regular API responses."""

    def __init__(self, api_handler, animator: Animator = None):
        super().__init__(animator, getattr(api_handler, "stats", None))
        self.api_handler = api_handler
        self.animator = animator or Animator()
        self.stats = getattr(api_handler, "stats", None)
        # Get the log file path from environment variable
        self.stream_log_file = os.environ.get("STREAM_LOG_FILE", None)
        if self.stream_log_file:
            imsg(f"*** Streaming log enabled: {self.stream_log_file}")

        # Initialize markdown colorizer
        self.colorizer = MarkdownColorizer()

    def _log_stream_data(self, data: str):
        """Log streaming data to file if logging is enabled."""
        if not self.stream_log_file:
            return

        try:
            with open(self.stream_log_file, "a", encoding="utf-8") as f:
                f.write(data + "\n")
        except Exception as e:
            dmsg(f"Error writing to stream log: {e}")

    def _reset_colorization_state(self):
        """Reset markdown colorization state for a new streaming response."""
        self.colorizer.reset_state()

    def _reset_all_streaming_state(self):
        """Reset all streaming-related state."""
        self._reset_colorization_state()

        # Reset print buffers if they exist
        if hasattr(self, "print_buffer"):
            self.print_buffer = ""
        if hasattr(self, "seen_first_printable"):
            self.seen_first_printable = False
        if hasattr(self, "trailing_whitespace_buffer"):
            self.trailing_whitespace_buffer = ""

    def make_request(
        self,
        messages: List[Dict[str, Any]],
        disable_streaming_mode: bool = False,
        disable_tools: bool = False,
    ):
        """
        Make an API request with streaming support.
        Falls back to regular request if streaming fails or is disabled.

        Args:
            messages: List of message dictionaries to send to the API
            disable_streaming_mode: If True, disables streaming mode (used for internal prompts
                                  that don't benefit from streaming, like summaries and autopilot decisions)
            disable_tools: If True, excludes tools from the request (used for decisions and summaries)
        """

        # CRITICAL FIX: Always reset streaming state before each request
        # This prevents state corruption from previous failed requests
        self._reset_all_streaming_state()

        # Disable streaming for internal prompts to avoid interference with application logic
        # and to ensure reliable response handling for programmatic use cases
        if disable_streaming_mode:
            # Call the original non-streaming implementation directly to avoid recursion
            return self._make_non_streaming_request(messages, disable_tools)

        # For regular requests, use streaming
        try:
            return self._streaming_request(messages, disable_streaming_mode)
        except Exception as e:
            dmsg(f"Streaming failed, falling back to regular request: {e}")
            # Fallback to regular request
            return self._make_non_streaming_request(messages)

    def _handle_error_response(self, error, error_type):
        """Handle error responses with early returns for specific types."""
        # Early returns for specific error types
        if error_type == "http_timeout":
            http_timeout = int(os.environ.get("HTTP_TIMEOUT", "300"))
            APIErrors.print(APIErrors.HTTP_TIMEOUT, timeout=http_timeout)
            return None

        if error_type == "connection_error":
            emsg(f"\nConnection error: {error}")
            wmsg("Check your internet connection and API endpoint.")
            return None

        # Default: re-raise for HTTP errors and general errors
        raise error

    def _make_non_streaming_request(
        self, messages: List[Dict[str, Any]], disable_tools: bool = False
    ):
        """Make a non-streaming API request directly."""

        # Update stats if available
        if self.stats:
            self.stats.api_requests += 1

        # Prepare API request data using shared functionality
        api_data = self._prepare_api_request_data(
            messages,
            stream=False,
            disable_tools=disable_tools,
            tool_manager=getattr(self.api_handler, "tool_manager", None),
        )

        self.animator.start_animation("Working...")
        api_start_time = time.time()

        while True:
            try:
                # Validate tool definitions using shared functionality
                self._validate_tool_definitions(api_data)
                request_body = json.dumps(api_data).encode("utf-8")
            except TypeError as e:
                self.animator.stop_animation()
                emsg(f"\nError serializing data for API request: {e}")
                return None
            except Exception:
                self.animator.stop_animation()
                raise

            dmsg(f"data length = {len(request_body)}")

            # Threading approach for API request with ESC cancellation support
            def api_request_worker(result_dict, stop_event):
                """Worker function to make the API request in a separate thread."""
                try:
                    # Get HTTP timeout from environment variable, default to 300 seconds (5 minutes)
                    http_timeout = int(os.environ.get("HTTP_TIMEOUT", "300"))
                    response_data = self._make_http_request(
                        api_data, timeout=http_timeout
                    )
                    result_dict["response"] = response_data
                    result_dict["success"] = True
                except socket.timeout as e:
                    # Handle HTTP timeout specifically with user-friendly message
                    result_dict["error"] = e
                    result_dict["error_type"] = "http_timeout"
                    result_dict["success"] = False
                except urllib.error.HTTPError as e:
                    # Handle HTTP errors specifically (like 502, 500, 429, etc.)
                    # These should be categorized separately so they can go through retry logic
                    result_dict["error"] = e
                    result_dict["error_type"] = "http_error"
                    result_dict["success"] = False
                except urllib.error.URLError as e:
                    # Handle other URL errors (timeouts, connection issues, etc.)
                    if isinstance(e.reason, socket.timeout):
                        result_dict["error"] = e
                        result_dict["error_type"] = "http_timeout"
                    else:
                        result_dict["error"] = e
                        result_dict["error_type"] = "connection_error"
                    result_dict["success"] = False
                except Exception as e:
                    result_dict["error"] = e
                    result_dict["error_type"] = "general_error"
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
                        emsg("\nRequest cancelled by user (ESC).")
                        # Note: We can't actually terminate the API request thread,
                        # but we can ignore its result
                        return None

                # Thread has completed, get the result
                self.animator.stop_animation()
                api_thread.join()

                if result_dict.get("success"):
                    processed_response = result_dict["response"]
                    self._update_stats_on_success(api_start_time, processed_response)

                    # Extract token usage information from the response if not handled by _update_stats_on_success
                    if processed_response and "usage" in processed_response:
                        usage = processed_response["usage"]
                        dmsg(f"Non-streaming usage data: {usage}")
                        # Extract prompt tokens (input) and completion tokens (output)
                        if "prompt_tokens" in usage and self.stats:
                            self.stats.current_prompt_size = usage["prompt_tokens"]
                            self.stats.current_prompt_size_estimated = False
                            self.stats.prompt_tokens += usage["prompt_tokens"]
                        if "completion_tokens" in usage and self.stats:
                            self.stats.completion_tokens += usage["completion_tokens"]

                    return processed_response

                # Record time spent even on failed API calls
                self._update_stats_on_failure(api_start_time)

                # Handle specific error types with user-friendly messages
                error = result_dict.get("error")
                error_type = result_dict.get("error_type", "general_error")
                return self._handle_error_response(error, error_type)

            except Exception as e:
                self.animator.stop_animation()
                dmsg(
                    f"DEBUG: _make_non_streaming_request caught exception: {type(e).__name__}: {e}"
                )
                try:
                    handle_request_error(e)
                    dmsg("DEBUG: handle_request_error returned False, breaking loop")
                    break  # Exit the retry loop when handle_request_error returns False (will not retry)
                except ShouldRetryException:
                    dmsg("DEBUG: ShouldRetryException raised, continuing loop")
                    continue  # Continue the retry loop when ShouldRetryException is raised
                return None
            finally:
                # No cleanup needed - terminal manager handles state
                pass

    def _streaming_request(
        self,
        messages: List[Dict[str, Any]],
        disable_streaming_mode: bool = False,
        disable_tools: bool = False,
    ):
        """Handle streaming API request with SSE."""
        # Update stats if available
        if self.stats:
            self.stats.api_requests += 1

        # Prepare API request data using shared functionality
        api_data = self._prepare_api_request_data(
            messages,
            stream=True,
            disable_tools=disable_tools,
            tool_manager=getattr(self.api_handler, "tool_manager", None),
        )

        # Log the request data if logging is enabled
        if self.stream_log_file:
            try:
                self._log_stream_data("=== REQUEST ===")
                self._log_stream_data(json.dumps(api_data, indent=2))
            except Exception as e:
                dmsg(f"Error logging request data: {e}")

        self.animator.start_animation("Working...")
        api_start_time = time.time()

        while True:
            try:
                # Validate tool definitions using shared functionality
                self._validate_tool_definitions(api_data)
                request_body = json.dumps(api_data).encode("utf-8")
            except TypeError as e:
                self.animator.stop_animation()
                emsg(f"\nError serializing data for API request: {e}")
                return None
            except Exception:
                self.animator.stop_animation()
                raise

            if not disable_streaming_mode:
                dmsg(f"data length = {len(request_body)}")

            # Create a generator for streaming response
            def streaming_worker(result_dict, stop_event):
                """Worker function to handle streaming API request."""
                try:
                    api_key = config.get_api_key()
                    api_endpoint = config.get_api_endpoint()

                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                        "User-Agent": "Mozilla/5.0",
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
                    # Get HTTP timeout from environment variable, default to 300 seconds (5 minutes)
                    http_timeout = int(os.environ.get("HTTP_TIMEOUT", "300"))
                    # Use timeout for streaming requests
                    response = urllib.request.urlopen(req, timeout=http_timeout)
                    result_dict["response"] = response
                    result_dict["success"] = True
                except socket.timeout as e:
                    # Handle HTTP timeout specifically with user-friendly message
                    result_dict["error"] = e
                    result_dict["error_type"] = "http_timeout"
                    result_dict["success"] = False
                except urllib.error.HTTPError as e:
                    # Handle HTTP errors specifically (like 502, 500, 429, etc.)
                    # These should be categorized separately so they can go through retry logic
                    result_dict["error"] = e
                    result_dict["error_type"] = "http_error"
                    result_dict["success"] = False
                except urllib.error.URLError as e:
                    # Handle other URL errors (timeouts, connection issues, etc.)
                    if isinstance(e.reason, socket.timeout):
                        result_dict["error"] = e
                        result_dict["error_type"] = "http_timeout"
                    else:
                        result_dict["error"] = e
                        result_dict["error_type"] = "connection_error"
                    result_dict["success"] = False
                except Exception as e:
                    result_dict["error"] = e
                    result_dict["error_type"] = "general_error"
                    result_dict["success"] = False

            # Dictionary to share results between threads
            result_dict = {}

            # Create and start the API request thread
            api_thread = threading.Thread(
                target=streaming_worker, args=(result_dict, None)
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
                        emsg("\nRequest cancelled by user (ESC).")
                        # Note: We can't actually terminate the API request thread,
                        # but we can ignore its result
                        return None

                # Thread has completed, get the result
                self.animator.stop_animation()
                api_thread.join()

                if result_dict.get("success"):
                    response = result_dict["response"]

                    # Process the streaming response in a separate thread to allow ESC monitoring
                    streaming_result = {}
                    streaming_error = None
                    streaming_completed = threading.Event()

                    # Create a flag to signal cancellation
                    cancellation_event = threading.Event()

                    def streaming_worker():
                        nonlocal streaming_result, streaming_error
                        try:
                            # Pass the cancellation event to the streaming method if possible
                            # We'll modify _process_streaming_response to be interruptible
                            streaming_result["response"] = (
                                self._process_streaming_response(
                                    response, cancellation_event
                                )
                            )
                        except ShouldRetryException as e:
                            streaming_error = e
                        except Exception as e:
                            streaming_error = e
                        finally:
                            streaming_completed.set()

                    streaming_thread = threading.Thread(
                        target=streaming_worker, daemon=True
                    )
                    streaming_thread.start()

                    # Monitor for ESC key press while streaming is processing
                    esc_pressed = False
                    while not streaming_completed.is_set():
                        time.sleep(0.1)  # Small delay to prevent busy-waiting

                        # Check for ESC keypress via centralized manager
                        if is_esc_pressed():
                            emsg("\nRequest cancelled by user (ESC).")

                            # Signal cancellation
                            cancellation_event.set()

                            # Don't wait for the streaming thread to complete
                            # Let it run in background and return immediately
                            esc_pressed = True
                            break

                    if esc_pressed:
                        # Return immediately without waiting for streaming thread
                        return None

                    # Wait for streaming thread to complete if it hasn't already
                    streaming_thread.join()

                    # Handle any errors from the streaming thread
                    if streaming_error:
                        raise streaming_error

                    processed_response = streaming_result.get("response")

                    # Update stats using shared functionality
                    self._update_stats_on_success(
                        api_start_time, processed_response or {}
                    )

                    # Extract token usage information from the response
                    if processed_response and "usage" in processed_response:
                        usage = processed_response["usage"]
                        dmsg(f"Streaming usage data: {usage}")
                        # Extract prompt tokens (input) and completion tokens (output)
                        if "prompt_tokens" in usage and self.stats:
                            self.stats.current_prompt_size = usage["prompt_tokens"]
                            self.stats.current_prompt_size_estimated = False
                            self.stats.prompt_tokens += usage["prompt_tokens"]
                        if "completion_tokens" in usage and self.stats:
                            self.stats.completion_tokens += usage["completion_tokens"]
                    else:
                        # Fallback: estimate tokens if usage information is not available
                        # This can happen with some API providers that don't include token usage
                        estimated_input_tokens = 0
                        estimated_output_tokens = 0

                        # For input tokens, we need to access the message history
                        if (
                            hasattr(self.api_handler, "message_history")
                            and self.api_handler.message_history
                        ):
                            estimated_input_tokens = estimate_messages_tokens(
                                self.api_handler.message_history.messages
                            )

                        # Estimate output tokens from the response content
                        if (
                            processed_response
                            and "choices" in processed_response
                            and len(processed_response["choices"]) > 0
                        ):
                            choice = processed_response["choices"][0]
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
                            self.stats.current_prompt_size_estimated = True

                    return processed_response

                # Record time spent even on failed API calls
                self._update_stats_on_failure(api_start_time)

                # Handle specific error types with user-friendly messages
                error = result_dict.get("error")
                error_type = result_dict.get("error_type", "general_error")
                return self._handle_error_response(error, error_type)

            except ShouldRetryException:
                # Direct retry for ShouldRetryException from streaming
                self.animator.stop_animation()
                continue
            except Exception as e:
                self.animator.stop_animation()
                try:
                    handle_request_error(e)
                    break  # Exit the retry loop when handle_request_error returns False (will not retry)
                except ShouldRetryException:
                    continue  # Continue the retry loop when ShouldRetryException is raised
                return None
            finally:
                # No cleanup needed - terminal manager handles state
                pass

    def _process_streaming_response(
        self, response, cancellation_event=None
    ) -> Optional[Dict[str, Any]]:
        """Process streaming response and return final message."""
        # Reset colorization state for new streaming response
        self._reset_colorization_state()

        # Process the streaming response
        full_response = {
            "id": "",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": config.get_api_model(),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "", "tool_calls": []},
                    "finish_reason": None,
                }
            ],
        }

        tool_call_buffers = {}  # Buffer for incomplete tool calls
        content_buffer = ""  # Buffer for content
        first_token_received = False
        usage_info = None  # To store usage information

        # New buffering system for whitespace handling
        self.print_buffer = ""  # Buffer for content to be printed
        self.seen_first_printable = (
            False  # Track if we've seen the first printable character
        )
        self.trailing_whitespace_buffer = ""  # Buffer for potential trailing whitespace

        try:
            # Keep track of time to implement a timeout
            last_data_time = time.time()
            # Get streaming timeout from config
            timeout_seconds = config.STREAMING_TIMEOUT
            # Also get individual read timeout (how long to wait for each line)
            # read_timeout_seconds = config.STREAMING_READ_TIMEOUT

            # Use non-blocking streaming with individual read timeouts
            while True:
                # Check for overall timeout first
                current_time = time.time()
                if current_time - last_data_time > timeout_seconds:
                    APIErrors.print(
                        APIErrors.STREAMING_TIMEOUT, timeout=timeout_seconds
                    )
                    return None

                # Read a line with timeout to prevent hanging on slow/unresponsive servers
                line = None

                # Check for cancellation before attempting to read
                if cancellation_event and cancellation_event.is_set():
                    emsg("\nRequest cancelled by user (ESC).")
                    self.animator.stop_cursor_blinking()
                    return None

                # Non-blocking line read with timeout and cancellation
                timeout_reminder_shown = False
                while line is None:
                    # Check for cancellation during the read attempt
                    if cancellation_event and cancellation_event.is_set():
                        emsg("\nRequest cancelled by user (ESC).")
                        self.animator.stop_cursor_blinking()
                        return None

                    try:
                        # Fallback: read with small timeout
                        line = response.readline()
                        if not line:  # EOF
                            raise ConnectionDroppedException(
                                "Connection dropped by server (EOF detected)"
                            )

                    except Exception as e:
                        handle_request_error(e)
                        self.animator.ensure_cursor_visible()  # Ensure cursor cleanup
                        return None

                    # Check overall timeout during read attempt
                    if time.time() - last_data_time > timeout_seconds:
                        emsg(
                            f"\nStreaming timeout reached ({timeout_seconds} seconds with no SSE data)."
                        )
                        return None

                # If we got here, we have a line to process
                # The connection drop detection above handles EOF cases, so we don't need to check again here

                # Process the line we read
                # Check for timeout - only if no SSE data received in the last X seconds
                current_time = time.time()
                if current_time - last_data_time > timeout_seconds:
                    APIErrors.print(
                        APIErrors.STREAMING_TIMEOUT, timeout=timeout_seconds
                    )
                    return None

                if not first_token_received:
                    # Notify plugins before AI response
                    if hasattr(self.api_handler, "loaded_plugins"):
                        from .plugin_system.loader import (
                            notify_plugins_before_ai_prompt,
                        )

                        notify_plugins_before_ai_prompt(self.api_handler.loaded_plugins)

                    # Display token information before AI response if enabled
                    if config.ENABLE_TOKEN_INFO_DISPLAY and hasattr(self, "stats"):
                        from .utils import display_token_info

                        display_token_info(self.stats, config.AUTO_COMPACT_THRESHOLD)
                        print()  # Add newline after token info

                    first_token_received = True
                    self.animator.stop_animation()
                    self.animator.start_cursor_blinking()
                    # Add [PLAN] prefix if planning mode is active
                    from .planning_mode import get_planning_mode

                    planning_mode = get_planning_mode()
                    plan_prefix = (
                        "[PLAN] " if planning_mode.is_plan_mode_active() else ""
                    )
                    print(
                        f"{config.RESET}{config.BOLD}{config.GREEN}{plan_prefix}AI:{config.RESET} ",
                        end="",
                        flush=True,
                    )

                # Check for user cancellation during streaming (more frequently)
                if (cancellation_event and cancellation_event.is_set()) or (
                    not cancellation_event
                    and self._check_user_cancel_during_streaming()
                ):
                    # emsg("\nStreaming cancelled by user.")
                    self.animator.stop_cursor_blinking()
                    return None

                # Update last data time
                last_data_time = time.time()

                line = line.decode("utf-8").strip()

                # If we successfully read data and timeout reminder was shown, clear it
                if timeout_reminder_shown:
                    # Clear timeout reminder messages
                    print(f"\r{' ' * 80}", end="", flush=True)  # Clear current line
                    print(f"\r{' ' * 80}", end="", flush=True)  # Clear reminder lines
                    timeout_reminder_shown = False

                # Skip lines that are not SSE data
                if not line.startswith("data:"):
                    continue

                if line.startswith("data:"):
                    data_str = line[5:]  # Remove "data:" prefix

                    # Log the raw SSE data if logging is enabled
                    self._log_stream_data(data_str)

                    # End of stream
                    if data_str == "[DONE]":
                        self._flush_print_buffers()
                        break

                    try:
                        data = json.loads(data_str)

                        # Extract response ID
                        if "id" in data:
                            full_response["id"] = data["id"]

                        # Process usage information if present
                        if "usage" in data:
                            usage_info = data["usage"]

                        # Process choices
                        current_finish_reason = None
                        if "choices" in data and len(data["choices"]) > 0:
                            choice = data["choices"][0]

                            # Process content
                            content = ""
                            if "delta" in choice and "content" in choice["delta"]:
                                content = choice["delta"]["content"]
                            
                            # If content is empty, try reasoning (fallback for providers like Minimax)
                            if not content and "delta" in choice and "reasoning" in choice["delta"]:
                                content = choice["delta"]["reasoning"]
                            
                            if content:
                                # Handle non-string content (API compatibility issue)
                                if not isinstance(content, str):
                                    # Ignore non string deltas, sometimes thinking comes as list
                                    continue
                                else:
                                    content_buffer += content
                                    # Use new buffering system to handle whitespace
                                    self._buffer_and_print_content(content)

                            # Process tool calls - handle null or missing tool_calls gracefully
                            if "delta" in choice and "tool_calls" in choice["delta"]:
                                tool_calls = choice["delta"]["tool_calls"]
                                # Handle the case where tool_calls is null (DeepSeek issue)
                                if tool_calls is None:
                                    dmsg(
                                        "Received null tool_calls from API, treating as empty array"
                                    )
                                    tool_calls = []
                                # Ensure tool_calls is iterable
                                if not isinstance(tool_calls, list):
                                    dmsg(
                                        f"tool_calls is not a list ({type(tool_calls)}), treating as empty array"
                                    )
                                    tool_calls = []

                                for tool_call in tool_calls:
                                    self._process_streaming_tool_call(
                                        tool_call, tool_call_buffers
                                    )

                            # Process finish reason
                            if "finish_reason" in choice and choice["finish_reason"]:
                                full_response["choices"][0]["finish_reason"] = choice[
                                    "finish_reason"
                                ]
                                current_finish_reason = choice["finish_reason"]
                                # Check if this is a final completion (stop, length, etc.)
                                # Some providers close the connection after sending finish_reason
                                # instead of sending a [DONE] message. We should recognize this as normal completion.
                                if choice["finish_reason"] in [
                                    "stop",
                                    "length",
                                    "content_filter",
                                    "function_call",
                                    "tool_calls",
                                ]:
                                    # Mark that we've received a completion signal
                                    # We'll break after processing this chunk
                                    full_response["choices"][0][
                                        "_completion_received"
                                    ] = True

                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue

                    # Check if we received a completion signal (for providers that don't send [DONE])
                    if full_response["choices"][0].get(
                        "_completion_received"
                    ) and current_finish_reason in [
                        "stop",
                        "length",
                        "content_filter",
                        "function_call",
                        "tool_calls",
                    ]:
                        # Some providers close the connection after sending finish_reason
                        # instead of sending [DONE]. We should break gracefully here.
                        self._flush_print_buffers()
                        break

            # Add final content to response
            full_response["choices"][0]["message"]["content"] = content_buffer
            # Add any completed tool calls with valid function names
            valid_tool_calls = []  # Initialize here to prevent UnboundLocalError
            if tool_call_buffers:
                for index, tool_call in tool_call_buffers.items():
                    # Include tool calls that have a function name (ID is now generated if missing)
                    if (
                        "function" in tool_call
                        and "name" in tool_call["function"]
                        and tool_call["function"]["name"].strip()
                    ):
                        valid_tool_calls.append(tool_call)
                    else:
                        dmsg(f"Skipping incomplete tool call at index {index}")
                        dmsg(f"Tool call data: {json.dumps(tool_call, indent=2)}")
                        # Log to stream file if enabled
                        if self.stream_log_file:
                            try:
                                with open(
                                    self.stream_log_file, "a", encoding="utf-8"
                                ) as f:
                                    f.write(
                                        f"DEBUG: Skipping incomplete tool call at index {index}: {json.dumps(tool_call)}\n"
                                    )
                            except Exception:
                                pass

                full_response["choices"][0]["message"]["tool_calls"] = valid_tool_calls

                # Log tool call summary
                dmsg("Tool call processing summary:")
                dmsg(f"Total tool call buffers: {len(tool_call_buffers)}")
                dmsg(f"Valid tool calls: {len(valid_tool_calls)}")
                dmsg(f"Content buffer length: {len(content_buffer)}")

                # Log the valid tool call names
                if valid_tool_calls:
                    tool_names = [
                        tc.get("function", {}).get("name", "unknown")
                        for tc in valid_tool_calls
                    ]
                    dmsg(f"Valid tool call names: {tool_names}")

            # Log to stream file if enabled
            if self.stream_log_file:
                try:
                    with open(self.stream_log_file, "a", encoding="utf-8") as f:
                        f.write(
                            f"DEBUG: Tool call summary - Total: {len(tool_call_buffers)}, Valid: {len(valid_tool_calls)}, Content length: {len(content_buffer)}\n"
                        )
                        if valid_tool_calls:
                            tool_names = [
                                tc.get("function", {}).get("name", "unknown")
                                for tc in valid_tool_calls
                            ]
                            f.write(f"DEBUG: Valid tool call names: {tool_names}\n")
                except Exception:
                    pass

            # Add usage information to the response if available
            if usage_info:
                full_response["usage"] = usage_info

            # Print newline at the end of streaming, but only if we actually printed content
            if content_buffer.strip():  # Only add newline if we had content
                print()  # New line after streaming is complete

            # Stop cursor blinking when streaming is complete
            self.animator.ensure_cursor_visible()

            # Add a flag to indicate this is a streaming response so the main app
            # knows not to print the content again (only if streaming is actually enabled)
            if config.ENABLE_STREAMING:
                full_response["choices"][0]["message"]["_streaming_response"] = True

            # Log the final response if logging is enabled
            if self.stream_log_file:
                try:
                    self._log_stream_data("=== FINAL RESPONSE ===")
                    self._log_stream_data(json.dumps(full_response, indent=2))
                except Exception as e:
                    dmsg(f"Error logging final response: {e}")

            return full_response

        except ShouldRetryException:
            # Re-raise retry exceptions so they bubble up to the retry loop
            raise
        except Exception as e:
            # CRITICAL FIX: Reset streaming state on error to prevent corruption
            self._reset_all_streaming_state()

            # ENHANCED ERROR HANDLING: Always show errors to the user so they know what happened
            APIErrors.print(APIErrors.STREAMING_PROCESSING_ERROR, error=e)

            if config.DEBUG:
                import traceback

                emsg("Full traceback:")
                traceback.print_exc()

            # Stop cursor blinking if there was an error
            self.animator.ensure_cursor_visible()

            # Even if there was an error, try to return what we have so far
            # This prevents the operation from appearing to start but never complete
            try:
                full_response["choices"][0]["message"]["content"] = content_buffer
                # Only set _streaming_response flag if streaming is actually enabled
                if config.ENABLE_STREAMING:
                    full_response["choices"][0]["message"]["_streaming_response"] = True
                # Add usage information if we have it
                if usage_info:
                    full_response["usage"] = usage_info
                return full_response
            except Exception:
                # If we can't even build a minimal response, return None
                # This will be handled by the caller
                return None
        finally:
            # CRITICAL FIX: Always ensure state is clean when exiting streaming
            # This prevents state leakage between requests
            self._reset_all_streaming_state()

    def _process_streaming_tool_call(
        self,
        tool_call_delta: Dict[str, Any],
        tool_call_buffers: Dict[int, Dict[str, Any]],
    ):
        """Process a streaming tool call delta and update buffers."""
        # Handle missing index by using a default or generating one
        index = tool_call_delta.get("index", len(tool_call_buffers))

        # Special handling for Google's empty tool call IDs
        tool_id = tool_call_delta.get("id", "")
        # If ID is empty, generate a unique one to avoid validation issues
        if not tool_id:
            tool_id = f"tool_call_{index}_{int(time.time() * 1000) % 100000}"

        # Initialize buffer for this tool call if needed
        if index not in tool_call_buffers:
            tool_call_buffers[index] = {
                "id": tool_id,  # Use generated ID if original was empty
                "type": "function",
                "function": {"name": "", "arguments": ""},
            }

        # Update tool call buffer with delta
        tool_call = tool_call_buffers[index]

        # Update ID if it's provided (even if empty, we'll use our generated one)
        if "id" in tool_call_delta:
            # Only override our generated ID if the provider gives us a non-empty one
            if tool_call_delta["id"]:
                tool_call["id"] = tool_call_delta["id"]
            # Otherwise, keep our generated ID

        if "type" in tool_call_delta:
            tool_call["type"] = tool_call_delta["type"]

        if "function" in tool_call_delta:
            func_delta = tool_call_delta["function"]
            if "name" in func_delta:
                # Handle null function name (DeepSeek issue)
                name_part = func_delta["name"]
                if name_part is None:
                    dmsg("Received null function name, treating as empty string")
                    name_part = ""
                tool_call["function"]["name"] += name_part
            if "arguments" in func_delta:
                # Handle null arguments (DeepSeek issue)
                args_part = func_delta["arguments"]
                if args_part is None:
                    dmsg("Received null arguments, treating as empty string")
                    args_part = ""
                tool_call["function"]["arguments"] += args_part
                # Debug: Print the arguments as they're being built
                if (
                    config.DEBUG and len(tool_call["function"]["arguments"]) % 100 == 0
                ):  # Print every 100 characters
                    print(
                        f"DEBUG: Arguments so far: {tool_call['function']['arguments'][:200]}..."
                    )

    def _check_user_cancel_during_streaming(self) -> bool:
        """Check for user cancellation during streaming (ESC key)."""
        return is_esc_pressed()

    def _buffer_and_print_content(self, content: str):
        """
        Buffer and print content with intelligent whitespace handling.
        - Before first printable char: Don't print whitespace/newlines
        - After last printable char: Don't print trailing whitespace/newlines
        - In between: Print everything normally
        """
        if not content:
            return

        for char in content:
            # Handle whitespace characters
            if char.isspace() or char in ["\n", "\r", "\t"]:
                if self.seen_first_printable:
                    # We're after the first printable char, buffer as potential trailing whitespace
                    self.trailing_whitespace_buffer += char
                else:
                    # We're before the first printable char, add to print buffer
                    self.print_buffer += char
                continue  # Skip to next character

            # Handle printable characters
            if not self.seen_first_printable:
                self.seen_first_printable = True
                self.print_buffer = ""

            if self.trailing_whitespace_buffer:
                self._print_with_colorization(self.trailing_whitespace_buffer)
                self.trailing_whitespace_buffer = ""

            self._print_with_colorization(char)

    def _flush_print_buffers(self):
        """
        Flush any remaining content in print buffers.
        Called at the end of streaming to ensure all content is displayed.
        """
        # If we never saw a printable character, don't print anything
        if not self.seen_first_printable:
            self.print_buffer = ""
            self.trailing_whitespace_buffer = ""
            return

        # Print any remaining content in buffers
        if self.print_buffer:
            self._print_with_colorization(self.print_buffer)
            self.print_buffer = ""

        if self.trailing_whitespace_buffer:
            # Strip trailing whitespace before printing
            cleaned_content = self.trailing_whitespace_buffer.rstrip()
            if cleaned_content:
                self._print_with_colorization(cleaned_content)
            self.trailing_whitespace_buffer = ""

    def _print_with_colorization(self, content: str):
        """
        Print content with simple colorization using the MarkdownColorizer.
        """
        self.colorizer.print_with_colorization(content)
