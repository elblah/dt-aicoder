"""
Load session command for AI Coder.
"""

import os
from typing import Tuple, List
from .base import BaseCommand


class LoadSessionCommand(BaseCommand):
    """Loads a session from a file."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/load"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Loads a session from a file."""
        fname = args[0] if args else "session.json"
        # Expand ~ to home directory
        fname = os.path.expanduser(fname)
        self.app.message_history.load_session(fname)
        return False, False
