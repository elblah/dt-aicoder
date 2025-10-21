"""
Centralized terminal and input management for AI Coder.
Handles ESC key detection, terminal modes, and input state management.
"""

import sys
import termios
import select
import threading
import time
from typing import Optional


class TerminalManager:
    """Centralized terminal and input management singleton."""

    _instance: Optional["TerminalManager"] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Check if we're in test mode (disable terminal operations)
        import os

        self._test_mode = os.environ.get("TEST_MODE") == "1"

        # ESC detection state
        self._esc_pressed = False
        self._esc_timestamp = 0

        # ESC monitoring state
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()

        # Terminal state management
        self._in_prompt_mode = False
        self._terminal_lock = threading.Lock()

        # Store original terminal settings
        self._original_settings = None
        if not self._test_mode:
            try:
                self._original_settings = termios.tcgetattr(sys.stdin)
            except (OSError, termios.error):
                self._original_settings = None

        # Initialize monitoring (no terminal setup yet)
        if not self._test_mode:
            self._start_monitoring()
        self._initialized = True

    def _start_monitoring(self):
        """Start the background thread for ESC key monitoring."""
        if self._monitor_thread is not None:
            return

        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_esc_keys, daemon=True
        )
        self._monitor_thread.start()

    def _monitor_esc_keys(self):
        """Background thread that monitors stdin for ESC key presses."""
        # The terminal state should be managed by enter/exit_prompt_mode methods
        # This thread just reads input for ESC detection

        while not self._stop_monitoring.wait(0.05):  # Check every 50ms
            # Try to acquire lock with timeout to avoid blocking prompts
            if not self._terminal_lock.acquire(timeout=0.02):
                continue

            try:
                # Don't do any monitoring work during prompt mode to avoid interference
                if self._in_prompt_mode:
                    continue

                # Only check for ESC when we're not in prompt mode
                # Use select to check if there's data available without blocking
                ready, _, _ = select.select(
                    [sys.stdin], [], [], 0.001
                )  # Very short timeout
                if not ready:
                    continue

                # Read ALL available data (this is the correct approach)
                data = sys.stdin.read()

                # Check if we got an ESC character and distinguish from escape sequences
                if data and data[0] == "\x1b":  # ESC character
                    if len(data) == 1:
                        # Lone ESC detected (not an escape sequence)
                        self._esc_pressed = True
                        self._esc_timestamp = time.time()
                    # else: It's an escape sequence (arrow key, function key, etc.), ignore it

            except Exception:
                continue
            finally:
                self._terminal_lock.release()

    def enter_prompt_mode(self):
        """Enter prompt mode - restore normal terminal settings for user input."""
        with self._terminal_lock:
            if self._in_prompt_mode:
                return  # Already in prompt mode

            # Clear any pending ESC state before showing prompt
            self._esc_pressed = False
            self._esc_timestamp = 0

            # Skip terminal operations in test mode
            if self._test_mode:
                self._in_prompt_mode = True
                return

            # Restore normal terminal settings for proper input
            if self._original_settings:
                try:
                    termios.tcsetattr(
                        sys.stdin, termios.TCSADRAIN, self._original_settings
                    )
                except (OSError, termios.error):
                    pass  # Best effort

            self._in_prompt_mode = True

    def exit_prompt_mode(self):
        """Exit prompt mode - prepare for non-blocking operations if needed."""
        with self._terminal_lock:
            if not self._in_prompt_mode:
                return  # Not in prompt mode

            # Skip terminal operations in test mode
            if self._test_mode:
                self._in_prompt_mode = False
                return

            # Set terminal to cbreak mode for ESC detection when not in prompt mode
            try:
                new_settings = termios.tcgetattr(sys.stdin)
                new_settings[3] &= ~termios.ICANON  # Disable canonical mode
                new_settings[3] &= ~termios.ECHO  # Disable echo
                new_settings[6][termios.VMIN] = 0  # Don't require minimum characters
                new_settings[6][termios.VTIME] = 0  # Don't wait for characters
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new_settings)
            except (OSError, termios.error):
                pass  # Best effort

            self._in_prompt_mode = False

    def is_esc_pressed(self) -> bool:
        """Check if ESC key has been pressed since last reset."""
        # with self._terminal_lock:
        return self._esc_pressed

    def reset_esc_state(self):
        """Reset the ESC pressed state."""
        with self._terminal_lock:
            self._esc_pressed = False
            self._esc_timestamp = 0

    def get_esc_timestamp(self) -> float:
        """Get the timestamp when ESC was last pressed."""
        # with self._terminal_lock:
        return self._esc_timestamp

    def _perform_terminal_reset(self, silent: bool = False):
        """Perform a terminal reset using 'stty sane'."""
        try:
            import subprocess

            # Run 'sttx sane' to reset terminal settings
            result = subprocess.run(["stty", "sane"], capture_output=True, timeout=5)
            if result.returncode == 0:
                # Only show feedback if not silent
                if not silent:
                    # Ensure terminal is in a usable state and show feedback
                    import sys

                    sys.stdout.write("\r[K[Ctrl+G] Terminal reset completed\r\n")
                    sys.stdout.flush()
            else:
                # Only show feedback if not silent
                if not silent:
                    import sys

                    sys.stdout.write("\r[K[Ctrl+G] Terminal reset failed\r\n")
                    sys.stdout.flush()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # Fallback if stty is not available or fails
            # Only show feedback if not silent
            if not silent:
                import sys

                sys.stdout.write("\r[K[Ctrl+G] Terminal reset unavailable\r\n")
                sys.stdout.flush()

    def setup_for_non_prompt_input(self):
        """Setup terminal for non-prompt input (animations, streaming, etc.)."""
        self.exit_prompt_mode()  # Same implementation

    def cleanup(self):
        """Clean up resources and restore terminal settings."""
        # Skip terminal operations in test mode
        if self._test_mode:
            return

        # Stop monitoring thread
        if self._monitor_thread is not None:
            self._stop_monitoring.set()
            self._monitor_thread.join(timeout=1.0)
            self._monitor_thread = None

        # Restore original terminal settings if available
        # This ensures we always exit with a properly configured terminal
        if self._original_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._original_settings)
            except (OSError, termios.error):
                pass  # Best effort

    def __del__(self):
        """Ensure cleanup on object destruction."""
        self.cleanup()


# Global instance for easy access
_terminal_manager: Optional[TerminalManager] = None


def get_terminal_manager() -> TerminalManager:
    """Get the global terminal manager instance."""
    global _terminal_manager
    if _terminal_manager is None:
        _terminal_manager = TerminalManager()
        # Register cleanup function to be called on exit
        import atexit

        atexit.register(cleanup_terminal_manager)
    return _terminal_manager


def is_esc_pressed() -> bool:
    """Convenience function to check if ESC key was pressed."""
    return get_terminal_manager().is_esc_pressed()


def reset_esc_state():
    """Convenience function to reset ESC state."""
    get_terminal_manager().reset_esc_state()


def enter_prompt_mode():
    """Convenience function to enter prompt mode."""
    get_terminal_manager().enter_prompt_mode()


def exit_prompt_mode():
    """Convenience function to exit prompt mode."""
    get_terminal_manager().exit_prompt_mode()


def setup_for_non_prompt_input():
    """Convenience function to setup for non-prompt input."""
    get_terminal_manager().setup_for_non_prompt_input()


def cleanup_terminal_manager():
    """Convenience function to cleanup terminal manager."""
    global _terminal_manager
    if _terminal_manager is not None:
        _terminal_manager.cleanup()
        _terminal_manager = None


# Note: Terminal manager is NOT auto-initialized to avoid breaking unit tests
# It will be initialized lazily when first needed
