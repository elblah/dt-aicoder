"""
Statistics tracking for AI Coder.
"""

import os
import time
from dataclasses import dataclass, field
from datetime import timedelta

from . import config
from .utils import imsg


def get_stats():
    """Get the singleton stats instance."""
    return Stats()


class Stats:
    """Statistics tracking for the application - singleton pattern."""

    _instance = None
    _initialized = False
    last_user_prompt = ""  # Class attribute - always exists

    def __new__(cls):
        # Allow bypassing singleton for testing
        if os.environ.get("AICODER_TEST_MODE") == "1":
            return super().__new__(cls)
            
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Allow bypassing singleton initialization for testing
        if os.environ.get("AICODER_TEST_MODE") == "1" or not self._initialized:
            self.api_requests = 0
            self.api_success = 0
            self.api_errors = 0
            self.api_time_spent = 0.0  # Time spent in API calls
            self.tool_calls = 0
            self.tool_errors = 0
            self.tool_time_spent = 0.0  # Time spent in tool calls
            self.messages_sent = 0
            self.tokens_processed = 0
            self.session_start_time = time.time()
            self.compactions = 0
            self.prompt_tokens = 0  # Cumulative input tokens for statistics
            self.completion_tokens = 0  # Cumulative output tokens for statistics
            self.current_prompt_size = 0  # Current conversation history size for auto-compaction
            self.current_prompt_size_estimated = False  # Whether current_prompt_size is estimated or from API
            self.last_user_prompt = ""  # Last user prompt content for plugins (spell check, etc.)
            self.usage_infos = []  # List of usage objects returned by the API with timestamps
            
            if os.environ.get("AICODER_TEST_MODE") != "1":
                self._initialized = True

    def print_stats(self, message_history=None):
        """Displays session statistics."""

        elapsed_time = time.time() - self.session_start_time

        tps = 0
        if self.api_time_spent > 0:
            tps = self.completion_tokens / self.api_time_spent

        imsg("\n=== Session Statistics ===")
        print(f"Session duration: {timedelta(seconds=int(elapsed_time))}")

        # Show message history count and size if available
        if message_history is not None:
            # Subtract 1 for the system message which is always present
            message_count = (
                len(message_history.messages) - 1 if message_history.messages else 0
            )
            # Calculate the size of the message history in bytes
            import json

            message_history_bytes = len(
                json.dumps(message_history.messages, default=str)
            )
            print(
                f"Messages in history: {message_count} ({message_history_bytes} bytes)"
            )
        print(f"API requests: {self.api_requests}")
        print(f"  - Successful: {self.api_success}")
        print(f"  - Errors: {self.api_errors}")
        print(f"  - Time spent: {timedelta(seconds=int(self.api_time_spent))}")
        print(
            f"  - Tokens: {self.prompt_tokens:,} input, {self.completion_tokens:,} output ({self.prompt_tokens + self.completion_tokens:,} total)"
        )
        print(f"  - Tokens per second (TPS): {tps:.1f}")
        print(f"Tool calls: {self.tool_calls}")
        print(f"  - Errors: {self.tool_errors}")
        print(f"  - Time spent: {timedelta(seconds=int(self.tool_time_spent))}")
        print(f"Memory compactions: {self.compactions}")

        # Calculate success rates
        if self.api_requests > 0:
            success_rate = (self.api_success / self.api_requests) * 100
            print(f"API success rate: {success_rate:.1f}%")

        if self.tool_calls > 0:
            tool_success_rate = (
                (self.tool_calls - self.tool_errors) / self.tool_calls
            ) * 100
            print(f"Tool success rate: {tool_success_rate:.1f}%")

        # Calculate TPS (Tokens Per Second)

        # Show context usage percentage if auto-compaction is enabled
        self._print_context_usage()

    def _print_context_usage(self):
        """Print context usage percentage if auto-compaction is enabled."""
        try:
            if config.AUTO_COMPACT_ENABLED:
                if self.current_prompt_size > 0:
                    usage_percentage = (
                        self.current_prompt_size / config.CONTEXT_SIZE
                    ) * 100
                    print(
                        f"Context usage: {usage_percentage:.1f}% "
                        f"({self.current_prompt_size:,}/{config.CONTEXT_SIZE:,} tokens, "
                        f"triggers at {config.CONTEXT_COMPACT_PERCENTAGE}%)"
                    )
                else:
                    print(
                        f"Context usage: 0.0% "
                        f"({self.current_prompt_size:,}/{config.CONTEXT_SIZE:,} tokens, "
                        f"triggers at {config.CONTEXT_COMPACT_PERCENTAGE}%)"
                    )
        except (ImportError, AttributeError):
            # Config not available, skip context usage display
            pass
