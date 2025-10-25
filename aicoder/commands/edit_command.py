"""
Edit command for AI Coder.
"""

import os
import tempfile
import subprocess
from typing import Tuple, List
from .base import BaseCommand
from .. import config
from ..utils import wmsg, imsg, emsg


class EditCommand(BaseCommand):
    """Opens $EDITOR to write a prompt."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/edit", "/e"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Opens $EDITOR to write a prompt."""
        editor = os.environ.get("EDITOR", "vim")
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+", delete=False, suffix=".md"
            ) as tf:
                temp_filename = tf.name

            # Try tmux popup first, fallback to normal editor
            if not self._run_editor_in_tmux_popup(editor, temp_filename):
                subprocess.run([editor, temp_filename], check=True)

            with open(temp_filename, "r") as tf:
                content = tf.read()

            os.unlink(temp_filename)

            if not content.strip():
                wmsg("\n*** Edit cancelled, no content.")
                return False, False

            imsg("\n>>> Using edited prompt...")
            print(content)
            self.app.message_history.add_user_message(content)

            # Also save the edited content to prompt history
            try:
                from ..readline_history_manager import prompt_history_manager

                prompt_history_manager.save_user_input(content)
            except Exception:
                # Silently fail if history saving fails
                pass

            return False, True

        except Exception as e:
            emsg(f"\n*** Error during edit: {e}")
            return False, False

    def _run_editor_in_tmux_popup(self, editor: str, file_path: str) -> bool:
        """
        Run editor in tmux popup if available and enabled, otherwise run normally.

        Args:
            editor: Editor command
            file_path: Path to the file to edit

        Returns:
            True if tmux popup was used, False otherwise
        """
        # Check if we're in tmux and popup editor is enabled
        in_tmux = os.environ.get("TMUX") is not None
        popup_enabled = getattr(config, "ENABLE_TMUX_POPUP_EDITOR", True)

        if not (in_tmux and popup_enabled):
            return False

        try:
            # Get current terminal dimensions
            try:
                terminal_width = os.get_terminal_size().columns
                terminal_height = os.get_terminal_size().lines
            except (OSError, AttributeError):
                # Fallback dimensions if terminal size detection fails
                terminal_width = 120
                terminal_height = 30

            # Calculate popup dimensions based on percentage
            width_percent = getattr(config, "TMUX_POPUP_WIDTH_PERCENT", 80)
            height_percent = getattr(config, "TMUX_POPUP_HEIGHT_PERCENT", 80)

            popup_width = max(40, int(terminal_width * width_percent / 100))
            popup_height = max(10, int(terminal_height * height_percent / 100))

            # Build tmux popup command with calculated dimensions
            popup_cmd = f'tmux display-popup -w {popup_width} -h {popup_height} -E "{editor} {file_path}"'

            if config.DEBUG:
                print(
                    f"{config.GREEN}*** Using tmux popup: {popup_width}x{popup_height} ({width_percent}% of {terminal_width}x{terminal_height}){config.RESET}"
                )

            subprocess.run(popup_cmd, shell=True, check=True)
            return True
        except Exception as e:
            if config.DEBUG:
                wmsg(f"*** Tmux popup failed, falling back to normal editor: {e}")
            # Fall through to normal editor

        return False
