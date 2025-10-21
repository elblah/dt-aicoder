"""
Utility functions for AI Coder.
"""

import os
import difflib
import shutil
import json
import datetime
from typing import Dict, Any, List, Union

from . import config


def make_readline_safe(text: str) -> str:
    """Make color codes safe for readline by wrapping them with RL_PROMPT_START_IGNORE and RL_PROMPT_END_IGNORE.

    These are \001 and \002 characters that tell readline to ignore cursor positioning
    for the enclosed characters.

    Args:
        text: Text containing color codes

    Returns:
        Text with color codes wrapped for readline safety
    """
    if not text:
        return text

    result = text
    # Replace all available color codes with readline-safe versions
    for color_code in [
        config.RESET,
        config.BOLD,
        config.RED,
        config.GREEN,
        config.YELLOW,
        config.BLUE,
    ]:
        result = result.replace(color_code, f"\001{color_code}\002")

    return result


def safe_strip(val, default="no content"):
    return val.strip() if isinstance(val, str) else default


def colorize_diff_lines(text):
    """Colorize lines that start with + or - for better visibility."""

    if not text:
        return text

    # Split into lines, preserving line endings
    lines = text.splitlines(True)
    colored_lines = []

    for line in lines:
        # Strip the line ending for comparison
        stripped_line = line.rstrip("\r\n")

        # Colorize based on line type
        if line.startswith("+") and not line.startswith("+++") and stripped_line:
            # Added lines (green) - preserve original line ending
            colored_lines.append(
                config.GREEN + stripped_line + config.RESET + line[len(stripped_line) :]
            )
        elif line.startswith("-") and not line.startswith("---") and stripped_line:
            # Removed lines (red) - preserve original line ending
            colored_lines.append(
                config.RED + stripped_line + config.RESET + line[len(stripped_line) :]
            )
        elif line.startswith("@@") and stripped_line:
            # Diff header lines (yellow) - preserve original line ending
            colored_lines.append(
                config.YELLOW
                + stripped_line
                + config.RESET
                + line[len(stripped_line) :]
            )
        else:
            # Unchanged lines (default color) - preserve original line exactly
            colored_lines.append(line)

    return "".join(colored_lines)


def format_tool_prompt(
    tool_name: str,
    arguments: Dict[str, Any],
    tool_config: Dict[str, Any],
    path: str = "",
    raw_arguments: str = None,
) -> str:
    """Format a user-friendly prompt for tool approval."""

    try:
        if config.DEBUG:
            print(f"DEBUG: Formatting tool prompt for {tool_name}")
            print(f"DEBUG: Tool config: {tool_config}")

        prompt_lines = [f"└─ AI wants to call: {tool_name}"]

        # Show raw JSON in debug mode or if provided
        if config.DEBUG and raw_arguments:
            prompt_lines.append(f"   Raw JSON: {raw_arguments}")
        elif raw_arguments and not config.DEBUG:
            # In non-debug mode, still show raw JSON if it's clearly malformed
            try:
                import json

                json.loads(raw_arguments)
            except json.JSONDecodeError:
                prompt_lines.append(f"   Raw JSON (malformed): {raw_arguments}")

        # Print the tool description if available
        if config.DEBUG and "description" in tool_config:
            print(f"DEBUG: Tool description: {tool_config['description']}")

        # Special handling for specific tools
        if tool_name == "write_file":
            content = arguments.get("content", "")
            old_content = ""
            if path and os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        old_content = f.read()
                except Exception:
                    pass

            if old_content != content:
                # Simple line-based diff
                old_lines = old_content.splitlines(keepends=True)
                new_lines = content.splitlines(keepends=True)
                diff = list(
                    difflib.unified_diff(
                        old_lines,
                        new_lines,
                        fromfile=f"{path} (old)",
                        tofile=f"{path} (new)",
                    )
                )

                if diff:
                    # Colorize the diff output using our new function
                    diff_text = colorize_diff_lines("".join(diff))
                else:
                    diff_text = "No significant changes detected."

                prompt_lines.append(f"File: {path}")
                prompt_lines.append("Changes:")
                prompt_lines.append(diff_text)
            else:
                prompt_lines.append(f"File: {path} (unchanged)")

        elif tool_name == "edit_file":
            # For edit_file, show a diff of what will change
            file_path = arguments.get("path", "")
            old_string = arguments.get("old_string", "")
            new_string = arguments.get("new_string", "")

            # Check if parameters should be hidden
            hidden_parameters = tool_config.get("hidden_parameters", [])

            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        old_content = f.read()

                    # Check if old_string exists in the file
                    if old_string in old_content:
                        # Check if old_string is unique
                        first_index = old_content.find(old_string)
                        last_index = old_content.rfind(old_string)

                        if first_index != last_index:
                            prompt_lines.append(f"File: {file_path}")
                            prompt_lines.append(
                                "Warning: old_string appears multiple times in the file"
                            )
                        else:
                            # Always generate diff for edit_file - users need to see changes to approve them
                            # Even when parameters are hidden, we can show the actual file changes
                            # Generate the new content
                            new_content = (
                                old_content[:first_index]
                                + new_string
                                + old_content[first_index + len(old_string) :]
                            )

                            # Generate diff
                            old_lines = old_content.splitlines(keepends=True)
                            new_lines = new_content.splitlines(keepends=True)
                            diff = list(
                                difflib.unified_diff(
                                    old_lines,
                                    new_lines,
                                    fromfile=f"{file_path} (old)",
                                    tofile=f"{file_path} (new)",
                                )
                            )

                            if diff:
                                # Colorize the diff output
                                diff_text = colorize_diff_lines("".join(diff))
                                prompt_lines.append(f"File: {file_path}")
                                prompt_lines.append("Changes:")
                                prompt_lines.append(diff_text)
                            else:
                                prompt_lines.append(f"File: {file_path} (no changes)")
                    else:
                        prompt_lines.append(f"File: {file_path}")
                        prompt_lines.append("Warning: old_string not found in file")
                except Exception as e:
                    prompt_lines.append(f"Error reading file {file_path}: {e}")
            elif file_path and not os.path.exists(file_path) and old_string == "":
                # For new file creation (old_string is empty), show a diff with all lines as additions
                old_content = ""
                new_content = new_string

                # Generate diff for new file (empty old content vs new content)
                old_lines = old_content.splitlines(keepends=True)
                new_lines = new_content.splitlines(keepends=True)
                diff = list(
                    difflib.unified_diff(
                        old_lines,
                        new_lines,
                        fromfile=f"{file_path} (old)",
                        tofile=f"{file_path} (new)",
                    )
                )

                if diff:
                    # Colorize the diff output
                    diff_text = colorize_diff_lines("".join(diff))
                    prompt_lines.append(f"File: {file_path} (new file)")
                    prompt_lines.append("Changes:")
                    prompt_lines.append(diff_text)
                else:
                    prompt_lines.append(f"File: {file_path} (new file)")
                    prompt_lines.append("Content:")
                    prompt_lines.append(
                        new_string[:500] + "..."
                        if len(new_string) > 500
                        else new_string
                    )
            else:
                # For new files, show what will be created
                prompt_lines.append(f"File: {file_path} (new file)")
                if new_string:
                    prompt_lines.append("Content:")
                    prompt_lines.append(
                        new_string[:500] + "..."
                        if len(new_string) > 500
                        else new_string
                    )

        elif tool_name == "run_shell_command":
            command = arguments.get("command", "")
            reason = arguments.get("reason", "")
            # Get default timeout from environment variable, fallback to 30 if not set
            default_timeout = int(os.environ.get("SHELL_COMMAND_TIMEOUT", 30))
            timeout = arguments.get("timeout", default_timeout)

            # Check if parameters should be hidden
            hidden_parameters = tool_config.get("hidden_parameters", [])
            hide_command = "command" in hidden_parameters
            hide_reason = "reason" in hidden_parameters
            hide_timeout = "timeout" in hidden_parameters

            prompt_lines = [f"   AI wants to run a command:{config.RESET}"]
            if hide_command:
                prompt_lines.append(f"{config.BOLD}    Command: [HIDDEN]{config.RESET}")
            else:
                prompt_lines.append(
                    f"{config.BOLD}    Command: {command}{config.RESET}"
                )
            if reason and not hide_reason:
                prompt_lines.append(f"    Reason: {reason}")
            elif hide_reason and reason:
                prompt_lines.append("    Reason: [HIDDEN]")
            if not hide_timeout:
                prompt_lines.append(f"    Timeout: {timeout} seconds")
            else:
                prompt_lines.append("    Timeout: [HIDDEN]")

        else:
            # Generic handling for other tools
            prompt_lines.append("Arguments:")
            # Get hidden parameters configuration
            hidden_parameters = tool_config.get("hidden_parameters", [])

            for key, value in arguments.items():
                # Hide sensitive parameters
                if key in hidden_parameters:
                    prompt_lines.append(f"  {key}: [HIDDEN]")
                    continue

                # Apply truncation if specified in tool config
                truncated_chars = tool_config.get("truncated_chars", 0)
                if (
                    truncated_chars > 0
                    and isinstance(value, str)
                    and len(value) > truncated_chars
                ):
                    value = (
                        value[:truncated_chars]
                        + f"... [truncated to {truncated_chars} chars]"
                    )
                # Fallback to default truncation if no specific setting
                elif (
                    truncated_chars == 0
                    and isinstance(value, str)
                    and len(value) > config.DEFAULT_TRUNCATION_LIMIT
                ):
                    value = value[: config.DEFAULT_TRUNCATION_LIMIT] + "... [truncated]"

                prompt_lines.append(f"    {key}: {value}")

        return "\n".join(prompt_lines)
    except Exception as e:
        # Fallback to basic prompt on error
        return f"└─ AI wants to call: {tool_name}\nArguments: {arguments}\n(Error formatting details: {e})"


def parse_markdown_streaming_style(text: str) -> str:
    """
    Parse markdown using the streaming adapter's character-by-character approach.
    This provides consistent colorization between streaming and non-streaming modes.
    """
    if not text:
        return text

    # State variables to track parsing state (similar to streaming adapter)
    in_code = False
    code_tick_count = 0
    in_star = False
    star_count = 0
    at_line_start = True
    in_header = False

    result = []
    i = 0
    while i < len(text):
        char = text[i]

        # Handle newlines - reset line start and any active modes
        if char == "\n":
            at_line_start = True
            # Reset header mode
            if in_header:
                result.append(config.RESET)
                in_header = False
            # Reset star mode on newline
            if in_star:
                result.append(config.RESET)
                in_star = False
                star_count = 0
            result.append(char)
            i += 1
            continue

        # Precedence 1: If we're in code mode, only look for closing backticks
        if in_code:
            result.append(char)
            if char == "`":
                code_tick_count -= 1
                if code_tick_count == 0:
                    result.append(config.RESET)
                    in_code = False
            i += 1
            continue

        # Precedence 2: If we're in star mode, only look for closing stars
        if in_star:
            result.append(char)
            if char == "*":
                star_count -= 1
                if star_count == 0:
                    result.append(config.RESET)
                    in_star = False
            i += 1
            continue

        # Precedence 3: Check for backticks (highest precedence)
        if char == "`":
            # Count consecutive backticks
            tick_count = 0
            j = i
            while j < len(text) and text[j] == "`":
                tick_count += 1
                j += 1

            # Start code block
            result.append(config.GREEN)
            for k in range(tick_count):
                result.append("`")
            in_code = True
            code_tick_count = tick_count
            at_line_start = False
            i += tick_count
            continue

        # Precedence 4: Check for asterisks (medium precedence)
        if char == "*":
            # Count consecutive asterisks
            star_count = 0
            j = i
            while j < len(text) and text[j] == "*":
                star_count += 1
                j += 1

            # Start star block
            result.append(config.GREEN)
            for k in range(star_count):
                result.append("*")
            in_star = True
            star_count = star_count
            at_line_start = False
            i += star_count
            continue

        # Precedence 5: Check for header # at line start (lowest precedence)
        if at_line_start and char == "#":
            result.append(config.RED)
            in_header = True
            result.append(char)
            at_line_start = False
            i += 1
            continue

        # Regular character
        result.append(char)
        at_line_start = False
        i += 1

    return "".join(result)


def parse_markdown(text: str) -> str:
    """A robust markdown parser that converts markdown to terminal-formatted text.

    This function now uses the streaming-style parsing for consistency between
    streaming and non-streaming modes.
    """
    return parse_markdown_streaming_style(text)


# Cache for tool availability checks
_tool_availability_cache = {}


def check_tool_availability(tool_name: str) -> bool:
    """Check if a command-line tool is available, with caching.

    Args:
        tool_name: Name of the tool to check for availability

    Returns:
        bool: True if the tool is available, False otherwise
    """
    # Return cached result if available
    if tool_name in _tool_availability_cache:
        return _tool_availability_cache[tool_name]

    try:
        # Use shutil.which which is more reliable than subprocess with 'command'
        is_available = shutil.which(tool_name) is not None
        # Cache the result
        _tool_availability_cache[tool_name] = is_available
        return is_available
    except Exception:
        # Cache failure result as well
        _tool_availability_cache[tool_name] = False
        return False


def hide_cursor():
    """Hide the cursor in the terminal."""
    import sys

    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    """Show the cursor in the terminal."""
    import sys

    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text string.
    Uses the standard approach: 4 characters per token.
    This is fast and good enough for pruning decisions.
    """
    if not text:
        return 0
    return max(0, round(len(text) / 4))


def estimate_messages_tokens(messages: List[Dict]) -> int:
    """
    Estimate total tokens for a list of messages.
    """
    total = 0
    for msg in messages:
        # Estimate content
        content = msg.get("content", "")
        total += estimate_tokens(content)

        # Estimate tool calls if present
        if "tool_calls" in msg and msg["tool_calls"]:
            for tool_call in msg["tool_calls"]:
                if isinstance(tool_call, dict) and "function" in tool_call:
                    func_name = tool_call["function"].get("name", "")
                    func_args = tool_call["function"].get("arguments", "")
                    total += estimate_tokens(func_name)
                    total += estimate_tokens(func_args)

        # Estimate tool results
        if msg.get("role") == "tool":
            tool_call_id = msg.get("tool_call_id", "")
            total += estimate_tokens(tool_call_id)

    return total


def display_token_info(stats, auto_compact_threshold=None):
    """Display token information in the requested format.

    Args:
        stats: Stats object containing token information
        auto_compact_threshold: Threshold value for calculating percentage (defaults to config.AUTO_COMPACT_THRESHOLD if not provided)
    """
    if not stats:
        return

    # Import config at the beginning
    import aicoder.config as config

    # Use provided threshold or fall back to config
    if auto_compact_threshold is None:
        threshold = config.AUTO_COMPACT_THRESHOLD
    else:
        threshold = auto_compact_threshold

    # Calculate usage percentage based on context size or threshold
    usage_percentage = 0
    display_threshold = threshold  # Default to the threshold for display

    if config.AUTO_COMPACT_ENABLED:
        # If auto-compaction is enabled, show percentage of context size and trigger point
        usage_percentage = min(
            100, (stats.current_prompt_size / config.CONTEXT_SIZE) * 100
        )
        display_threshold = config.CONTEXT_SIZE
    elif threshold > 0:
        # If using old-style threshold, calculate against that
        usage_percentage = min(100, (stats.current_prompt_size / threshold) * 100)
    else:
        # If no threshold, calculate against context size
        usage_percentage = min(
            100, (stats.current_prompt_size / config.CONTEXT_SIZE) * 100
        )
        display_threshold = config.CONTEXT_SIZE

    # Create visual representation (10 segments wide) with half-based rounding
    # Fill n-th segment if usage >= 5 + 10*(n-1) %, i.e., (usage + 5) // 10
    filled_bars = int((usage_percentage + 5) // 10)
    filled_bars = min(10, filled_bars)  # Cap at 10 for 100%
    empty_bars = 10 - filled_bars

    # Choose color based on usage percentage
    if usage_percentage <= 50:
        bar_color = config.GREEN
    elif usage_percentage <= 80:
        bar_color = config.YELLOW
    else:
        bar_color = config.RED

    # Add color to filled balls based on usage level
    bars = f"{bar_color}{config.TOKEN_INFO_FILLED_CHAR * filled_bars}{config.TOKEN_INFO_EMPTY_CHAR * empty_bars}{config.RESET}"

    # Format numbers for display - use abbreviated format for cleaner output
    def format_token_count(count):
        if count >= 1000000:
            return f"{count / 1000000:.1f}M"
        elif count >= 1000:
            return f"{count / 1000:.1f}k"
        else:
            return str(count)

    current_size_formatted = format_token_count(stats.current_prompt_size)
    threshold_formatted = format_token_count(display_threshold)
    current_time = datetime.datetime.now().strftime("%H:%M:%S")

    # Display token info in the abbreviated format
    print(
        f"\nContext: {bars} {usage_percentage:.0f}% ({current_size_formatted}/{threshold_formatted} @{config.get_api_model()}) \033[2m- {current_time}\033[22m",
        end="",
        flush=True,
    )


def cancellable_sleep(seconds: float, animator=None) -> bool:
    """Sleep for specified seconds, but allow cancellation via ESC key.

    Args:
        seconds: Number of seconds to sleep
        animator: Optional animator instance to check for cancellation

    Returns:
        bool: True if sleep completed normally, False if cancelled
    """
    import time
    from .terminal_manager import is_esc_pressed, setup_for_non_prompt_input

    # Setup terminal for ESC detection
    setup_for_non_prompt_input()

    start_time = time.time()
    check_interval = 0.1  # Check for ESC every 100ms

    try:
        while time.time() - start_time < seconds:
            # Check for user cancellation via centralized terminal manager
            if is_esc_pressed():
                return False

            # Check via animator if provided (for backwards compatibility)
            if animator and animator.check_user_cancel():
                return False

            # Sleep for check interval
            time.sleep(check_interval)

        # Sleep completed normally
        return True
    finally:
        # No cleanup needed - terminal manager handles state
        pass


def parse_json_arguments(arguments: Union[str, dict, list]) -> Union[dict, list]:
    """
    Parse JSON arguments that may be double/triple encoded.

    Handles the case where AI models send JSON as a string, which may itself
    be encoded multiple times (e.g., '{"arg": "value"}' vs '"{\\"arg\\": \\"value\\"}"')

    Args:
        arguments: Either a dict/list (already parsed) or a JSON string that needs parsing

    Returns:
        Parsed dict or list

    Raises:
        json.JSONDecodeError: If JSON is malformed
        ValueError: If after max attempts we still have a string
    """
    # If already a dict or list, return as-is
    if not isinstance(arguments, str):
        return arguments

    current_value = arguments
    max_attempts = 5

    for attempt in range(max_attempts):
        try:
            parsed = json.loads(current_value)

            # If we got a dict or list, this is what we want
            if isinstance(parsed, (dict, list)):
                return parsed
            # If we got a string, try parsing again (handles double/triple encoding)
            elif isinstance(parsed, str):
                current_value = parsed
                continue
            else:
                # Unexpected type (int, float, bool, None) - return as-is
                return parsed

        except json.JSONDecodeError:
            # If we can't parse and this is the first attempt, the original was malformed
            if attempt == 0:
                raise
            else:
                # We parsed some levels but then hit malformed JSON
                raise ValueError(
                    f"Arguments still a string after {attempt} parse attempts: {current_value}"
                )

    # If we get here, we maxed out attempts and still have a string
    raise ValueError(
        f"Arguments still a string after {max_attempts} parse attempts: {current_value}"
    )


def colorize(msg: str, color: str) -> str:
    return f"{color}{msg}{config.RESET}"


# Print variants
def wmsg(msg: str, file=None) -> None:
    """Print a yellow message."""
    print(colorize(msg, config.YELLOW), file=file)


def emsg(msg: str, file=None) -> None:
    """Print a red error message."""
    print(colorize(msg, config.RED), file=file)


def imsg(msg: str, file=None) -> None:
    """Print a green info message."""
    print(colorize(msg, config.GREEN), file=file)


# String-return variants
def wmsg_str(msg: str) -> str:
    """Return a colorized yellow string."""
    return colorize(msg, config.YELLOW)


def emsg_str(msg: str) -> str:
    """Return a colorized red string."""
    return colorize(msg, config.RED)


def imsg_str(msg: str) -> str:
    """Return a colorized green string."""
    return colorize(msg, config.GREEN)
