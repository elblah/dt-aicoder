"""
Input handling for AI Coder.
"""

import os
from .config import GREEN, YELLOW, RED, RESET, BOLD


class InputHandlerMixin:
    """Mixin class for input handling."""

    def _get_multiline_input(self) -> str:
        """Handles multi-line input with backslash continuation."""
        lines = []
        while True:
            prompt = f"{BOLD}{GREEN}\n>{RESET} " if not lines else f"{GREEN}...{RESET} "
            try:
                line = input(prompt).rstrip()

                # Check if this is a continuation line (ends with backslash)
                if line.endswith("\\") and not line.endswith("\\\\"):
                    # Remove the trailing backslash and add to lines
                    lines.append(line[:-1])
                else:
                    # If it's a regular line or ends with escaped backslash
                    if line.endswith("\\\\"):
                        # Replace escaped backslash with single backslash
                        line = line[:-1]
                    lines.append(line)
                    break
            except KeyboardInterrupt:
                # Ctrl+C should exit the application, not just cancel input
                raise
            except EOFError:
                # EOF (Ctrl+D) should also exit
                raise

        return "\n".join(lines)

    def _handle_prompt_append(self, user_input: str) -> str:
        """Handles prompt appending functionality."""
        if len(user_input) > 0 and user_input[0] == "/":
            # Ignore commands
            return user_input

        prompt_append_file = "prompt_append.txt"

        # Check if prompt_append.txt exists
        if os.path.exists(prompt_append_file):
            try:
                with open(prompt_append_file, "r", encoding="utf-8") as f:
                    prompt_append_content = f.read().strip()

                # If file has content, append it to user input
                if prompt_append_content:
                    # Print a blank line and the prompt append content in yellow
                    print(f"\n{YELLOW}Prompt append: {prompt_append_content}{RESET}")

                    # Append the content with a blank line separator
                    return f"{user_input}\n\n{prompt_append_content}"
            except Exception as e:
                print(f"{RED}Error reading {prompt_append_file}: {e}{RESET}")

        # Return original input if no file or empty content
        return user_input
