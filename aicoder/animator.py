"""
Animator for AI Coder - handles animated status messages and cursor management.
"""

import sys
import time
import select
import threading
from datetime import timedelta

from . import config

# termios is imported conditionally for Unix systems
try:
    import termios

    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False


class Animator:
    """Handles animated status messages with elapsed time and cursor management."""

    def __init__(self):
        self._stop_event = None
        self._animation_thread = None
        self._cursor_thread = None
        self._cursor_stop_event = None
        self._start_time = None
        self._user_cancelled = False
        self._cursor_visible = True
        self._is_streaming = False

    def start_animation(self, message=""):
        """Start a non-blocking animation thread with elapsed time."""
        self.stop_animation()

        self._stop_event = threading.Event()
        self._start_time = time.time()
        self._user_cancelled = False
        self._cursor_visible = True
        chars = "|/-\\"

        def animate():
            char_index = 0
            while not self._stop_event.is_set():
                char = chars[char_index % len(chars)]
                elapsed = time.time() - self._start_time
                elapsed_str = str(timedelta(seconds=int(elapsed)))

                # Toggle cursor visibility as part of animation
                if self._cursor_visible:
                    cursor_code = "\033[?25h"  # Show cursor
                else:
                    cursor_code = "\033[?25l"  # Hide cursor

                sys.stdout.write(
                    f"\r{config.RESET}{config.BOLD}{message} {char} {int(elapsed)}s (ESC cancel){config.RESET}{cursor_code}"
                )
                sys.stdout.flush()

                self._cursor_visible = not self._cursor_visible
                char_index += 1

                # Sleep for 0.5 seconds, but check for stop event every 0.1 seconds
                for _ in range(5):
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.1)

        self._animation_thread = threading.Thread(target=animate, daemon=True)
        self._animation_thread.start()

    def stop_animation(self):
        """Stop the animation thread and clear the line."""
        if self._stop_event:
            self._stop_event.set()

        if self._animation_thread and self._animation_thread.is_alive():
            self._animation_thread.join()

        sys.stdout.write("\r" + " " * 60 + "\r")
        # Ensure cursor is visible when animation stops
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        self._start_time = None

    def start_cursor_blinking(self):
        """Start blinking cursor during streaming (when no animation is shown)."""
        # Stop any existing cursor blinking
        self.stop_cursor_blinking()

        self._is_streaming = True
        self._cursor_stop_event = threading.Event()

        def blink_cursor():
            visible = True
            while not self._cursor_stop_event.is_set():
                if visible:
                    sys.stdout.write("\033[?25h")  # Show cursor
                else:
                    sys.stdout.write("\033[?25l")  # Hide cursor
                sys.stdout.flush()
                visible = not visible
                time.sleep(0.5)  # Blink every 0.5 seconds

        self._cursor_thread = threading.Thread(target=blink_cursor, daemon=True)
        self._cursor_thread.start()

    def stop_cursor_blinking(self):
        """Stop cursor blinking and ensure cursor is visible."""
        self._is_streaming = False

        if self._cursor_stop_event:
            self._cursor_stop_event.set()

        if self._cursor_thread and self._cursor_thread.is_alive():
            self._cursor_thread.join(timeout=1.0)

        # Ensure cursor is visible
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

        # Clean up
        self._cursor_stop_event = None
        self._cursor_thread = None

    def check_user_cancel(self):
        """Check if user has pressed ESC to cancel during animation."""
        # Save original terminal settings if available
        old_settings = None
        if HAS_TERMIOS:
            try:
                old_settings = termios.tcgetattr(sys.stdin)
                # Set terminal to non-canonical mode to read single characters
                new_settings = termios.tcgetattr(sys.stdin)
                new_settings[3] = (
                    new_settings[3] & ~termios.ICANON
                )  # Disable canonical mode
                new_settings[6][termios.VMIN] = b"\x00"  # Non-blocking read
                new_settings[6][termios.VTIME] = b"\x00"
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new_settings)
            except Exception:
                # Fall back to regular method if terminal manipulation fails
                old_settings = None

        try:
            # Use a non-blocking check with a very short timeout
            if select.select([sys.stdin], [], [], 0.01) == ([sys.stdin], [], []):
                ch = sys.stdin.read(1)
                # Check for ESC key (ASCII 27)
                if ord(ch) == 27:
                    self._user_cancelled = True
                    return True
        except Exception:
            # Handle any exceptions that might prevent ESC from working
            pass
        finally:
            # Restore original terminal settings if we changed them
            if old_settings is not None:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except Exception:
                    pass

        return self._user_cancelled

    def user_cancelled(self):
        """Check if user has cancelled the operation."""
        return self._user_cancelled

    def ensure_cursor_visible(self):
        """Ensure cursor is visible."""
        # Stop any cursor blinking
        self.stop_cursor_blinking()
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
