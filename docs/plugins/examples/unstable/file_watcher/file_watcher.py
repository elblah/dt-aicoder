"""
File Watcher Plugin Example

This plugin watches for file changes in the current directory and notifies the AI
about important changes. It's useful for development workflows where the AI needs
to be aware of code changes.
"""

import time
import threading
from pathlib import Path
from aicoder.app import AICoder
from aicoder.command_handlers import CommandHandler

# Configuration
WATCHED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".json",
    ".md",
}
WATCH_INTERVAL = 5  # seconds


class FileWatcher:
    def __init__(self):
        self.watched_files = {}
        self.running = False
        self.thread = None
        self.message_history = None

    def set_message_history(self, message_history):
        """Set the message history to send notifications to."""
        self.message_history = message_history

    def start_watching(self):
        """Start the file watching thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        print("✅ File watcher started")

    def stop_watching(self):
        """Stop the file watching thread."""
        self.running = False
        if self.thread:
            self.thread.join()
        print("⏹️ File watcher stopped")

    def _watch_loop(self):
        """Main watching loop."""
        while self.running:
            try:
                self._check_files()
                time.sleep(WATCH_INTERVAL)
            except Exception as e:
                if self.running:  # Only print if we're still supposed to be running
                    print(f"⚠️ File watcher error: {e}")

    def _check_files(self):
        """Check for file changes."""
        try:
            current_dir = Path(".")
            changes = []

            for file_path in current_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix in WATCHED_EXTENSIONS:
                    stat = file_path.stat()
                    mtime = stat.st_mtime

                    rel_path = str(file_path.relative_to(current_dir))

                    if rel_path not in self.watched_files:
                        # New file
                        self.watched_files[rel_path] = mtime
                        changes.append(f"🆕 New file created: {rel_path}")
                    elif self.watched_files[rel_path] != mtime:
                        # Modified file
                        self.watched_files[rel_path] = mtime
                        changes.append(f"✏️ File modified: {rel_path}")

            # Notify about changes
            if changes and self.message_history:
                notification = {
                    "role": "system",
                    "content": "File System Notification:\n" + "\n".join(changes),
                }
                self.message_history.messages.append(notification)

                # Print to console as well
                for change in changes:
                    print(f"📁 {change}")

        except Exception as e:
            print(f"⚠️ File check error: {e}")


# Global file watcher instance
file_watcher = FileWatcher()

# Hook into app initialization to start watching
# Store original method
_original_init = AICoder.__init__


def watched_init(self):
    """Initialize the app and start file watching."""
    # Call original init
    _original_init(self)

    # Set message history and start watching
    file_watcher.set_message_history(self.message_history)
    file_watcher.start_watching()


# Monkey patch
AICoder.__init__ = watched_init


def watch_command(self, args):
    """Control file watching."""
    if not args or args.strip().lower() in ["start", "on"]:
        if not file_watcher.running:
            file_watcher.start_watching()
            return "✅ File watching started"
        else:
            return "ℹ️ File watching is already running"
    elif args.strip().lower() in ["stop", "off"]:
        if file_watcher.running:
            file_watcher.stop_watching()
            return "⏹️ File watching stopped"
        else:
            return "ℹ️ File watching is already stopped"
    elif args.strip().lower() == "status":
        status = "running" if file_watcher.running else "stopped"
        files = len(file_watcher.watched_files)
        return f"📁 File watcher status: {status}\n   Watching {files} files"
    else:
        return "Usage: /watch [start|stop|status]"


# Add the command
CommandHandler.watch = watch_command

print("✅ File watcher plugin loaded")
print(
    "   - Watching for changes in .py, .js, .ts, .jsx, .tsx, .html, .css, .json, .md files"
)
print("   - Use '/watch start|stop|status' to control the watcher")
