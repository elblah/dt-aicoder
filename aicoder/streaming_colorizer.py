"""
Markdown colorization component for streaming responses.
Handles colorized output of markdown content with proper state management.
"""

from . import config


class MarkdownColorizer:
    """Handles markdown colorization with proper state management."""

    def __init__(self):
        """Initialize colorizer and reset state."""
        self.reset_state()

    def reset_state(self):
        """Reset colorization state for a new streaming response."""
        self._in_code = False
        self._code_tick_count = 0
        self._in_star = False
        self._star_count = 0
        self._at_line_start = True
        self._in_header = False
        self._in_bold = False
        self._consecutive_count = 0
        self._can_be_bold = False

    def print_with_colorization(self, content: str):
        """
        Print content with markdown colorization.

        Color rules:
        - ` starts green, count consecutive `, wait for same number to close
        - * follows same rule when not in green
        - # at line start colors entire line red when not in green
        """
        if not content:
            print(content, end="", flush=True)
            return

        i = 0
        while i < len(content):
            char = content[i]

            # Handle consecutive asterisk counting
            if char == "*":
                self._consecutive_count += 1
                # Only allow bold for exactly 2 asterisks, not 3+
                if self._consecutive_count == 2:
                    self._can_be_bold = True
                elif self._consecutive_count > 2:
                    self._can_be_bold = False
            else:
                self._consecutive_count = 0

            # Handle newlines - reset line start and any active modes
            if char == "\n":
                self._at_line_start = True
                # Reset header mode
                if self._in_header:
                    print(config.RESET, end="", flush=True)
                    self._in_header = False
                # Reset star mode on newline
                if self._in_star:
                    print(config.RESET, end="", flush=True)
                    self._in_star = False
                    self._star_count = 0
                # Reset bold mode on newline
                if self._in_bold:
                    print(config.RESET, end="", flush=True)
                    self._in_bold = False
                # Reset can_be_bold on newline
                self._can_be_bold = False
                print(char, end="", flush=True)
                i += 1
                continue

            # Precedence 1: If we're in code mode, only look for closing backticks
            if self._in_code:
                print(char, end="", flush=True)
                if char == "`":
                    self._code_tick_count -= 1
                    if self._code_tick_count == 0:
                        print(config.RESET, end="", flush=True)
                        self._in_code = False
                i += 1
                continue

            # Precedence 2: If we're in star mode, only look for closing stars
            if self._in_star:
                print(char, end="", flush=True)
                if char == "*":
                    self._star_count -= 1
                    if self._star_count == 0:
                        print(config.RESET, end="", flush=True)
                        self._in_star = False
                        
                        # Handle bold mode logic - only if can_be_bold
                        if self._can_be_bold:
                            if self._in_bold:
                                self._in_bold = False
                            else:
                                self._in_bold = True
                                print(config.BOLD, end="", flush=True)
                        
                        # Reset counters when sequence ends
                        self._consecutive_count = 0
                        self._can_be_bold = False
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
                self._in_code = True
                self._code_tick_count = tick_count
                self._at_line_start = False
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
                print(config.GREEN + config.BOLD, end="", flush=True)
                for k in range(star_count):
                    print("*", end="", flush=True)
                self._in_star = True
                self._star_count = star_count
                self._at_line_start = False
                i += star_count
                continue

            # Precedence 5: Check for header # at line start (lowest precedence)
            if self._at_line_start and char == "#":
                print(config.RED, end="", flush=True)
                self._in_header = True
                print(char, end="", flush=True)
                self._at_line_start = False
                i += 1
                continue

            # Regular character
            print(char, end="", flush=True)
            self._at_line_start = False
            i += 1
