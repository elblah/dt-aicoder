"""
New session command for AI Coder.
"""

from typing import Tuple, List
from .base import BaseCommand
from .. import config
from ..utils import imsg


class NewSessionCommand(BaseCommand):
    """Starts a new chat session."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/new"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Starts a new chat session."""
        imsg(f"\n *** New session created...")
        self.app.message_history.reset_session()
        return False, False
