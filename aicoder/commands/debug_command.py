"""
Debug command for AI Coder.
"""

import os
from typing import Tuple, List
from .base import BaseCommand
from .. import config
from ..utils import imsg, wmsg


class DebugCommand(BaseCommand):
    """Manage debug mode: /debug [on|off] - Show or toggle debug logging for streaming issues."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/debug", "/d"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Manage debug mode: /debug [on|off] - Show or toggle debug logging for streaming issues."""
        # Check current debug state
        current_debug = os.environ.get("DEBUG", "") == "1"
        current_stream_log = os.environ.get("STREAM_LOG_FILE", "")

        if not args:
            # Show current status
            status = "enabled" if current_debug and current_stream_log else "disabled"
            imsg(f"\n*** Debug logging is {status}")
            if current_debug and current_stream_log:
                print("    - DEBUG mode: ON")
                print(f"    - Stream logging: {current_stream_log}")
            return False, False

        arg = args[0].lower()
        if arg in ["on", "enable", "1", "true"]:
            if current_debug and current_stream_log:
                print(
                    f"\n{config.GREEN}*** Debug logging is already enabled{config.RESET}"
                )
                print("    - DEBUG mode: ON")
                print(f"    - Stream logging: {current_stream_log}")
                return False, False

            # Enable debug logging
            os.environ["DEBUG"] = "1"
            os.environ["STREAM_LOG_FILE"] = "stream_debug.log"

            # Also set longer timeouts to avoid false timeouts during debugging
            os.environ["STREAMING_TIMEOUT"] = "600"
            os.environ["STREAMING_READ_TIMEOUT"] = "120"
            os.environ["HTTP_TIMEOUT"] = "600"

            # Force re-initialization of streaming adapter to pick up new debug settings
            if hasattr(self.app, "_streaming_adapter"):
                delattr(self.app, "_streaming_adapter")
                print("    - Streaming adapter reset to pick up debug settings")

            imsg(f"\n*** Debug logging enabled")
            print("    - DEBUG mode: ON")
            print("    - Stream logging: stream_debug.log")
            print("    - Streaming timeout: 600s")
            print("    - Read timeout: 120s")
            print("    - HTTP timeout: 600s")
            wmsg(f"*** Run /retry or make a request to capture debug data.")

        elif arg in ["off", "disable", "0", "false"]:
            if not current_debug:
                print(
                    f"\n{config.GREEN}*** Debug logging is already disabled{config.RESET}"
                )
                return False, False

            # Disable debug logging
            os.environ.pop("DEBUG", None)
            os.environ.pop("STREAM_LOG_FILE", None)
            os.environ.pop("STREAMING_TIMEOUT", None)
            os.environ.pop("STREAMING_READ_TIMEOUT", None)
            os.environ.pop("HTTP_TIMEOUT", None)

            # Force re-initialization of streaming adapter to pick up new debug settings
            if hasattr(self.app, "_streaming_adapter"):
                delattr(self.app, "_streaming_adapter")
                print("    - Streaming adapter reset to disable debug settings")

            imsg(f"\n*** Debug logging disabled")
            print("    - DEBUG mode: OFF")
            print("    - Stream logging: OFF")

        else:
            print(
                f"\n{config.RED}*** Invalid argument. Use: /debug [on|off]{config.RESET}"
            )

        return False, False
