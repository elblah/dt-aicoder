"""
Animator for AI Coder - handles animated status messages and cursor management.
"""

import sys
import time
import threading

from . import config
from .terminal_manager import is_esc_pressed

class Animator:
    """Handles animated status messages with elapsed time and cursor management."""
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Check if already initialized (singleton pattern)
        if hasattr(self, '_initialized'):
            return
            
        self._stop_event = None
        self._animation_thread = None
        self._cursor_thread = None
        self._cursor_stop_event = None
        self._start_time = None
        self._user_cancelled = False
        self._cursor_visible = True
        self._is_streaming = False
        self._line_width = "\r" + " " * 60 + "\r"
        
        self._initialized = True

    def start_animation(self, message=""):
        """Start a non-blocking animation thread with elapsed time."""
        self.stop_animation()

        self._stop_event = threading.Event()
        self._start_time = time.time()
        self._user_cancelled = False
        self._cursor_visible = True

        def animate():
            try:
                while not self._stop_event.is_set():
                    elapsed = time.time() - self._start_time

                    # Toggle cursor visibility as part of animation
                    if self._cursor_visible:
                        cursor_code = "\033[?25h"  # Show cursor
                    else:
                        cursor_code = "\033[?25l"  # Hide cursor

                    sys.stdout.write(
                        f"\r{config.RESET}{config.BOLD}{message} {int(elapsed)}s (ESC cancel){config.RESET}{cursor_code}"
                    )
                    sys.stdout.flush()

                    self._cursor_visible = not self._cursor_visible

                    # Sleep for 0.5 seconds, but check for stop event every 0.1 seconds
                    for _ in range(5):
                        if self._stop_event.is_set():
                            break
                        time.sleep(0.1)
            finally:
                self.ensure_cursor_visible()

        self._animation_thread = threading.Thread(target=animate, daemon=True)
        self._animation_thread.start()

    def stop_animation(self):
        """Stop the animation thread and clear the line."""
        if self._stop_event:
            self._stop_event.set()

        if self._animation_thread and self._animation_thread.is_alive():
            self._animation_thread.join()

        sys.stdout.write(self._line_width)
        self.ensure_cursor_visible()
        self._start_time = None

    def start_cursor_blinking(self):
        """Start blinking cursor during streaming (when no animation is shown)."""
        # Stop any existing cursor blinking
        self.stop_cursor_blinking()

        self._is_streaming = True
        self._cursor_stop_event = threading.Event()

        def blink_cursor():
            visible = True
            # Keep a local reference to avoid race conditions
            stop_event = self._cursor_stop_event
            try:
                while stop_event and not stop_event.is_set():
                    if visible:
                        sys.stdout.write("\033[?25h")  # Show cursor
                    else:
                        sys.stdout.write("\033[?25l")  # Hide cursor
                    sys.stdout.flush()
                    visible = not visible
                    time.sleep(0.5)  # Blink every 0.5 seconds
            except Exception:
                # Silently handle errors to avoid thread exceptions bubbling up
                # This can happen if the terminal is closed or during rapid cleanup
                pass
            finally:
                self.ensure_cursor_visible()

        self._cursor_thread = threading.Thread(target=blink_cursor, daemon=True)
        self._cursor_thread.start()

    def stop_cursor_blinking(self):
        """Stop cursor blinking and ensure cursor is visible."""
        self._is_streaming = False

        # Signal the thread to stop
        if self._cursor_stop_event:
            self._cursor_stop_event.set()

        self.ensure_cursor_visible(stop_blinking=False)

        # Wait for the thread to actually stop
        if self._cursor_thread and self._cursor_thread.is_alive():
            try:
                self._cursor_thread.join(timeout=3.0)
            except Exception:
                pass

        # Clean up only after thread has stopped
        self._cursor_stop_event = None
        self._cursor_thread = None
        self.ensure_cursor_visible(stop_blinking=False)

    def check_user_cancel(self):
        """Check if user has pressed ESC to cancel during animation."""
        if is_esc_pressed():
            self._user_cancelled = True
            return True
        return self._user_cancelled

    def user_cancelled(self):
        """Check if user has cancelled the operation."""
        return self._user_cancelled

    def ensure_cursor_visible(self, stop_blinking=True):
        """Ensure cursor is visible."""
        if stop_blinking:
            self.stop_cursor_blinking()
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


def get_animator():
    """Get the singleton animator instance."""
    return Animator()
