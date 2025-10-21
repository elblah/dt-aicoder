"""
Input handling for AI Coder.
"""

import os
from . import config
from .utils import make_readline_safe, wmsg, emsg, imsg
from .readline_history_manager import prompt_history_manager
from .terminal_manager import enter_prompt_mode, exit_prompt_mode





class InputHandlerMixin:
    """Mixin class for input handling."""

    def _display_token_info(self):
        """Display token information before user prompt and AI response."""
        if not hasattr(self, 'stats'):
            return

        from .utils import display_token_info
        display_token_info(self.stats, config.AUTO_COMPACT_THRESHOLD)

    def _get_multiline_input(self) -> str:
        """Get user input with simplified handling (no multiline support)."""
        # Notify plugins before user prompt
        if hasattr(self, 'loaded_plugins'):
            from .plugin_system.loader import notify_plugins_before_user_prompt
            notify_plugins_before_user_prompt(self.loaded_plugins)

        # Display token information before user prompt if enabled
        if config.ENABLE_TOKEN_INFO_DISPLAY:
            self._display_token_info()

        # Enter prompt mode - restore normal terminal settings for readline
        enter_prompt_mode()

        # Reset terminal state to fix any display issues before showing prompt
        try:
            from .terminal_manager import get_terminal_manager
            manager = get_terminal_manager()
            manager._perform_terminal_reset(silent=True)
        except:
            pass  # If reset fails, continue anyway

        # Switch to user input mode for proper history
        prompt_history_manager.setup_user_input_mode()

        # Get planning mode instance to check if we should show [PLAN] prefix
        from .planning_mode import get_planning_mode
        planning_mode = get_planning_mode()

        # Get the prompt prefix
        prompt = planning_mode.get_prompt_prefix()

        # Make the prompt readline-safe to handle colors properly
        safe_prompt = make_readline_safe(prompt)

        # Get single line input
        try:
            user_input = input(safe_prompt).rstrip()
        except KeyboardInterrupt:
            # Ctrl+C should exit the application, not just cancel input
            exit_prompt_mode()  # Restore terminal before raising
            raise
        except EOFError:
            # EOF (Ctrl+D) should also exit
            exit_prompt_mode()  # Restore terminal before raising
            raise

        # Save to user input history
        prompt_history_manager.save_user_input(user_input)

        # Return input without exiting prompt mode - caller will decide when to exit
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
                    wmsg(f"\nPrompt append: {prompt_append_content}")

                    # Append the content with a blank line separator
                    return f"{user_input}\n\n{prompt_append_content}"
            except Exception as e:
                emsg(f"Error reading {prompt_append_file}: {e}")

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
                    wmsg("\nPlanning mode: Read-only tools only")
                else:
                    imsg("\nBuild mode: All tools available")

                # Append the content with a blank line separator
                return f"{user_input}\n\n{mode_content}"
        except ImportError:
            pass  # Planning mode not available

        return user_input