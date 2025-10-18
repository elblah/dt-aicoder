"""
Compact command for AI Coder.
"""

from typing import Tuple, List
from .base import BaseCommand
from .. import config
from ..utils import imsg, emsg, wmsg
from ..message_history import NoMessagesToCompactError


class CompactCommand(BaseCommand):
    """Forces session compaction."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/compact", "/c"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Forces session compaction."""
        try:
            self.app.message_history.compact_memory()
            imsg(f"\n ✓ Compaction completed successfully")
        except NoMessagesToCompactError:
            wmsg(
                f"\n ℹ️  Nothing to compact - all messages are recent or already compacted"
            )
        except Exception as e:
            # CRITICAL: Compaction failed - preserve user data and inform user
            emsg(f"\n ❌ Compaction failed: {str(e)}")
            wmsg(f" *** Your conversation history has been preserved.")
            wmsg(f" *** Options: Try '/compact' again, save with '/save', or continue with a new message.")
            # Reset compaction flag to allow retry
            self.app.message_history._compaction_performed = False
        return False, False
