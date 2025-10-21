"""
Retry command for AI Coder.
"""

from typing import Tuple, List
from .base import BaseCommand
from .. import config
from ..utils import wmsg, imsg


class RetryCommand(BaseCommand):
    """Retries the last API call without modifying the conversation history."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/retry", "/r"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Retries the last API call without modifying the conversation history."""
        if len(self.app.message_history.messages) < 2:
            wmsg("\n*** Not enough messages to retry.")
            return False, False

        imsg("\n*** Retrying last request...")

        # Check if debug mode is enabled and notify user
        if config.DEBUG and config.STREAM_LOG_FILE:
            wmsg(f"*** Debug mode is active - will log to: {config.STREAM_LOG_FILE}")

        # Simply resend the current context without modifying history
        return False, True
