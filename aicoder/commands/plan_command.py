"""
Plan command for AI Coder.
"""

from typing import Tuple, List
from .base import BaseCommand
from .. import config


class PlanCommand(BaseCommand):
    """Manage planning mode: /plan [on|off|start|end|true|false|toggle|focus|help] - Show or toggle planning mode."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/plan", "/plan toggle", "/plan focus", "/plan help"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Manage planning mode: /plan [on|off|start|end|true|false|toggle|focus|help] - Show or toggle planning mode."""
        from ..planning_mode import get_planning_mode

        planning_mode = get_planning_mode()

        if not args:
            # Show current status
            print(f"\n{planning_mode.get_status_text()}")
            return False, False

        arg = args[0].lower()
        if arg == "toggle":
            # Toggle planning mode
            new_state = planning_mode.toggle_plan_mode()
            if new_state:
                print(
                    f"\n{config.GREEN}*** Planning mode enabled (read-only){config.RESET}"
                )
            else:
                print(
                    f"\n{config.GREEN}*** Planning mode disabled (read-write){config.RESET}"
                )
        elif arg in ["on", "start", "enable", "1", "true"]:
            # Enable planning mode
            planning_mode.set_plan_mode(True)
            print(
                f"\n{config.GREEN}*** Planning mode enabled (read-only){config.RESET}"
            )
        elif arg in ["off", "end", "disable", "0", "false"]:
            # Disable planning mode
            planning_mode.set_plan_mode(False)
            print(
                f"\n{config.GREEN}*** Planning mode disabled (read-write){config.RESET}"
            )
        elif arg == "focus":
            # Create new session focused on last assistant message
            return self._handle_focus_command()
        elif arg == "help":
            # Show help for plan command
            return self._handle_help_command()
        else:
            print(
                f"\n{config.RED}*** Invalid argument. Use: /plan [on|off|start|end|true|false|toggle|focus|help]{config.RESET}"
            )

        return False, False

    def _handle_help_command(self) -> Tuple[bool, bool]:
        """Handle the help subcommand to show detailed help for plan command."""
        from ..planning_mode import get_planning_mode

        planning_mode = get_planning_mode()

        print(f"\n{config.CYAN}Planning Mode Commands:{config.RESET}")
        print(f"\n{config.YELLOW}Usage: /plan [subcommand]{config.RESET}")
        print(f"\n{config.GREEN}Subcommands:{config.RESET}")
        print(
            f"  {config.BOLD}/plan{config.RESET}                    Show current planning mode status"
        )
        print(
            f"  {config.BOLD}/plan toggle{config.RESET}            Toggle planning mode on/off"
        )
        print(
            f"  {config.BOLD}/plan on{config.RESET}                Enable planning mode (read-only)"
        )
        print(
            f"  {config.BOLD}/plan off{config.RESET}               Disable planning mode (read-write)"
        )
        print(
            f"  {config.BOLD}/plan start{config.RESET}             Enable planning mode (alias)"
        )
        print(
            f"  {config.BOLD}/plan end{config.RESET}               Disable planning mode (alias)"
        )
        print(
            f"  {config.BOLD}/plan true{config.RESET}              Enable planning mode (alias)"
        )
        print(
            f"  {config.BOLD}/plan false{config.RESET}             Disable planning mode (alias)"
        )
        print(
            f"  {config.BOLD}/plan 1{config.RESET}                 Enable planning mode (alias)"
        )
        print(
            f"  {config.BOLD}/plan 0{config.RESET}                 Disable planning mode (alias)"
        )
        print(
            f"  {config.BOLD}/plan focus{config.RESET}             Create new session focused on last assistant message"
        )
        print(
            f"  {config.BOLD}/plan help{config.RESET}              Show this help message"
        )

        print(f"\n{config.GREEN}Description:{config.RESET}")
        print("  Planning mode provides read-only access to explore and analyze")
        print("  your codebase without making changes. When planning mode is")
        print("  enabled, destructive tools like write_file are disabled.")

        print(f"\n{config.GREEN}Focus Subcommand:{config.RESET}")
        print(
            f"  The {config.BOLD}/plan focus{config.RESET} command creates a new session with the"
        )
        print("  last assistant message transformed into a user message.")
        print("  This is useful when the AI provides a good plan and you want")
        print("  to start a fresh session focused entirely on that plan.")

        print(f"\n{config.YELLOW}Current Status:{config.RESET}")
        print(f"  {planning_mode.get_status_text()}")

        return False, False

    def _handle_focus_command(self) -> Tuple[bool, bool]:
        """Handle the focus subcommand to create a new session with the last assistant message."""
        from ..utils import imsg, emsg

        # Get the last assistant message from the current session
        last_assistant_message = self._get_last_assistant_message()

        if not last_assistant_message:
            emsg(
                "\n*** No assistant message found to focus on. Make sure you have received a response from the AI first."
            )
            return False, False

        # Create a new session
        self.app.message_history.reset_session()
        imsg("\n*** New session created...")

        # Add the last assistant message content as a user message in the new session
        message_content = last_assistant_message.get("content", "")
        if message_content:
            self.app.message_history.add_user_message(message_content)
            imsg(
                f"*** Focused on previous assistant message: {message_content[:100]}{'...' if len(message_content) > 100 else ''}"
            )
        else:
            # If no content, add a placeholder
            self.app.message_history.add_user_message(
                "Focus on previous assistant response"
            )
            imsg("*** Focused on previous assistant response (no content available)")

        return False, False

    def _get_last_assistant_message(self) -> dict:
        """Get the last assistant message from the current message history."""
        messages = self.app.message_history.messages

        # Iterate backwards through messages to find the last assistant message
        for message in reversed(messages):
            if message.get("role") == "assistant":
                return message

        return None
