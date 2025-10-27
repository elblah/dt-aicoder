"""
Enhanced compact command for AI Coder with subcommands.
"""

from typing import Tuple, List
from .base import BaseCommand
from ..utils import imsg, emsg, wmsg
from ..message_history import NoMessagesToCompactError


class CompactCommand(BaseCommand):
    """Enhanced session compaction with multiple subcommands."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/compact", "/c"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Execute compact subcommands."""

        # No arguments = try auto-compaction with enhanced feedback
        if not args:
            return self._handle_auto_compact()

        # Handle subcommands
        subcommand = args[0].lower()

        if subcommand == "force":
            return self._handle_force_compact(args[1:])
        elif subcommand == "stats":
            return self._handle_stats()
        elif subcommand == "auto":
            return self._handle_auto_control(args[1:])
        elif subcommand == "help":
            return self._handle_help()
        else:
            emsg(f"\n [X] Unknown subcommand: {subcommand}")
            wmsg(" *** Use '/compact help' to see available commands")
            return False, False

    def _handle_auto_compact(self) -> Tuple[bool, bool]:
        """Handle normal auto-compaction attempt with enhanced feedback."""
        from .. import config

        # Calculate current token usage
        current_tokens = 0
        threshold = 0
        percentage = 0

        if self.app.message_history.api_handler and hasattr(
            self.app.message_history.api_handler, "stats"
        ):
            current_tokens = (
                self.app.message_history.api_handler.stats.current_prompt_size
            )

        if config.AUTO_COMPACT_THRESHOLD > 0:
            threshold = config.AUTO_COMPACT_THRESHOLD
            percentage = (current_tokens / threshold) * 100 if threshold > 0 else 0

        # Get round count
        round_count = self.app.message_history.get_round_count()

        # Check if there are any messages at all
        if round_count == 0:
            wmsg("\n [i] No messages available to compact")
            wmsg(" [i] Your conversation is already minimal")
            wmsg(" [i] Start a conversation to enable compaction features")
            wmsg(" [i] Use '/compact help' for more options")
            return False, False

        # Check if auto-compaction is actually needed first
        if (
            config.AUTO_COMPACT_THRESHOLD > 0
            and percentage < config.CONTEXT_COMPACT_PERCENTAGE
        ):
            wmsg(
                f"\n [i] Auto-compaction not needed ({percentage:.1f}% of {threshold:,} tokens - below {config.CONTEXT_COMPACT_PERCENTAGE}% threshold)"
            )
            wmsg(f" [i] Current conversation: {round_count} rounds")
            wmsg(' [i] A "round" = user message + complete assistant response')
            wmsg(" [i] Force compaction: /compact force [N] (default 1 round)")
            wmsg(" [i] Use '/compact help' for more options")
            return False, False

        try:
            # Store original message count to detect if compaction actually happened
            original_message_count = len(self.app.message_history.messages)
            self.app.message_history.compact_memory()

            # Check if compaction actually occurred
            if self.app.message_history._compaction_performed:
                new_message_count = len(self.app.message_history.messages)
                messages_removed = original_message_count - new_message_count
                imsg(
                    f"\n [✓] Auto-compaction completed successfully (removed {messages_removed} messages)"
                )
            else:
                wmsg("\n [i] Auto-compaction checked - no changes needed")
                wmsg(" [i] Your conversation context is already optimized")
                wmsg(f" [i] Current conversation: {round_count} rounds")
                wmsg(" [i] If you want to force compaction anyway: /compact force [N]")
                wmsg(" [i] Use '/compact help' for more options")

        except NoMessagesToCompactError:
            wmsg("\n [i] No messages available to compact")
            wmsg(" [i] Your conversation is already minimal")
            wmsg(f" [i] Current conversation: {round_count} rounds")
            if round_count == 0:
                wmsg(" [i] Start a conversation to enable compaction features")
            else:
                wmsg(" [i] Use '/compact force [N]' to remove specific rounds if needed")
            wmsg(" [i] Use '/compact help' for more options")
        except Exception as e:
            emsg(f"\n [X] Auto-compaction failed: {str(e)}")
            wmsg(" *** Your conversation history has been preserved.")
            wmsg(
                " *** Options: Try '/compact force', save with '/save', or continue with a new message."
            )
            self.app.message_history._compaction_performed = False

        return False, False

    def _handle_force_compact(self, args: List[str]) -> Tuple[bool, bool]:
        """Handle force compaction of N oldest rounds."""
        # Parse number of rounds
        if args and args[0].isdigit():
            num_rounds = int(args[0])
            if num_rounds <= 0:
                emsg("\n [X] Number of rounds must be positive")
                return False, False
        else:
            num_rounds = 1  # Default

        try:
            compacted_rounds = self.app.message_history.compact_rounds(num_rounds)
            actual_compacted = len(compacted_rounds)
            remaining = self.app.message_history.get_round_count()

            imsg(
                f"\n [✓] Force compacted {actual_compacted} oldest round{'s' if actual_compacted != 1 else ''}"
            )
            wmsg(f" [i] Remaining: {remaining} round{'s' if remaining != 1 else ''}")

        except NoMessagesToCompactError as e:
            wmsg(f"\n [i] Nothing to compact: {str(e)}")
        except Exception as e:
            emsg(f"\n [X] Force compaction failed: {str(e)}")
            wmsg(" *** Your conversation history has been preserved.")
            self.app.message_history._compaction_performed = False

        return False, False

    def _handle_stats(self) -> Tuple[bool, bool]:
        """Handle statistics display."""
        from .. import config

        # Get round count
        round_count = self.app.message_history.get_round_count()

        # Get token info
        current_tokens = 0
        threshold = 0
        percentage = 0
        auto_enabled = False

        if self.app.message_history.api_handler and hasattr(
            self.app.message_history.api_handler, "stats"
        ):
            current_tokens = (
                self.app.message_history.api_handler.stats.current_prompt_size
            )

        if config.AUTO_COMPACT_THRESHOLD > 0:
            threshold = config.AUTO_COMPACT_THRESHOLD
            percentage = (current_tokens / threshold) * 100 if threshold > 0 else 0
            auto_enabled = True

        # Display stats
        imsg("\n Conversation Statistics:")
        wmsg(
            f" [i] Current conversation: {round_count} round{'s' if round_count != 1 else ''}"
        )

        if auto_enabled:
            wmsg(
                f" [i] Auto-compaction: enabled (triggers at {config.CONTEXT_COMPACT_PERCENTAGE}% of {threshold:,} tokens)"
            )
            wmsg(f" [i] Current usage: {current_tokens:,} tokens ({percentage:.1f}%)")
        else:
            wmsg(" [i] Auto-compaction: disabled")

        # Show compaction stats
        compaction_count = getattr(self.app.message_history.stats, "compactions", 0)
        wmsg(f" [i] Total compactions: {compaction_count}")

        return False, False

    def _handle_auto_control(self, args: List[str]) -> Tuple[bool, bool]:
        """Handle auto-compaction control (enable/disable/status)."""

        if not args:
            # Default to status if no sub-subcommand
            return self._handle_auto_status()

        action = args[0].lower()

        if action == "enable":
            return self._handle_auto_enable()
        elif action == "disable":
            return self._handle_auto_disable()
        elif action == "status":
            return self._handle_auto_status()
        else:
            emsg(f"\n [X] Unknown auto control action: {action}")
            wmsg(" *** Use: /compact auto enable|disable|status")
            return False, False

    def _handle_auto_enable(self) -> Tuple[bool, bool]:
        """Handle enabling auto-compaction."""
        import os
        from .. import config

        if config.CONTEXT_COMPACT_PERCENTAGE > 0:
            wmsg("\n [i] Auto-compaction is already enabled")
        else:
            # Set default percentage if currently disabled
            os.environ["CONTEXT_COMPACT_PERCENTAGE"] = "80"
            wmsg("\n [✓] Auto-compaction enabled (80% threshold)")
            wmsg(
                " *** Restart application or use '/compact auto status' to see updated settings"
            )

        return False, False

    def _handle_auto_disable(self) -> Tuple[bool, bool]:
        """Handle disabling auto-compaction."""
        import os
        from .. import config

        if config.CONTEXT_COMPACT_PERCENTAGE == 0:
            wmsg("\n [i] Auto-compaction is already disabled")
        else:
            os.environ["CONTEXT_COMPACT_PERCENTAGE"] = "0"
            wmsg("\n [✓] Auto-compaction disabled")
            wmsg(
                " *** Restart application or use '/compact auto status' to see updated settings"
            )

        return False, False

    def _handle_auto_status(self) -> Tuple[bool, bool]:
        """Handle auto-compaction status display."""
        from .. import config

        # Get round count
        round_count = self.app.message_history.get_round_count()

        if config.CONTEXT_COMPACT_PERCENTAGE > 0:
            threshold = config.AUTO_COMPACT_THRESHOLD
            wmsg(
                f"\n [i] Auto-compaction: enabled ({config.CONTEXT_COMPACT_PERCENTAGE}% of {threshold:,} tokens)"
            )

            # Show current usage if available
            if self.app.message_history.api_handler and hasattr(
                self.app.message_history.api_handler, "stats"
            ):
                current_tokens = (
                    self.app.message_history.api_handler.stats.current_prompt_size
                )
                percentage = (current_tokens / threshold) * 100 if threshold > 0 else 0
                wmsg(
                    f" [i] Current usage: {current_tokens:,} tokens ({percentage:.1f}%)"
                )
        else:
            wmsg("\n [i] Auto-compaction: disabled")

        wmsg(
            f" [i] Current conversation: {round_count} round{'s' if round_count != 1 else ''}"
        )

        return False, False

    def _handle_help(self) -> Tuple[bool, bool]:
        """Handle help display."""
        imsg("\n Compact Command Help:\n")

        wmsg("  - /compact                    Try auto-compaction (threshold-based)")
        wmsg("    - Compacts when token usage exceeds threshold")
        wmsg("    - Shows why compaction is/isn't needed\n")

        wmsg(
            "  - /compact force [N]           Force compact N oldest conversation rounds"
        )
        wmsg("    - Default: 1 round (use /compact force for 1 round)")
        wmsg("    - Example: /compact force 3 (compacts 3 oldest rounds)")
        wmsg('    - A "round" = user message + complete assistant response\n')

        wmsg("  - /compact stats              Show conversation statistics")
        wmsg("    - Current round count and token usage")
        wmsg("    - Auto-compaction status\n")

        wmsg("  - /compact auto enable         Enable auto-compaction")
        wmsg("  - /compact auto disable        Disable auto-compaction")
        wmsg("  - /compact auto status        Show auto-compaction setting\n")

        wmsg("  - /compact help               Show this help message\n")

        wmsg("  Tips:")
        wmsg(
            "    - Use /compact force when approaching model limits (even if threshold not reached)"
        )
        wmsg("    - Auto-compaction preserves recent rounds by default")
        wmsg("    - Force compaction only removes oldest rounds")

        return False, False
