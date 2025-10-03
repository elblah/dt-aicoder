"""
Streaming adapter for AI Coder to handle SSE streaming responses.
This module provides a pluggable adapter that can handle both streaming
and regular API responses without breaking existing functionality.
"""

import json
import re
import time
import select
import tty
import sys
import socket
import urllib.request
import urllib.error
import threading
import os
from typing import List, Dict, Any, Optional

from . import config
from .animator import Animator
from .api_client import APIClient


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
            print(
                f"{config.GREEN}*** Streaming log enabled: {self.stream_log_file}{config.RESET}"
            )

        # State for markdown colorization across streaming chunks
        self._reset_colorization_state()

    def _log_stream_data(self, data: str):
        """Log streaming data to file if logging is enabled."""
        if self.stream_log_file:
            try:
                with open(self.stream_log_file, "a", encoding="utf-8") as f:
                    f.write(data + "\n")
            except Exception as e:
                if config.DEBUG:
                    print(f"{config.RED}Error writing to stream log: {e}{config.RESET}")

    def _reset_colorization_state(self):
        """Reset markdown colorization state for a new streaming response."""
        self._color_in_code = False
        self._color_code_tick_count = 0
        self._color_in_star = False
        self._color_star_count = 0
        self._color_at_line_start = True
        self._color_in_header = False

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
        self._reset_colorization_state()

        # Also reset any print buffers that might be left over
        if hasattr(self, "print_buffer"):
            self.print_buffer = ""
        if hasattr(self, "seen_first_printable"):
            self.seen_first_printable = False
        if hasattr(self, "trailing_whitespace_buffer"):
            self.trailing_whitespace_buffer = ""

        # Disable streaming for internal prompts to avoid interference with application logic
        # and to ensure reliable response handling for programmatic use cases
        if disable_streaming_mode:
            # Call the original non-streaming implementation directly to avoid recursion
            return self._make_non_streaming_request(messages, disable_tools)

        # For regular requests, use streaming
        try:
            return self._streaming_request(messages, disable_streaming_mode)
        except Exception as e:
            if config.DEBUG:
                print(f"DEBUG: Streaming failed, falling back to regular request: {e}")
            # Fallback to regular request
            return self._make_non_streaming_request(messages)

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

        self.animator.start_animation("Making API request...")

        # Track API call time
        api_start_time = time.time()

        while True:
            try:
                # Validate tool definitions using shared functionality
                self._validate_tool_definitions(api_data)
                request_body = json.dumps(api_data).encode("utf-8")
            except TypeError as e:
                self.animator.stop_animation()
                print(
                    f"\n{config.RED}Error serializing data for API request: {e}{config.RESET}"
                )
                return None
            except Exception:
                self.animator.stop_animation()
                raise

            if config.DEBUG:
                print(f"DEBUG: data length = {len(request_body)}")

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
            old_settings = None
            try:
                old_settings = self._setup_terminal_for_input()
                tty.setcbreak(sys.stdin.fileno())

                # Wait for the thread to complete or for user cancellation
                while api_thread.is_alive():
                    time.sleep(0.1)  # Small delay to prevent busy-waiting

                    # Check for ESC keypress (non-blocking)
                    if self._handle_user_cancellation():
                        self.animator.stop_animation()
                        print(
                            f"\n{config.RED}Request cancelled by user (ESC).{config.RESET}"
                        )
                        # Note: We can't actually terminate the API request thread,
                        # but we can ignore its result
                        return None

                # Thread has completed, get the result
                self.animator.stop_animation()

                # Wait for thread to finish and get result
                api_thread.join()

                if result_dict.get("success"):
                    processed_response = result_dict["response"]
                    self._update_stats_on_success(
                        api_start_time, processed_response
                    )

                    # Extract token usage information from the response if not handled by _update_stats_on_success
                    if processed_response and "usage" in processed_response:
                        usage = processed_response["usage"]
                        if config.DEBUG:
                            print(f"DEBUG: Non-streaming usage data: {usage}")
                        # Extract prompt tokens (input) and completion tokens (output)
                        if "prompt_tokens" in usage and self.stats:
                            self.stats.current_prompt_size = usage["prompt_tokens"]
                            self.stats.prompt_tokens += usage["prompt_tokens"]
                        if "completion_tokens" in usage and self.stats:
                            self.stats.completion_tokens += usage["completion_tokens"]
                    
                    return processed_response
                else:
                    # Record time spent even on failed API calls
                    self._update_stats_on_failure(api_start_time)

                    # Handle specific error types with user-friendly messages
                    error = result_dict.get("error")
                    error_type = result_dict.get("error_type", "general_error")

                    if error_type == "http_timeout":
                        http_timeout = int(os.environ.get("HTTP_TIMEOUT", "300"))
                        print(
                            f"\n{config.RED}HTTP connection timeout reached ({http_timeout} seconds).{config.RESET}"
                        )
                        print(
                            f"{config.YELLOW}The connection to the AI model timed out. This can happen with slow models.{config.RESET}"
                        )
                        print(
                            f"{config.YELLOW}Tip: Set HTTP_TIMEOUT=X to increase timeout (e.g., HTTP_TIMEOUT=600 for 10 minutes){config.RESET}"
                        )
                        print(
                            f"{config.YELLOW}Tip: You can also press ESC to cancel if you think it's taking too long{config.RESET}"
                        )
                        return None
                    elif error_type == "http_error":
                        # Re-raise HTTP errors so they can be handled by the outer exception handler
                        # which will route them to the retry logic
                        raise error
                    elif error_type == "connection_error":
                        print(f"\n{config.RED}Connection error: {error}{config.RESET}")
                        print(
                            f"{config.YELLOW}Check your internet connection and API endpoint.{config.RESET}"
                        )
                        return None
                    else:
                        # For general errors, re-raise to let existing error handling deal with it
                        raise error

            except Exception as e:
                self.animator.stop_animation()
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
            finally:
                # Restore terminal settings only if we successfully saved them
                if old_settings is not None:
                    self._restore_terminal(old_settings)

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
                if config.DEBUG:
                    print(f"{config.RED}Error logging request data: {e}{config.RESET}")

        self.animator.start_animation("Making API request...")

        # Track API call time
        api_start_time = time.time()

        while True:
            try:
                # Validate tool definitions using shared functionality
                self._validate_tool_definitions(api_data)
                request_body = json.dumps(api_data).encode("utf-8")
            except TypeError as e:
                self.animator.stop_animation()
                print(
                    f"\n{config.RED}Error serializing data for API request: {e}{config.RESET}"
                )
                return None
            except Exception:
                self.animator.stop_animation()
                raise

            if config.DEBUG:
                if not disable_streaming_mode:
                    print(f"DEBUG: data length = {len(request_body)}")

            # Create a generator for streaming response
            def streaming_worker(result_dict, stop_event):
                """Worker function to handle streaming API request."""
                try:
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {config.API_KEY}",
                        "User-Agent": "Mozilla/5.0",
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
            old_settings = None
            try:
                old_settings = self._setup_terminal_for_input()
                tty.setcbreak(sys.stdin.fileno())

                # Wait for the thread to complete or for user cancellation
                while api_thread.is_alive():
                    time.sleep(0.1)  # Small delay to prevent busy-waiting

                    # Check for ESC keypress (non-blocking)
                    if self._handle_user_cancellation():
                        self.animator.stop_animation()
                        print(
                            f"\n{config.RED}Request cancelled by user (ESC).{config.RESET}"
                        )
                        # Note: We can't actually terminate the API request thread,
                        # but we can ignore its result
                        return None

                # Thread has completed, get the result
                self.animator.stop_animation()

                # Wait for thread to finish and get result
                api_thread.join()

                if result_dict.get("success"):
                    response = result_dict["response"]
                    processed_response = self._process_streaming_response(response)

                    # Update stats using shared functionality
                    self._update_stats_on_success(
                        api_start_time, processed_response or {}
                    )

                    # Extract token usage information from the response
                    if processed_response and "usage" in processed_response:
                        usage = processed_response["usage"]
                        if config.DEBUG:
                            print(f"DEBUG: Streaming usage data: {usage}")
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
                        if hasattr(self.api_handler, 'message_history') and self.api_handler.message_history:
                            from .utils import estimate_messages_tokens
                            estimated_input_tokens = estimate_messages_tokens(self.api_handler.message_history.messages)
                        
                        # Estimate output tokens from the response content
                        if processed_response and "choices" in processed_response and len(processed_response["choices"]) > 0:
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

                    return processed_response
                else:
                    # Record time spent even on failed API calls
                    self._update_stats_on_failure(api_start_time)

                    # Handle specific error types with user-friendly messages
                    error = result_dict.get("error")
                    error_type = result_dict.get("error_type", "general_error")

                    if error_type == "http_timeout":
                        http_timeout = int(os.environ.get("HTTP_TIMEOUT", "300"))
                        print(
                            f"\n{config.RED}HTTP connection timeout reached ({http_timeout} seconds).{config.RESET}"
                        )
                        print(
                            f"{config.YELLOW}The connection to the AI model timed out. This can happen with slow models.{config.RESET}"
                        )
                        print(
                            f"{config.YELLOW}Tip: Set HTTP_TIMEOUT=X to increase timeout (e.g., HTTP_TIMEOUT=600 for 10 minutes){config.RESET}"
                        )
                        print(
                            f"{config.YELLOW}Tip: You can also press ESC to cancel if you think it's taking too long{config.RESET}"
                        )
                        return None
                    elif error_type == "http_error":
                        # Re-raise HTTP errors so they can be handled by the outer exception handler
                        # which will route them to the retry logic
                        raise error
                    elif error_type == "connection_error":
                        print(f"\n{config.RED}Connection error: {error}{config.RESET}")
                        print(
                            f"{config.YELLOW}Check your internet connection and API endpoint.{config.RESET}"
                        )
                        return None
                    else:
                        # For general errors, re-raise to let existing error handling deal with it
                        raise error

            except Exception as e:
                self.animator.stop_animation()
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
            finally:
                # Restore terminal settings only if we successfully saved them
                if old_settings is not None:
                    self._restore_terminal(old_settings)

    def _process_streaming_response(self, response) -> Optional[Dict[str, Any]]:
        """Process streaming response and return final message."""
        # Reset colorization state for new streaming response
        self._reset_colorization_state()

        # Process the streaming response
        full_response = {
            "id": "",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": config.API_MODEL,
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
            # Get streaming timeout from environment variable, default to 300 seconds (5 minutes)
            timeout_seconds = int(os.environ.get("STREAMING_TIMEOUT", "300"))
            # Also get individual read timeout (how long to wait for each line)
            read_timeout_seconds = int(os.environ.get("STREAMING_READ_TIMEOUT", "30"))

            # Use non-blocking streaming with individual read timeouts
            while True:
                # Check for overall timeout first
                current_time = time.time()
                if current_time - last_data_time > timeout_seconds:
                    print(
                        f"\n{config.RED}Streaming timeout reached ({timeout_seconds} seconds with no SSE data).{config.RESET}"
                    )
                    print(
                        f"{config.YELLOW}Tip: Set STREAMING_TIMEOUT=X to adjust (e.g., STREAMING_TIMEOUT=600 for 10 minutes){config.RESET}"
                    )
                    print(
                        f"{config.YELLOW}Tip: For HTTP connection timeouts, set HTTP_TIMEOUT=X (e.g., HTTP_TIMEOUT=600){config.RESET}"
                    )
                    return None

                # Read a line with timeout to prevent hanging on slow/unresponsive servers
                line = None
                read_start_time = time.time()

                # Non-blocking line read with timeout
                timeout_reminder_shown = False
                while line is None:
                    try:
                        # Check if socket is still connected first
                        if hasattr(response, "fp") and hasattr(response.fp, "_sock"):
                            sock = response.fp._sock

                            # Check if socket is still connected using select
                            # This will detect if the connection was closed by the server
                            try:
                                ready_to_read, _, exceptional_conditions = (
                                    select.select([sock], [], [sock], 0.1)
                                )

                                # If socket is in exceptional conditions, connection was dropped
                                if exceptional_conditions:
                                    print(
                                        f"\n{config.RED}🚫 Connection dropped by server (detected by select).{config.RESET}"
                                    )
                                    print(
                                        f"{config.YELLOW}The AI model server closed the connection unexpectedly.{config.RESET}"
                                    )
                                    print(
                                        f"{config.YELLOW}Please try your request again - the connection may work next time.{config.RESET}"
                                    )
                                    return None

                                # If socket is not ready to read and no timeout yet, continue waiting
                                if not ready_to_read:
                                    # Check if we've exceeded read timeout
                                    if (
                                        time.time() - read_start_time
                                        > read_timeout_seconds
                                    ):
                                        if not timeout_reminder_shown:
                                            print(f"\r{' ' * 80}", end="", flush=True)
                                            print(
                                                f"\n{config.YELLOW}⚠️  It's been {read_timeout_seconds} seconds with no new data.{config.RESET}"
                                            )
                                            print(
                                                f"{config.YELLOW}   Press ESC to cancel the request, or wait for more data...{config.RESET}"
                                            )
                                            timeout_reminder_shown = True

                                        if self._check_user_cancel_during_streaming():
                                            print(
                                                f"\n{config.RED}Request cancelled by user (ESC).{config.RESET}"
                                            )
                                            return None
                                        continue
                                    time.sleep(0.1)  # Small delay before checking again
                                    continue

                                # Socket is ready to read, try to read data
                                original_timeout = sock.gettimeout()
                                # Use a patient read timeout - very slow models can take 30+ seconds per line
                                read_timeout = min(
                                    30.0, read_timeout_seconds
                                )  # Cap at 30 seconds per read for very slow models
                                sock.settimeout(read_timeout)
                                try:
                                    line = response.fp.readline()
                                    if not line:  # EOF - connection closed
                                        print(
                                            f"\n{config.RED}🚫 Connection dropped by server (EOF detected).{config.RESET}"
                                        )
                                        print(
                                            f"{config.YELLOW}The AI model server closed the connection unexpectedly.{config.RESET}"
                                        )
                                        print(
                                            f"{config.YELLOW}Please try your request again - the connection may work next time.{config.RESET}"
                                        )
                                        return None
                                except socket.timeout:
                                    # Read timeout - this could mean either:
                                    # 1. Connection is hanging/dead
                                    # 2. Model is extremely slow (2 tokens/second can take 30+ seconds per line)

                                    # Check if this is the first timeout or if we've had multiple
                                    current_time = time.time()
                                    if not hasattr(self, "_read_timeout_count"):
                                        self._read_timeout_count = 0
                                        self._first_timeout_time = current_time

                                    self._read_timeout_count += 1

                                    # If we've had multiple timeouts over a longer period, connection is likely dead
                                    # Be very patient - allow up to 3 timeouts over 60 seconds for extremely slow models
                                    if (
                                        self._read_timeout_count >= 3
                                        and (current_time - self._first_timeout_time)
                                        < 60.0
                                    ):
                                        print(
                                            f"\n{config.RED}🚫 Connection dropped by server (multiple read timeouts).{config.RESET}"
                                        )
                                        print(
                                            f"{config.YELLOW}The AI model server stopped responding mid-stream.{config.RESET}"
                                        )
                                        print(
                                            f"{config.YELLOW}Please try your request again - the connection may work next time.{config.RESET}"
                                        )
                                        return None

                                    # If we've been waiting too long overall (more than 2 minutes), give up
                                    if (
                                        current_time - self._first_timeout_time
                                    ) > 120.0:
                                        print(
                                            f"\n{config.RED}🚫 Connection dropped by server (excessive wait time).{config.RESET}"
                                        )
                                        print(
                                            f"{config.YELLOW}Waited over 2 minutes with incomplete response.{config.RESET}"
                                        )
                                        print(
                                            f"{config.YELLOW}The AI model server is too slow or connection is unstable.{config.RESET}"
                                        )
                                        print(
                                            f"{config.YELLOW}Please try your request again with a faster model.{config.RESET}"
                                        )
                                        return None

                                    # Show progress warning for slow models
                                    if self._read_timeout_count == 1:
                                        print(
                                            f"\n{config.YELLOW}⏳ Very slow model detected (no data for {read_timeout}s).{config.RESET}"
                                        )
                                        print(
                                            f"{config.YELLOW}   Some models take 30+ seconds per line when generating complex responses.{config.RESET}"
                                        )
                                        print(
                                            f"{config.YELLOW}   Waiting patiently... Press ESC to cancel if needed.{config.RESET}"
                                        )
                                    elif (
                                        self._read_timeout_count % 5 == 0
                                    ):  # Every 5th timeout
                                        minutes_waited = (
                                            int(current_time - self._first_timeout_time)
                                            // 60
                                        )
                                        seconds_waited = (
                                            int(current_time - self._first_timeout_time)
                                            % 60
                                        )
                                        print(
                                            f"\n{config.YELLOW}⏳ Still waiting for slow model... ({minutes_waited}m {seconds_waited}s elapsed).{config.RESET}"
                                        )
                                        print(
                                            f"{config.YELLOW}   Press ESC to cancel if you think it's stuck.{config.RESET}"
                                        )

                                    # Check for ESC key press while waiting
                                    if self._check_user_cancel_during_streaming():
                                        print(
                                            f"\n{config.RED}Request cancelled by user (ESC).{config.RESET}"
                                        )
                                        return None

                                    # Continue the loop to try reading again
                                    continue
                                finally:
                                    sock.settimeout(original_timeout)

                            except (ConnectionResetError, BrokenPipeError):
                                print(
                                    f"\n{config.RED}🚫 Connection dropped by server (connection reset).{config.RESET}"
                                )
                                print(
                                    f"{config.YELLOW}The AI model server closed the connection unexpectedly.{config.RESET}"
                                )
                                print(
                                    f"{config.YELLOW}Please try your request again - the connection may work next time.{config.RESET}"
                                )
                                return None
                            except socket.error as e:
                                if e.errno in [10054, 104]:  # Connection reset by peer
                                    print(
                                        f"\n{config.RED}🚫 Connection dropped by server (connection reset).{config.RESET}"
                                    )
                                    print(
                                        f"{config.YELLOW}The AI model server closed the connection unexpectedly.{config.RESET}"
                                    )
                                    print(
                                        f"{config.YELLOW}Please try your request again - the connection may work next time.{config.RESET}"
                                    )
                                    return None
                                else:
                                    # Other socket errors
                                    if config.DEBUG:
                                        print(
                                            f"{config.RED}Socket error: {e}{config.RESET}"
                                        )
                                    return None
                        else:
                            # Fallback: read with small timeout
                            line = response.readline()
                            if not line:  # EOF
                                print(
                                    f"\n{config.RED}🚫 Connection dropped by server (EOF detected).{config.RESET}"
                                )
                                print(
                                    f"{config.YELLOW}The AI model server closed the connection unexpectedly.{config.RESET}"
                                )
                                print(
                                    f"{config.YELLOW}Please try your request again - the connection may work next time.{config.RESET}"
                                )
                                return None

                    except socket.timeout:
                        # Socket timeout occurred, check if we've exceeded read timeout
                        if time.time() - read_start_time > read_timeout_seconds:
                            if not timeout_reminder_shown:
                                print(f"\r{' ' * 80}", end="", flush=True)
                                print(
                                    f"\n{config.YELLOW}⚠️  It's been {read_timeout_seconds} seconds with no new data.{config.RESET}"
                                )
                                print(
                                    f"{config.YELLOW}   Press ESC to cancel the request, or wait for more data...{config.RESET}"
                                )
                                timeout_reminder_shown = True

                            if self._check_user_cancel_during_streaming():
                                print(
                                    f"\n{config.RED}Request cancelled by user (ESC).{config.RESET}"
                                )
                                return None
                            continue
                        continue
                    except (ConnectionResetError, BrokenPipeError):
                        print(
                            f"\n{config.RED}🚫 Connection dropped by server (connection reset).{config.RESET}"
                        )
                        print(
                            f"{config.YELLOW}The AI model server closed the connection unexpectedly.{config.RESET}"
                        )
                        print(
                            f"{config.YELLOW}Please try your request again - the connection may work next time.{config.RESET}"
                        )
                        return None
                    except Exception as e:
                        if config.DEBUG:
                            print(
                                f"{config.RED}Error reading from stream: {e}{config.RESET}"
                            )
                        return None

                    # Check overall timeout during read attempt
                    if time.time() - last_data_time > timeout_seconds:
                        print(
                            f"\n{config.RED}Streaming timeout reached ({timeout_seconds} seconds with no SSE data).{config.RESET}"
                        )
                        return None

                # If we got here, we have a line to process
                # The connection drop detection above handles EOF cases, so we don't need to check again here

                # Process the line we read
                # Check for timeout - only if no SSE data received in the last X seconds
                current_time = time.time()
                if current_time - last_data_time > timeout_seconds:
                    print(
                        f"\n{config.RED}Streaming timeout reached ({timeout_seconds} seconds with no SSE data).{config.RESET}"
                    )
                    print(
                        f"{config.YELLOW}Tip: Set STREAMING_TIMEOUT=X to adjust (e.g., STREAMING_TIMEOUT=600 for 10 minutes){config.RESET}"
                    )
                    return None

                if not first_token_received:
                    # Display token information before AI response if enabled
                    if config.ENABLE_TOKEN_INFO_DISPLAY and hasattr(self, 'stats'):
                        from .utils import display_token_info
                        display_token_info(self.stats, config.AUTO_COMPACT_THRESHOLD)
                        print()  # Add newline after token info

                    first_token_received = True
                    self.animator.stop_animation()
                    self.animator.start_cursor_blinking()
                    print(
                        f"{config.BOLD}{config.GREEN}AI:{config.RESET} ",
                        end="",
                        flush=True,
                    )

                # Check for user cancellation during streaming (more frequently)
                if self._check_user_cancel_during_streaming():
                    print(f"\n{config.RED}Streaming cancelled by user.{config.RESET}")
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
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix

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
                        if "choices" in data and len(data["choices"]) > 0:
                            choice = data["choices"][0]

                            # Process content
                            if "delta" in choice and "content" in choice["delta"]:
                                content = choice["delta"]["content"]
                                if content:
                                    content_buffer += content
                                    # Use new buffering system to handle whitespace
                                    self._buffer_and_print_content(content)

                            # Process tool calls - handle null or missing tool_calls gracefully
                            if "delta" in choice and "tool_calls" in choice["delta"]:
                                tool_calls = choice["delta"]["tool_calls"]
                                # Handle the case where tool_calls is null (DeepSeek issue)
                                if tool_calls is None:
                                    if config.DEBUG:
                                        print(
                                            f"{config.YELLOW} * Debug: Received null tool_calls from API, treating as empty array{config.RESET}"
                                        )
                                    tool_calls = []
                                # Ensure tool_calls is iterable
                                if not isinstance(tool_calls, list):
                                    if config.DEBUG:
                                        print(
                                            f"{config.YELLOW} * Debug: tool_calls is not a list ({type(tool_calls)}), treating as empty array{config.RESET}"
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

                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue

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
                        if config.DEBUG:
                            print(
                                f"{config.RED} * Debug: Skipping incomplete tool call at index {index}:{config.RESET}"
                            )
                            print(
                                f"{config.RED} * Debug: Tool call data: {json.dumps(tool_call, indent=2)}{config.RESET}"
                            )
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

            # Log tool call summary if debug enabled
            if config.DEBUG:
                print(
                    f"{config.YELLOW} * Debug: Tool call processing summary:{config.RESET}"
                )
                print(
                    f"{config.YELLOW} * Debug: Total tool call buffers: {len(tool_call_buffers)}{config.RESET}"
                )
                print(
                    f"{config.YELLOW} * Debug: Valid tool calls: {len(valid_tool_calls)}{config.RESET}"
                )
                print(
                    f"{config.YELLOW} * Debug: Content buffer length: {len(content_buffer)}{config.RESET}"
                )

                # Log the valid tool call names
                if valid_tool_calls:
                    tool_names = [
                        tc.get("function", {}).get("name", "unknown")
                        for tc in valid_tool_calls
                    ]
                    print(
                        f"{config.YELLOW} * Debug: Valid tool call names: {tool_names}{config.RESET}"
                    )

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
                    if config.DEBUG:
                        print(
                            f"{config.RED}Error logging final response: {e}{config.RESET}"
                        )

            return full_response

        except Exception as e:
            # CRITICAL FIX: Reset streaming state on error to prevent corruption
            self._reset_colorization_state()

            # Also reset print buffers
            if hasattr(self, "print_buffer"):
                self.print_buffer = ""
            if hasattr(self, "seen_first_printable"):
                self.seen_first_printable = False
            if hasattr(self, "trailing_whitespace_buffer"):
                self.trailing_whitespace_buffer = ""

            # ENHANCED ERROR HANDLING: Always show errors to the user so they know what happened
            print(
                f"\n{config.RED}Error processing streaming response: {e}{config.RESET}"
            )
            print(
                f"{config.YELLOW}This appears to be an API compatibility issue. The streaming was interrupted.{config.RESET}"
            )
            print(
                f"{config.YELLOW}You can try running with ENABLE_STREAMING=0 to disable streaming mode.{config.RESET}"
            )

            if config.DEBUG:
                import traceback

                print(f"{config.RED}Full traceback:{config.RESET}")
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
            self._reset_colorization_state()

            # Also reset print buffers
            if hasattr(self, "print_buffer"):
                self.print_buffer = ""
            if hasattr(self, "seen_first_printable"):
                self.seen_first_printable = False
            if hasattr(self, "trailing_whitespace_buffer"):
                self.trailing_whitespace_buffer = ""

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
                    if config.DEBUG:
                        print(
                            f"{config.YELLOW} * Debug: Received null function name, treating as empty string{config.RESET}"
                        )
                    name_part = ""
                tool_call["function"]["name"] += name_part
            if "arguments" in func_delta:
                # Handle null arguments (DeepSeek issue)
                args_part = func_delta["arguments"]
                if args_part is None:
                    if config.DEBUG:
                        print(
                            f"{config.YELLOW} * Debug: Received null arguments, treating as empty string{config.RESET}"
                        )
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
        try:
            # Use a non-blocking check with a very short timeout
            if select.select([sys.stdin], [], [], 0.01) == ([sys.stdin], [], []):
                key = sys.stdin.read(1)
                # Check for ESC key (ASCII 27)
                if ord(key) == 27:
                    return True
        except IOError:
            # No input available
            pass
        except Exception:
            # Handle any other exceptions that might prevent ESC from working
            if config.DEBUG:
                print(
                    f"{config.RED} * Debug: Exception in ESC detection: {sys.exc_info()[0]}{config.RESET}"
                )
            pass
        return False

    def _colorize_content(self, content: str) -> str:
        """
        Apply simple colorization to content without removing any characters.
        Preserves all markdown syntax while adding color.
        """
        if not content:
            return content

        # Colorize markdown headers (###, ##, #) without removing them
        # Headers - preserve the '#' characters but add color
        content = re.sub(
            r"(^|\n)(#{1,3} .+?)(?=\n|$)",
            rf"\1{config.BOLD}{config.BRIGHT_GREEN}\2{config.RESET}",
            content,
            flags=re.MULTILINE,
        )

        # Bold (**text**) - preserve the asterisks but add color
        content = re.sub(
            r"(\*\*.+?\*\*)",
            rf"{config.BOLD}\1{config.RESET}",
            content,
        )

        # Italic (*text*) - preserve the asterisks but add color
        content = re.sub(
            r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)",
            rf"{config.ITALIC}\1{config.RESET}",
            content,
        )

        # Inline code (`code`) - preserve the backticks but add color
        content = re.sub(
            r"(`.+?`)",
            rf"{config.BRIGHT_GREEN}\1{config.RESET}",
            content,
        )

        return content

    def _simple_colorize_content(self, content: str) -> str:
        """
        Apply simple character-by-character colorization to avoid gaps in streaming.
        This method adds color codes without consuming or modifying any characters.
        """
        if not content:
            return content

        # Simple colorization that works character-by-character
        # We'll just add color to certain patterns without complex regex processing
        result = []
        i = 0
        while i < len(content):
            char = content[i]

            # Check for inline code (`code`)
            if char == "`" and i + 1 < len(content):
                # Find the closing backtick
                end = content.find("`", i + 1)
                if end != -1:
                    # Colorize the entire inline code segment
                    result.append(config.BRIGHT_GREEN)  # Green color
                    result.append(content[i : end + 1])  # Include both backticks
                    result.append(config.RESET)  # Reset color
                    i = end + 1
                    continue

            # Check for bold (**text**)
            if char == "*" and i + 1 < len(content) and content[i + 1] == "*":
                # Find the closing **
                end = content.find("**", i + 2)
                if end != -1:
                    # Colorize the entire bold segment
                    result.append(config.BOLD)  # Bold
                    result.append(content[i : end + 2])  # Include both **
                    result.append(config.RESET)  # Reset
                    i = end + 2
                    continue

            # Check for italic (*text*)
            if char == "*" and i + 1 < len(content) and content[i + 1] != "*":
                # Find the closing *
                end = content.find("*", i + 1)
                if end != -1 and (end + 1 >= len(content) or content[end + 1] != "*"):
                    # Make sure this isn't the start of a bold pattern
                    # Colorize the entire italic segment
                    result.append(config.ITALIC)  # Italic
                    result.append(content[i : end + 1])  # Include both *
                    result.append(config.RESET)  # Reset
                    i = end + 1
                    continue

            # For headers, we need to be more careful since they're line-based
            # We'll just add the character as-is for now
            result.append(char)
            i += 1

        return "".join(result)

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
            if char.isspace() or char in ["\n", "\r", "\t"]:
                # Whitespace character
                if self.seen_first_printable:
                    # We're after the first printable char, buffer as potential trailing whitespace
                    self.trailing_whitespace_buffer += char
                else:
                    # We're before the first printable char, add to print buffer
                    self.print_buffer += char
            else:
                # Printable character
                if not self.seen_first_printable:
                    # This is the first printable character we've seen
                    self.seen_first_printable = True
                    # DISCARD any whitespace that was before it (don't print leading whitespace)
                    self.print_buffer = ""

                # We have a printable character, flush any trailing whitespace first
                if self.trailing_whitespace_buffer:
                    self._print_with_colorization(self.trailing_whitespace_buffer)
                    self.trailing_whitespace_buffer = ""

                # Print the printable character
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
        Print content with simple colorization based on your clear specification:
        - ` starts green, count consecutive `, wait for same number to close
        - * follows same rule when not in green
        - # at line start colors entire line red when not in green
        """
        if not content:
            print(content, end="", flush=True)
            return

        # Color codes
        # These are now imported from config.py:
        # RED = "\033[31m"
        # GREEN = "\033[32m"
        # RESET = "\033[0m"

        i = 0
        while i < len(content):
            char = content[i]

            # Handle newlines - reset line start and any active modes
            if char == "\n":
                self._color_at_line_start = True
                # Reset header mode
                if self._color_in_header:
                    print(config.RESET, end="", flush=True)
                    self._color_in_header = False
                # Reset star mode on newline
                if self._color_in_star:
                    print(config.RESET, end="", flush=True)
                    self._color_in_star = False
                    self._color_star_count = 0
                print(char, end="", flush=True)
                i += 1
                continue

            # Precedence 1: If we're in code mode, only look for closing backticks
            if self._color_in_code:
                print(char, end="", flush=True)
                if char == "`":
                    self._color_code_tick_count -= 1
                    if self._color_code_tick_count == 0:
                        print(config.RESET, end="", flush=True)
                        self._color_in_code = False
                i += 1
                continue

            # Precedence 2: If we're in star mode, only look for closing stars
            if self._color_in_star:
                print(char, end="", flush=True)
                if char == "*":
                    self._color_star_count -= 1
                    if self._color_star_count == 0:
                        print(config.RESET, end="", flush=True)
                        self._color_in_star = False
                i += 1
                continue

            # Precedence 3: Check for backticks (highest precedence)
            if char == "`":
                # Count consecutive backticks
                tick_count = 0
                j = i
                while j < len(content) and content[j] == "`":
                    tick_count += 1
                    j += 1

                # Start code block
                print(config.GREEN, end="", flush=True)
                for k in range(tick_count):
                    print("`", end="", flush=True)
                self._color_in_code = True
                self._color_code_tick_count = tick_count
                self._color_at_line_start = False
                i += tick_count
                continue

            # Precedence 4: Check for asterisks (medium precedence)
            if char == "*":
                # Count consecutive asterisks
                star_count = 0
                j = i
                while j < len(content) and content[j] == "*":
                    star_count += 1
                    j += 1

                # Start star block
                print(config.GREEN, end="", flush=True)
                for k in range(star_count):
                    print("*", end="", flush=True)
                self._color_in_star = True
                self._color_star_count = star_count
                self._color_at_line_start = False
                i += star_count
                continue

            # Precedence 5: Check for header # at line start (lowest precedence)
            if self._color_at_line_start and char == "#":
                print(config.RED, end="", flush=True)
                self._color_in_header = True
                print(char, end="", flush=True)
                self._color_at_line_start = False
                i += 1
                continue

            # Regular character
            print(char, end="", flush=True)
            self._color_at_line_start = False
            i += 1
