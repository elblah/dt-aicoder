"""
Save session command for AI Coder.
"""

import os
from typing import Tuple, List
from .base import BaseCommand


class SaveSessionCommand(BaseCommand):
    """Saves the current session to a file."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/save"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Saves the current session to a file."""
        fname = args[0] if args else "session.json"
        # Expand ~ to home directory
        fname = os.path.expanduser(fname)
        self.app.message_history.save_session(fname)
        return False, False
