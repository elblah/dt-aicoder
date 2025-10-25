"""
Memory command for AI Coder.
"""

import os
import json
import tempfile
import subprocess
from typing import Tuple, List
from .base import BaseCommand
from .. import config
from ..utils import estimate_messages_tokens, wmsg, imsg, emsg


class MemoryCommand(BaseCommand):
    """Opens $EDITOR to write the memory."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/memory", "/m"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Execute memory command with subcommands."""
        if not args:
            # Default behavior: open editor
            return self._open_editor()
        
        subcommand = args[0].lower()
        
        if subcommand in ["estimate", "est", "tokens"]:
            return self._estimate_tokens()
        elif subcommand in ["help", "-h", "--help"]:
            self._show_help()
        elif subcommand in ["edit", "e"]:
            return self._open_editor()
        else:
            wmsg(f"*** Unknown subcommand: {subcommand}")
            self._show_help()
        
        return False, False

    def _estimate_tokens(self) -> Tuple[bool, bool]:
        """Estimate tokens in current session data."""
        try:
            messages = self.app.message_history.messages
            estimated_tokens = estimate_messages_tokens(messages)
            
            imsg(f"\n>>> Session token estimation:")
            imsg(f"    Messages: {len(messages)}")
            imsg(f"    Estimated tokens: ~{estimated_tokens}")
            
            # Additional breakdown if helpful
            if messages:
                total_chars = sum(len(msg.get("content", "")) for msg in messages)
                avg_chars = total_chars / len(messages) if messages else 0
                imsg(f"    Total characters: {total_chars}")
                imsg(f"    Average chars per message: {avg_chars:.1f}")
            
        except Exception as e:
            emsg(f"*** Error estimating tokens: {e}")
            if config.DEBUG:
                import traceback
                traceback.print_exc()
        
        return False, False

    def _open_editor(self) -> Tuple[bool, bool]:
        """Opens $EDITOR to write the memory."""
        editor = os.environ.get("EDITOR", "vim")
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+", delete=False, suffix=".md"
            ) as tf:
                temp_filename = tf.name
                json.dump(self.app.message_history.messages, tf.file, indent=4)

            # Try tmux popup first, fallback to normal editor
            if not self._run_editor_in_tmux_popup(editor, temp_filename):
                subprocess.run([editor, temp_filename], check=True)

            with open(temp_filename, "r") as tf:
                content = tf.read()

            os.unlink(temp_filename)

            if not content.strip():
                wmsg("\n*** Edit cancelled, no content.")
                return False, False

            imsg("\n>>> Memory updated...")
            self.app.message_history.messages = json.loads(content)

            # Re-estimate tokens since memory content changed
            try:
                estimated_tokens = estimate_messages_tokens(
                    self.app.message_history.messages
                )
                print(
                    f"{config.BLUE}>>> Context re-estimated: ~{estimated_tokens} tokens{config.RESET}"
                )
            except Exception as e:
                if config.DEBUG:
                    print(
                        f"{config.RED} *** Error re-estimating tokens: {e}{config.RESET}"
                    )

            return False, False

        except Exception as e:
            emsg(f"\n*** Error during edit: {e}")
            return False, False

    def _show_help(self):
        """Show help for memory command."""
        imsg("Memory command usage:")
        imsg("  /memory                       - Open editor to edit memory (default)")
        imsg("  /memory edit                  - Open editor to edit memory")
        imsg("  /memory estimate               - Estimate tokens in current session")
        imsg("  /memory help                   - Show this help message")
        imsg("")
        imsg("Aliases:")
        imsg("  /m, /memory")
        imsg("")
        imsg("Examples:")
        imsg("  /memory                       - Edit memory")
        imsg("  /memory estimate               - Show token estimation")
        imsg("  /m estimate                   - Show token estimation (short form)")
        imsg("")
        imsg("Note: The estimate command analyzes your current session data")
        imsg("      and provides a token count approximation.")

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
