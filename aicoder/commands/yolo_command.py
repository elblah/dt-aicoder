"""
Yolo command for AI Coder.
"""

import os
from typing import Tuple, List
from .base import BaseCommand
from .. import config
from ..utils import imsg


class YoloCommand(BaseCommand):
    """Manage YOLO mode: /yolo [on|off] - Show or toggle YOLO mode."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/yolo"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Manage YOLO mode: /yolo [on|off] - Show or toggle YOLO mode."""
        import aicoder.config

        if not args:
            # Show current status
            status = "enabled" if aicoder.config.YOLO_MODE else "disabled"
            imsg(f"\n*** YOLO mode is {status}")
            return False, False

        arg = args[0].lower()
        if arg in ["on", "enable", "1", "true"]:
            # Enable YOLO mode
            os.environ["YOLO_MODE"] = "1"
            aicoder.config.YOLO_MODE = True
            imsg(f"\n*** YOLO mode enabled")
        elif arg in ["off", "disable", "0", "false"]:
            # Disable YOLO mode
            os.environ["YOLO_MODE"] = "0"
            aicoder.config.YOLO_MODE = False
            imsg(f"\n*** YOLO mode disabled")
        else:
            print(
                f"\n{config.RED}*** Invalid argument. Use: /yolo [on|off]{config.RESET}"
            )

        return False, False
