"""
Quit command for AI Coder.
"""

from typing import Tuple, List
from .base import BaseCommand


class QuitCommand(BaseCommand):
    """Exits the application."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/quit", "/q"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Exits the application."""
        return True, False
