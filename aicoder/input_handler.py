"""
Input handling for AI Coder.
"""

import os
import readline
from . import config
from .utils import make_readline_safe
from .prompt_history_manager import prompt_history_manager


class InputHandlerMixin:
    """Mixin class for input handling."""

    def _display_token_info(self):
        """Display token information before user prompt and AI response."""
        if not hasattr(self, 'stats'):
            return
        
        from .utils import display_token_info
        display_token_info(self.stats, config.AUTO_COMPACT_THRESHOLD)

    def _get_multiline_input(self) -> str:
        """Handles multi-line input with backslash continuation."""
        # Notify plugins before user prompt
        if hasattr(self, 'loaded_plugins'):
            from .plugin_system.loader import notify_plugins_before_user_prompt
            notify_plugins_before_user_prompt(self.loaded_plugins)
        
        # Display token information before user prompt if enabled
        if config.ENABLE_TOKEN_INFO_DISPLAY:
            self._display_token_info()

        # Switch to user input mode for proper history
        prompt_history_manager.setup_user_input_mode()

        # Get planning mode instance to check if we should show [PLAN] prefix
        from .planning_mode import get_planning_mode
        planning_mode = get_planning_mode()

        lines = []
        while True:
            if not lines:
                prompt = planning_mode.get_prompt_prefix()
            else:
                prompt = f"{config.GREEN}...{config.RESET} "
            # Make the prompt readline-safe to handle colors properly
            safe_prompt = make_readline_safe(prompt)
            try:
                line = input(safe_prompt).rstrip()

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

        user_input = "\n".join(lines)
        
        # Save to user input history
        prompt_history_manager.save_user_input(user_input)
        
        return user_input

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
                    print(f"\n{config.YELLOW}Prompt append: {prompt_append_content}{config.RESET}")

                    # Append the content with a blank line separator
                    return f"{user_input}\n\n{prompt_append_content}"
            except Exception as e:
                print(f"{config.RED}Error reading {prompt_append_file}: {e}{config.RESET}")

        # Return original input if no file or empty content
        return user_input

    def _handle_planning_mode_content(self, user_input: str) -> str:
        """Handles planning mode content appending."""
        # Skip for commands
        if len(user_input) > 0 and user_input[0] == "/":
            return user_input
            
        try:
            from .planning_mode import get_planning_mode
            planning_mode = get_planning_mode()
            
            # Get mode content (plan mode reminder or build switch)
            mode_content = planning_mode.get_mode_content()
            if mode_content:
                # Print the mode content being added
                if planning_mode.is_plan_mode_active():
                    print(f"\n{config.YELLOW}Planning mode: Read-only tools only{config.RESET}")
                else:
                    print(f"\n{config.GREEN}Build mode: All tools available{config.RESET}")
                
                # Append the content with a blank line separator
                return f"{user_input}\n\n{mode_content}"
        except ImportError:
            pass  # Planning mode not available
            
        return user_input
