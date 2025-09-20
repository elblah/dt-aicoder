#!/usr/bin/env python3
"""
Temporary test to check if the context summary plugin would work.
"""

import sys

# Add the current directory to Python path
sys.path.insert(0, ".")

# Import the message history module
from aicoder.message_history import MessageHistory

# Simulate loading the context summary plugin
print("Simulating context summary plugin loading...")

# Configuration
AUTO_SUMMARY_THRESHOLD = 50  # Messages
SUMMARY_INTERVAL = 20  # Summarize every 20 messages after threshold


class ContextSummarizer:
    def __init__(self):
        self.message_counter = 0
        self.last_summary_count = 0

    def should_summarize(self, message_count):
        """Check if we should generate a summary."""
        if message_count < AUTO_SUMMARY_THRESHOLD:
            return False

        # Summarize every SUMMARY_INTERVAL messages after threshold
        messages_since_last = message_count - self.last_summary_count
        return messages_since_last >= SUMMARY_INTERVAL


# Global summarizer instance
summarizer = ContextSummarizer()

# Store original method
_original_add_message = MessageHistory.add_assistant_message


def summarized_add_assistant_message(self, message):
    """Add assistant message and potentially generate summary."""
    # Call original method first
    result = _original_add_message(self, message)

    # Check if we should summarize
    message_count = len(self.messages)

    if summarizer.should_summarize(message_count):
        try:
            print("📝 Generating context summary...")
            # Trigger memory compaction (which includes summarization)
            if hasattr(self, "compact_memory"):
                self.compact_memory()
                summarizer.last_summary_count = len(self.messages)
                print("✅ Context summary generated and applied")
        except Exception as e:
            print(f"⚠️ Failed to generate context summary: {e}")

    return result


# Monkey patch
MessageHistory.add_assistant_message = summarized_add_assistant_message

print("Plugin simulation complete. Testing...")


def test_context_summary_plugin():
    """Test if the context summary plugin is active."""
    print("Testing context summary plugin...")

    # Check if the monkey patching worked
    history = MessageHistory()

    # Check if the add_assistant_message method has been modified
    method = history.add_assistant_message
    print(f"Method: {method}")
    print(f"Method name: {method.__name__}")

    # Check if it's the original or modified version
    if method.__name__ == "summarized_add_assistant_message":
        print("✅ Plugin is active - method has been wrapped")
    else:
        print("❌ Plugin is not active - method is original")


if __name__ == "__main__":
    test_context_summary_plugin()
