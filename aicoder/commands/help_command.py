"""
Help command for AI Coder.
"""

from typing import Tuple, List
from .base import BaseCommand


class HelpCommand(BaseCommand):
    """Displays help message."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/help"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Displays help message."""
        print("\nAvailable commands:")

        # Group commands by handler using the centralized registry
        command_map = {}
        for command, handler in sorted(self.app.command_handlers.items()):
            if handler not in command_map:
                command_map[handler] = []
            command_map[handler].append(command)

        command_groups = [", ".join(cmds) for cmds in command_map.values()]
        max_len = max(len(group) for group in command_groups) if command_groups else 0

        for handler, cmds in command_map.items():
            aliases = ", ".join(cmds)
            # Get docstring from the handler function
            docstring = handler.__doc__ or "No description available."
            print(f"  {aliases.ljust(max_len)}   {docstring}")

        return False, False
