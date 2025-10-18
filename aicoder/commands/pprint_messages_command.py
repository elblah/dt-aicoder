"""
Pprint messages command for AI Coder.
"""

import pprint
from typing import Tuple, List
from .base import BaseCommand
from .. import config
from ..utils import wmsg


class PprintMessagesCommand(BaseCommand):
    """Prints the current message history."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/pprint_messages", "/pm"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Prints the current message history."""
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self.app.message_history.messages)

        # Also print the system prompt content if in debug mode
        if config.DEBUG and self.app.message_history.messages:
            system_prompt = self.app.message_history.messages[0].get("content", "")
            wmsg(f"\n=== SYSTEM PROMPT CONTENT ===")
            print(system_prompt)
            wmsg(f"=== END SYSTEM PROMPT ===")

        return False, False
