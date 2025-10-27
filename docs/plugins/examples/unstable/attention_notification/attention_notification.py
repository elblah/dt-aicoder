"""
Attention Notification Plugin Example

This plugin notifies you when the AI needs your attention, such as when:
- An approval prompt is shown
- The user prompt is available for typing
- Long-running operations are completed

The plugin can send desktop notifications and/or play sounds to get your attention.
"""

import sys
from aicoder.tool_manager.approval_system import ApprovalSystem
from aicoder.app import AICoder
from aicoder.command_handlers import CommandHandler

# Configuration
NOTIFICATION_METHODS = {
    "desktop": True,  # Send desktop notifications
    "sound": True,  # Play beep sounds
    "terminal": True,  # Highlight terminal output
}

# Try to import notification libraries
try:
    import subprocess

    NOTIFICATION_AVAILABLE = True
except ImportError:
    NOTIFICATION_AVAILABLE = False


def send_desktop_notification(title, message):
    """Send a desktop notification."""
    if not NOTIFICATION_METHODS.get("desktop", True):
        return

    try:
        # Try different notification methods
        if sys.platform == "darwin":  # macOS
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{message}" with title "{title}"',
                ],
                check=False,
                timeout=5,
            )
        elif sys.platform.startswith("linux"):  # Linux
            subprocess.run(["notify-send", title, message], check=False, timeout=5)
        elif sys.platform == "win32":  # Windows
            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    f"New-BurntToastNotification -Text '{title}', '{message}'",
                ],
                check=False,
                timeout=5,
            )
    except Exception:
        # Silent fail if notifications aren't available
        pass


def play_sound():
    """Play a sound to get attention."""
    if not NOTIFICATION_METHODS.get("sound", True):
        return

    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(
                ["afplay", "/System/Library/Sounds/Ping.aiff"], check=False, timeout=5
            )
        elif sys.platform.startswith("linux"):  # Linux
            subprocess.run(
                ["paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"],
                check=False,
                timeout=5,
            )
        elif sys.platform == "win32":  # Windows
            import winsound

            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        # Fallback: print bell character
        try:
            print("\a", end="", flush=True)
        except Exception:
            pass


def highlight_terminal(message):
    """Highlight terminal output to get attention."""
    if not NOTIFICATION_METHODS.get("terminal", True):
        return

    try:
        # Use ANSI escape codes to make text more visible
        from aicoder.config import YELLOW, RESET

        highlighted = f"{YELLOW}[!] {message} [!]{RESET}"
        print(highlighted, file=sys.stderr)
    except Exception:
        # Fallback to regular print
        print(f"[!] {message} [!]", file=sys.stderr)


# Store original method
_original_request_approval = ApprovalSystem.request_user_approval


def notifying_request_approval(self, prompt_message, tool_name, arguments, tool_config):
    """Request user approval with attention notifications."""

    # Notify user that attention is needed
    notification_message = f"AI Coder needs your attention for {tool_name}"
    send_desktop_notification("AI Coder - Approval Needed", notification_message)
    play_sound()
    highlight_terminal("APPROVAL NEEDED - Please review the prompt above")

    # Call original method
    return _original_request_approval(
        self, prompt_message, tool_name, arguments, tool_config
    )


# Monkey patch
ApprovalSystem.request_user_approval = notifying_request_approval

# Store original method
_original_get_multiline_input = AICoder._get_multiline_input


def notifying_get_multiline_input(self):
    """Get multiline input with attention notification."""

    # Notify user that input is needed
    send_desktop_notification(
        "AI Coder - Input Ready", "AI Coder is waiting for your input"
    )
    play_sound()
    highlight_terminal("YOUR INPUT NEEDED - Please type your response above")

    # Call original method
    return _original_get_multiline_input(self)


# Monkey patch
AICoder._get_multiline_input = notifying_get_multiline_input


def notify_test_command(self, args):
    """Test the notification system."""
    try:
        send_desktop_notification("AI Coder - Test", "Notification system is working!")
        play_sound()
        highlight_terminal(
            "TEST NOTIFICATION - This is a test of the notification system"
        )
        return "[✓] Notification test completed"
    except Exception as e:
        return f"[X] Notification test failed: {e}"


# Add the command
CommandHandler.notify_test = notify_test_command

print("[✓] Attention notification plugin loaded")
print("   - Desktop notifications enabled")
print("   - Sound alerts enabled")
print("   - Terminal highlighting enabled")
print("   - Use '/notify_test' to test the notification system")
