"""
Export History Plugin Example

This plugin adds a '/export' command to save conversation history.
"""

import json
import os
from datetime import datetime
from aicoder.command_handlers import CommandHandler


def export_history_command(self, args):
    """Export conversation history to a file."""
    try:
        # Get filename from args or use default
        if args.strip():
            filename = args.strip()
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_export_{timestamp}.json"

        # Ensure filename ends with .json
        if not filename.endswith(".json"):
            filename += ".json"

        # Get the full path in current directory
        filepath = os.path.join(os.getcwd(), filename)

        # Export messages
        messages = (
            self.message_history.messages if hasattr(self, "message_history") else []
        )

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)

        return f"✅ Conversation history exported to {filepath}"

    except Exception as e:
        return f"❌ Failed to export history: {e}"


# Add the new command
CommandHandler.export = export_history_command

print("✅ Export history plugin loaded - use '/export [filename]' to save conversation")
