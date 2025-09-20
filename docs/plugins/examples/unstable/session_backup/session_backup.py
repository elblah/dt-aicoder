"""
Session Backup Plugin Example

This plugin automatically backs up the session every N messages or at regular intervals.
It also adds a '/backup' command to manually trigger a backup.
"""

import os
import json
import time
from datetime import datetime
from aicoder.command_handlers import CommandHandler
from aicoder.message_history import MessageHistory

# Configuration
BACKUP_INTERVAL = 10  # Backup every 10 messages
AUTO_BACKUP_ENABLED = True
BACKUP_DIR = "backups"


class SessionBackupManager:
    def __init__(self):
        self.message_count = 0
        self.last_backup_time = time.time()
        self.ensure_backup_dir()

    def ensure_backup_dir(self):
        """Ensure backup directory exists."""
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

    def should_backup(self):
        """Check if we should create a backup."""
        if not AUTO_BACKUP_ENABLED:
            return False

        current_time = time.time()
        time_since_last = current_time - self.last_backup_time

        # Backup every N messages or every 5 minutes (whichever comes first)
        return (self.message_count >= BACKUP_INTERVAL) or (time_since_last > 300)

    def create_backup(self, message_history, stats):
        """Create a backup of the current session."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"session_backup_{timestamp}.json")

            backup_data = {
                "messages": message_history.messages if message_history else [],
                "stats": {
                    "api_requests": getattr(stats, "api_requests", 0),
                    "api_success": getattr(stats, "api_success", 0),
                    "api_errors": getattr(stats, "api_errors", 0),
                    "api_time_spent": getattr(stats, "api_time_spent", 0),
                    "tool_calls": getattr(stats, "tool_calls", 0),
                    "tool_errors": getattr(stats, "tool_errors", 0),
                    "tool_time_spent": getattr(stats, "tool_time_spent", 0),
                    "messages_sent": getattr(stats, "messages_sent", 0),
                    "compactions": getattr(stats, "compactions", 0),
                }
                if stats
                else {},
                "timestamp": timestamp,
                "backup_reason": "automatic"
                if self.message_count >= BACKUP_INTERVAL
                else "time_based",
            }

            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, default=str)

            print(f"✅ Session backed up to {backup_file}")

            # Reset counter
            self.message_count = 0
            self.last_backup_time = time.time()

            return backup_file

        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return None


# Global backup manager
backup_manager = SessionBackupManager()

# Store original methods
_original_add_user_message = MessageHistory.add_user_message
_original_add_assistant_message = MessageHistory.add_assistant_message
_original_add_tool_results = MessageHistory.add_tool_results


def tracked_add_user_message(self, content):
    """Track user messages for backup purposes."""
    backup_manager.message_count += 1

    # Check if we should backup
    if backup_manager.should_backup() and hasattr(self, "api_handler"):
        backup_manager.create_backup(self, self.api_handler.stats)

    # Call original method
    return _original_add_user_message(self, content)


def tracked_add_assistant_message(self, message):
    """Track assistant messages for backup purposes."""
    backup_manager.message_count += 1

    # Check if we should backup
    if backup_manager.should_backup() and hasattr(self, "api_handler"):
        backup_manager.create_backup(self, self.api_handler.stats)

    # Call original method
    return _original_add_assistant_message(self, message)


def tracked_add_tool_results(self, tool_results):
    """Track tool results for backup purposes."""
    backup_manager.message_count += len(tool_results)

    # Check if we should backup
    if backup_manager.should_backup() and hasattr(self, "api_handler"):
        backup_manager.create_backup(self, self.api_handler.stats)

    # Call original method
    return _original_add_tool_results(self, tool_results)


# Monkey patch the methods
MessageHistory.add_user_message = tracked_add_user_message
MessageHistory.add_assistant_message = tracked_add_assistant_message
MessageHistory.add_tool_results = tracked_add_tool_results


def backup_command(self, args):
    """Manually trigger a session backup."""
    try:
        if not hasattr(self, "message_history") or not hasattr(self, "stats"):
            return "❌ Cannot create backup - missing session data"

        backup_file = backup_manager.create_backup(self.message_history, self.stats)
        if backup_file:
            return f"✅ Session manually backed up to {backup_file}"
        else:
            return "❌ Failed to create manual backup"
    except Exception as e:
        return f"❌ Error during manual backup: {e}"


# Add the new command
CommandHandler.backup = backup_command

print("✅ Session backup plugin loaded - automatic backups enabled")
print(f"   - Backup every {BACKUP_INTERVAL} messages")
print(f"   - Backup directory: {BACKUP_DIR}")
print("   - Use '/backup' to manually trigger a backup")
