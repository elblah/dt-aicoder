"""
Command handlers for AI Coder.
"""

from typing import Tuple
from .utils import emsg


class CommandHandlerMixin:
    """Mixin class for command handling."""

    def _handle_command(self, user_input: str) -> Tuple[bool, bool]:
        """Handle command input and return (should_quit, run_api_call)."""
        parts = user_input.split()
        command = parts[0].lower()
        args = parts[1:]

        # Use the centralized command registry
        handler = self.command_handlers.get(command)
        if not handler:
            emsg(f"\n *** Command not found: {command}")
            return False, False
            
        return handler(args)