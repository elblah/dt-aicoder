"""
Stats command for AI Coder.
"""

from typing import Tuple, List
from .base import BaseCommand


class StatsCommand(BaseCommand):
    """Displays session statistics."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/stats"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Displays session statistics."""
        # Use the stats object to print statistics, passing message history for context
        self.app.stats.print_stats(self.app.message_history)
        return False, False
