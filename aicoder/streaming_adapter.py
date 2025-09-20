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
import urllib.request
import urllib.error
import threading
import os
from typing import List, Dict, Any, Optional

from .config import (
    DEBUG,
    RED,
    GREEN,
    RESET,
    API_MODEL,
    API_ENDPOINT,
    API_KEY,
    BOLD,
    ITALIC,
    BRIGHT_GREEN,
)
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
            print(f"{GREEN}*** Streaming log enabled: {self.stream_log_file}{RESET}")

        # State for markdown colorization across streaming chunks
        self._reset_colorization_state()

    def _log_stream_data(self, data: str):
        """Log streaming data to file if logging is enabled."""
        if self.stream_log_file:
            try:
                with open(self.stream_log_file, "a", encoding="utf-8") as f:
                    f.write(data + "\n")
            except Exception as e:
                if DEBUG:
                    print(f"{RED}Error writing to stream log: {e}{RESET}")

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
        # Disable streaming for internal prompts to avoid interference with application logic
        # and to ensure reliable response handling for programmatic use cases
        if disable_streaming_mode:
            # Call the original non-streaming implementation directly to avoid recursion
            return self._make_non_streaming_request(messages, disable_tools)

        # For regular requests, use streaming
        try:
            return self._streaming_request(messages, disable_streaming_mode)
        except Exception as e:
            if DEBUG:
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
                print(f"\n{RED}Error serializing data for API request: {e}{RESET}")
                return None
            except Exception:
                self.animator.stop_animation()
                raise

            if DEBUG:
                print(f"DEBUG: data length = {len(request_body)}")

            # Threading approach for API request with ESC cancellation support
            def api_request_worker(result_dict, stop_event):
                """Worker function to make the API request in a separate thread."""
                try:
                    response_data = self._make_http_request(api_data, timeout=600)
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
                        print(f"\n{RED}Request cancelled by user (ESC).{RESET}")
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
                    return result_dict["response"]
                else:
                    # Record time spent even on failed API calls
                    self._update_stats_on_failure(api_start_time)
                    raise result_dict["error"]

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
                if DEBUG:
                    print(f"{RED}Error logging request data: {e}{RESET}")

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
                print(f"\n{RED}Error serializing data for API request: {e}{RESET}")
                return None
            except Exception:
                self.animator.stop_animation()
                raise

            if DEBUG:
                if not disable_streaming_mode:
                    print(f"DEBUG: data length = {len(request_body)}")

            # Create a generator for streaming response
            def streaming_worker(result_dict, stop_event):
                """Worker function to handle streaming API request."""
                try:
                    req = urllib.request.Request(
                        API_ENDPOINT,
                        data=request_body,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {API_KEY}",
                            "User-Agent": "Mozilla/5.0",
                            "Referrer": "localhost",
                        },
                        method="POST",
                    )
                    # Use a shorter timeout for streaming requests
                    response = urllib.request.urlopen(req, timeout=300)
                    result_dict["response"] = response
                    result_dict["success"] = True
                except Exception as e:
                    result_dict["error"] = e
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
                        print(f"\n{RED}Request cancelled by user (ESC).{RESET}")
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
                        if DEBUG:
                            print(f"DEBUG: Streaming usage data: {usage}")
                        # Extract prompt tokens (input) and completion tokens (output)
                        if "prompt_tokens" in usage:
                            self.stats.prompt_tokens += usage["prompt_tokens"]
                        if "completion_tokens" in usage:
                            self.stats.completion_tokens += usage["completion_tokens"]

                    return processed_response
                else:
                    # Record time spent even on failed API calls
                    self._update_stats_on_failure(api_start_time)
                    raise result_dict["error"]

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
            "model": API_MODEL,
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

        try:
            # Keep track of time to implement a timeout
            last_data_time = time.time()
            timeout_seconds = 300  # 5 minute timeout for streaming

            for line in response:
                # Check for timeout
                current_time = time.time()
                if current_time - last_data_time > timeout_seconds:
                    print(
                        f"\n{RED}Streaming timeout reached ({timeout_seconds} seconds).{RESET}"
                    )
                    return None

                if not first_token_received:
                    first_token_received = True
                    self.animator.stop_animation()
                    self.animator.start_cursor_blinking()
                    print(f"\n{BOLD}{GREEN}AI:{RESET} ", end="", flush=True)

                # Check for user cancellation during streaming (more frequently)
                if self._check_user_cancel_during_streaming():
                    print(f"\n{RED}Streaming cancelled by user.{RESET}")
                    self.animator.stop_cursor_blinking()
                    return None

                # Update last data time
                last_data_time = time.time()

                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix

                    # Log the raw SSE data if logging is enabled
                    self._log_stream_data(data_str)

                    # End of stream
                    if data_str == "[DONE]":
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
                                    # Print content with simple line-by-line colorization
                                    # This avoids cursor positioning issues while still providing color
                                    self._print_with_colorization(content)

                            # Process tool calls
                            if "delta" in choice and "tool_calls" in choice["delta"]:
                                tool_calls = choice["delta"]["tool_calls"]
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
            if tool_call_buffers:
                valid_tool_calls = []
                for index, tool_call in tool_call_buffers.items():
                    # Include tool calls that have a function name (ID is now generated if missing)
                    if (
                        "function" in tool_call
                        and "name" in tool_call["function"]
                        and tool_call["function"]["name"].strip()
                    ):
                        valid_tool_calls.append(tool_call)
                    elif DEBUG:
                        print(
                            f"{RED} * Debug: Skipping incomplete tool call (missing function name){RESET}"
                        )

                full_response["choices"][0]["message"]["tool_calls"] = valid_tool_calls

            # Add usage information to the response if available
            if usage_info:
                full_response["usage"] = usage_info

            # Print newline at the end of streaming, but only if we actually printed content
            if content_buffer.strip():  # Only add newline if we had content
                print()  # New line after streaming is complete

            # Stop cursor blinking when streaming is complete
            self.animator.ensure_cursor_visible()

            # Add a flag to indicate this is a streaming response so the main app
            # knows not to print the content again
            full_response["choices"][0]["message"]["_streaming_response"] = True

            # Log the final response if logging is enabled
            if self.stream_log_file:
                try:
                    self._log_stream_data("=== FINAL RESPONSE ===")
                    self._log_stream_data(json.dumps(full_response, indent=2))
                except Exception as e:
                    if DEBUG:
                        print(f"{RED}Error logging final response: {e}{RESET}")

            return full_response

        except Exception as e:
            if DEBUG:
                print(f"\n{RED}Error processing streaming response: {e}{RESET}")
            # Stop cursor blinking if there was an error
            self.animator.ensure_cursor_visible()
            # Even if there was an error, return what we have so far
            # This prevents the operation from appearing to start but never complete
            try:
                full_response["choices"][0]["message"]["content"] = content_buffer
                full_response["choices"][0]["message"]["_streaming_response"] = True
                # Add usage information if we have it
                if usage_info:
                    full_response["usage"] = usage_info
                return full_response
            except Exception:
                return None

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
                tool_call["function"]["name"] += func_delta["name"]
            if "arguments" in func_delta:
                tool_call["function"]["arguments"] += func_delta["arguments"]
                # Debug: Print the arguments as they're being built
                if (
                    DEBUG and len(tool_call["function"]["arguments"]) % 100 == 0
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
            if DEBUG:
                print(
                    f"{RED} * Debug: Exception in ESC detection: {sys.exc_info()[0]}{RESET}"
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
            rf"\1{BOLD}{BRIGHT_GREEN}\2{RESET}",
            content,
            flags=re.MULTILINE,
        )

        # Bold (**text**) - preserve the asterisks but add color
        content = re.sub(
            r"(\*\*.+?\*\*)",
            rf"{BOLD}\1{RESET}",
            content,
        )

        # Italic (*text*) - preserve the asterisks but add color
        content = re.sub(
            r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)",
            rf"{ITALIC}\1{RESET}",
            content,
        )

        # Inline code (`code`) - preserve the backticks but add color
        content = re.sub(
            r"(`.+?`)",
            rf"{BRIGHT_GREEN}\1{RESET}",
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
                    result.append(BRIGHT_GREEN)  # Green color
                    result.append(content[i : end + 1])  # Include both backticks
                    result.append(RESET)  # Reset color
                    i = end + 1
                    continue

            # Check for bold (**text**)
            if char == "*" and i + 1 < len(content) and content[i + 1] == "*":
                # Find the closing **
                end = content.find("**", i + 2)
                if end != -1:
                    # Colorize the entire bold segment
                    result.append(BOLD)  # Bold
                    result.append(content[i : end + 2])  # Include both **
                    result.append(RESET)  # Reset
                    i = end + 2
                    continue

            # Check for italic (*text*)
            if char == "*" and i + 1 < len(content) and content[i + 1] != "*":
                # Find the closing *
                end = content.find("*", i + 1)
                if end != -1 and (end + 1 >= len(content) or content[end + 1] != "*"):
                    # Make sure this isn't the start of a bold pattern
                    # Colorize the entire italic segment
                    result.append(ITALIC)  # Italic
                    result.append(content[i : end + 1])  # Include both *
                    result.append(RESET)  # Reset
                    i = end + 1
                    continue

            # For headers, we need to be more careful since they're line-based
            # We'll just add the character as-is for now
            result.append(char)
            i += 1

        return "".join(result)

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
                    print(RESET, end="", flush=True)
                    self._color_in_header = False
                # Reset star mode on newline
                if self._color_in_star:
                    print(RESET, end="", flush=True)
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
                        print(RESET, end="", flush=True)
                        self._color_in_code = False
                i += 1
                continue

            # Precedence 2: If we're in star mode, only look for closing stars
            if self._color_in_star:
                print(char, end="", flush=True)
                if char == "*":
                    self._color_star_count -= 1
                    if self._color_star_count == 0:
                        print(RESET, end="", flush=True)
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
                print(GREEN, end="", flush=True)
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
                print(GREEN, end="", flush=True)
                for k in range(star_count):
                    print("*", end="", flush=True)
                self._color_in_star = True
                self._color_star_count = star_count
                self._color_at_line_start = False
                i += star_count
                continue

            # Precedence 5: Check for header # at line start (lowest precedence)
            if self._color_at_line_start and char == "#":
                print(RED, end="", flush=True)
                self._color_in_header = True
                print(char, end="", flush=True)
                self._color_at_line_start = False
                i += 1
                continue

            # Regular character
            print(char, end="", flush=True)
            self._color_at_line_start = False
            i += 1

    def _simple_colorize_inline(self, content: str) -> str:
        """
        Apply simple colorization only to inline markdown elements to avoid positioning issues.
        This method only colorizes elements that don't affect line structure:
        - Inline code (`code`)
        - Bold (**text**)
        - Italic (*text*)
        """
        if not content:
            return content

        # We'll process the content and only add color to inline elements
        # This avoids issues with headers which can cause positioning problems
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
                    result.append(BRIGHT_GREEN)  # Green color
                    result.append(content[i : end + 1])  # Include both backticks
                    result.append(RESET)  # Reset color
                    i = end + 1
                    continue

            # Check for bold (**text**)
            if char == "*" and i + 1 < len(content) and content[i + 1] == "*":
                # Find the closing **
                end = content.find("**", i + 2)
                if end != -1:
                    # Colorize the entire bold segment
                    result.append(BOLD)  # Bold
                    result.append(content[i : end + 2])  # Include both **
                    result.append(RESET)  # Reset
                    i = end + 2
                    continue

            # Check for italic (*text*)
            if char == "*" and i + 1 < len(content) and content[i + 1] != "*":
                # Find the closing *
                end = content.find("*", i + 1)
                if end != -1 and (end + 1 >= len(content) or content[end + 1] != "*"):
                    # Make sure this isn't the start of a bold pattern
                    # Colorize the entire italic segment
                    result.append(ITALIC)  # Italic
                    result.append(content[i : end + 1])  # Include both *
                    result.append(RESET)  # Reset
                    i = end + 1
                    continue

            # Add the character as-is
            result.append(char)
            i += 1

        return "".join(result)
