"""Terminal reset command"""

from typing import Tuple
from .base import BaseCommand


class ResetCommand(BaseCommand):
    """Reset terminal settings to fix display issues"""
    
    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/terminalreset", "/tr"]
    
    def execute(self, args: list[str]) -> Tuple[bool, bool]:
        """Execute the terminal reset command"""
        try:
            from ..terminal_manager import get_terminal_manager
            manager = get_terminal_manager()
            manager._perform_terminal_reset()
            from ..utils import wmsg
            wmsg("Terminal settings reset")
            return (False, False)  # Don't quit, don't run API call
        except Exception as e:
            from ..utils import emsg
            emsg(f"Terminal reset failed: {e}")
            return (False, False)  # Don't quit, don't run API call