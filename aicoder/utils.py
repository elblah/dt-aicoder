"""
Utility functions for AI Coder.
"""

import os
import difflib
import shutil
from typing import Dict, Any

from .config import GREEN, RED, RESET, DEFAULT_TRUNCATION_LIMIT, YELLOW, BOLD


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
                GREEN + stripped_line + RESET + line[len(stripped_line) :]
            )
        elif line.startswith("-") and not line.startswith("---") and stripped_line:
            # Removed lines (red) - preserve original line ending
            colored_lines.append(
                RED + stripped_line + RESET + line[len(stripped_line) :]
            )
        elif line.startswith("@@") and stripped_line:
            # Diff header lines (yellow) - preserve original line ending
            colored_lines.append(
                YELLOW + stripped_line + RESET + line[len(stripped_line) :]
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
) -> str:
    """Format a user-friendly prompt for tool approval."""
    from .config import DEBUG

    try:
        if DEBUG:
            print(f"DEBUG: Formatting tool prompt for {tool_name}")
            print(f"DEBUG: Tool config: {tool_config}")

        prompt_lines = [f"└─ AI wants to call: {tool_name}"]

        # Print the tool description if available
        if DEBUG and "description" in tool_config:
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
            file_path = arguments.get("file_path", "")
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

            prompt_lines = [f"   AI wants to run a command:{RESET}"]
            if hide_command:
                prompt_lines.append(f"{BOLD}    Command: [HIDDEN]{RESET}")
            else:
                prompt_lines.append(f"{BOLD}    Command: {command}{RESET}")
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
                    and len(value) > DEFAULT_TRUNCATION_LIMIT
                ):
                    value = value[:DEFAULT_TRUNCATION_LIMIT] + "... [truncated]"

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
                result.append(RESET)
                in_header = False
            # Reset star mode on newline
            if in_star:
                result.append(RESET)
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
                    result.append(RESET)
                    in_code = False
            i += 1
            continue

        # Precedence 2: If we're in star mode, only look for closing stars
        if in_star:
            result.append(char)
            if char == "*":
                star_count -= 1
                if star_count == 0:
                    result.append(RESET)
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
            result.append(GREEN)
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
            result.append(GREEN)
            for k in range(star_count):
                result.append("*")
            in_star = True
            star_count = star_count
            at_line_start = False
            i += star_count
            continue

        # Precedence 5: Check for header # at line start (lowest precedence)
        if at_line_start and char == "#":
            result.append(RED)
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


def cancellable_sleep(seconds: float, animator=None) -> bool:
    """Sleep for specified seconds, but allow cancellation via ESC key.

    Args:
        seconds: Number of seconds to sleep
        animator: Optional animator instance to check for cancellation

    Returns:
        bool: True if sleep completed normally, False if cancelled
    """
    import time
    import select
    import sys

    # Try to import termios for Unix systems
    try:
        import termios

        HAS_TERMIOS = True
    except ImportError:
        HAS_TERMIOS = False

    start_time = time.time()
    check_interval = 0.1  # Check for ESC every 100ms

    # Save original terminal settings if available
    old_settings = None
    if HAS_TERMIOS:
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            # Set terminal to non-canonical mode to read single characters
            new_settings = termios.tcgetattr(sys.stdin)
            new_settings[3] = (
                new_settings[3] & ~termios.ICANON
            )  # Disable canonical mode
            new_settings[6][termios.VMIN] = b"\x00"  # Non-blocking read
            new_settings[6][termios.VTIME] = b"\x00"
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new_settings)
        except Exception:
            old_settings = None

    try:
        while time.time() - start_time < seconds:
            # Check for user cancellation
            if animator and animator.check_user_cancel():
                return False

            # Use a non-blocking check for ESC key
            try:
                if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                    ch = sys.stdin.read(1)
                    # Check for ESC key (ASCII 27)
                    if ord(ch) == 27:
                        return False
            except Exception:
                pass

            # Sleep for check interval
            time.sleep(check_interval)

        # Sleep completed normally
        return True
    finally:
        # Restore original terminal settings if we changed them
        if old_settings is not None and HAS_TERMIOS:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except Exception:
                pass
