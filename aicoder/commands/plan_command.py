"""
Plan command for AI Coder.
"""

from typing import Tuple, List
from .base import BaseCommand
from .. import config


class PlanCommand(BaseCommand):
    """Manage planning mode: /plan [on|off|start|end|true|false|toggle] - Show or toggle planning mode."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/plan", "/plan toggle"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Manage planning mode: /plan [on|off|start|end|true|false|toggle] - Show or toggle planning mode."""
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
        else:
            print(
                f"\n{config.RED}*** Invalid argument. Use: /plan [on|off|start|end|true|false|toggle]{config.RESET}"
            )

        return False, False
