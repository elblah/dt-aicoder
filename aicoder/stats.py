"""
Statistics tracking for AI Coder.
"""

import time
from dataclasses import dataclass, field
from datetime import timedelta

from . import config
from .utils import imsg


@dataclass
class Stats:
    """Statistics tracking for the application."""

    api_requests: int = 0
    api_success: int = 0
    api_errors: int = 0
    api_time_spent: float = 0.0  # Time spent in API calls
    tool_calls: int = 0
    tool_errors: int = 0
    tool_time_spent: float = 0.0  # Time spent in tool calls
    messages_sent: int = 0
    tokens_processed: int = 0
    session_start_time: float = field(default_factory=time.time)
    compactions: int = 0
    prompt_tokens: int = 0  # Cumulative input tokens for statistics
    completion_tokens: int = 0  # Cumulative output tokens for statistics
    current_prompt_size: int = (
        0  # Current conversation history size for auto-compaction
    )

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
