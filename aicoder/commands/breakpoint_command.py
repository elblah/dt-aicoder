"""
Breakpoint command for AI Coder.
"""

from typing import Tuple, List
from .base import BaseCommand


class BreakpointCommand(BaseCommand):
    """Enters the debugger."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/breakpoint", "/bp"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Enters the debugger."""
        breakpoint()
        return False, False
