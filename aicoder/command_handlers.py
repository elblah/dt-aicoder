"""
Command handlers for AI Coder.
"""

import os
import json
import tempfile
import subprocess
import pprint
from typing import Tuple, List
from . import config


class CommandHandlerMixin:
    """Mixin class for command handling."""

    def _handle_command(self, user_input: str) -> Tuple[bool, bool]:
        """Handle command input and return (should_quit, run_api_call)."""
        parts = user_input.split()
        command = parts[0].lower()
        args = parts[1:]

        # Use the centralized command registry
        handler = self.command_handlers.get(command)
        if handler:
            return handler(args)
        else:
            print(f"\n{config.RED} *** Command not found: {command}{config.RESET}")
            return False, False

    def _handle_help(self, args: List[str]) -> Tuple[bool, bool]:
        """Displays help message."""
        print("\nAvailable commands:")

        # Group commands by handler using the centralized registry
        command_map = {}
        for command, handler in sorted(self.command_handlers.items()):
            if handler not in command_map:
                command_map[handler] = []
            command_map[handler].append(command)

        command_groups = [", ".join(cmds) for cmds in command_map.values()]
        max_len = max(len(group) for group in command_groups) if command_groups else 0

        for handler, cmds in command_map.items():
            aliases = ", ".join(cmds)
            # Get docstring from the handler function
            docstring = handler.__doc__ or "No description available."
            print(f"  {aliases.ljust(max_len)}   {docstring}")

        return False, False

    def _handle_edit_memory(self, args: List[str]) -> Tuple[bool, bool]:
        """Opens $EDITOR to write the memory."""
        editor = os.environ.get("EDITOR", "vim")
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+", delete=False, suffix=".md"
            ) as tf:
                temp_filename = tf.name
                json.dump(self.message_history.messages, tf.file, indent=4)

            subprocess.run([editor, temp_filename], check=True)

            with open(temp_filename, "r") as tf:
                content = tf.read()

            os.unlink(temp_filename)

            if content.strip():
                print(f"\n{config.GREEN}>>> Memory updated...{config.RESET}")
                self.message_history.messages = json.loads(content)
                
                # Re-estimate tokens since memory content changed
                try:
                    from ..utils import estimate_messages_tokens
                    estimated_tokens = estimate_messages_tokens(self.message_history.messages)
                    print(f"{config.BLUE}>>> Context re-estimated: ~{estimated_tokens} tokens{config.RESET}")
                except Exception as e:
                    if config.DEBUG:
                        print(f"{config.RED} *** Error re-estimating tokens: {e}{config.RESET}")
                
                return False, False
            else:
                print(f"\n{config.YELLOW}*** Edit cancelled, no content.{config.RESET}")
                return False, False

        except Exception as e:
            print(f"\n{config.RED}*** Error during edit: {e}{config.RESET}")
            return False, False

    def _handle_edit(self, args: List[str]) -> Tuple[bool, bool]:
        """Opens $EDITOR to write a prompt."""
        editor = os.environ.get("EDITOR", "vim")
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+", delete=False, suffix=".md"
            ) as tf:
                temp_filename = tf.name

            subprocess.run([editor, temp_filename], check=True)

            with open(temp_filename, "r") as tf:
                content = tf.read()

            os.unlink(temp_filename)

            if content.strip():
                print(f"\n{config.GREEN}>>> Using edited prompt...{config.RESET}")
                print(content)
                self.message_history.add_user_message(content)
                return False, True
            else:
                print(f"\n{config.YELLOW}*** Edit cancelled, no content.{config.RESET}")
                return False, False

        except Exception as e:
            print(f"\n{config.RED}*** Error during edit: {e}{config.RESET}")
            return False, False

    def _handle_print_messages(self, args: List[str]) -> Tuple[bool, bool]:
        """Prints the current message history."""
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self.message_history.messages)

        # Also print the system prompt content if in debug mode
        if config.DEBUG and self.message_history.messages:
            system_prompt = self.message_history.messages[0].get("content", "")
            print(f"\n{config.YELLOW}=== SYSTEM PROMPT CONTENT ==={config.RESET}")
            print(system_prompt)
            print(f"{config.YELLOW}=== END SYSTEM PROMPT ==={config.RESET}")

        return False, False

    def _handle_summary(self, args: List[str]) -> Tuple[bool, bool]:
        """Forces session compaction."""
        self.message_history.compact_memory()
        return False, False

    def _handle_model(self, args: List[str]) -> Tuple[bool, bool]:
        """Gets or sets the API model."""
        if args:
            # Update the model in the config module
            import aicoder.config

            aicoder.config.API_MODEL = args[0]
        
        print(f"\n{config.GREEN} *** Model: {config.API_MODEL}{config.RESET}")
        return False, False

    def _handle_new_session(self, args: List[str]) -> Tuple[bool, bool]:
        """Starts a new chat session."""
        print(f"\n{config.GREEN} *** New session created...{config.RESET}")
        self.message_history.reset_session()
        return False, False

    def _handle_save_session(self, args: List[str]) -> Tuple[bool, bool]:
        """Saves the current session to a file."""
        fname = args[0] if args else "session.json"
        self.message_history.save_session(fname)
        return False, False

    def _handle_load_session(self, args: List[str]) -> Tuple[bool, bool]:
        """Loads a session from a file."""
        fname = args[0] if args else "session.json"
        self.message_history.load_session(fname)
        return False, False

    def _handle_breakpoint(self, args: List[str]) -> Tuple[bool, bool]:
        """Enters the debugger."""
        breakpoint()
        return False, False

    def _handle_stats(self, args: List[str]) -> Tuple[bool, bool]:
        """Displays session statistics."""
        # Use the stats object to print statistics, passing message history for context
        self.stats.print_stats(self.message_history)
        return False, False

    def _handle_yolo(self, args: List[str]) -> Tuple[bool, bool]:
        """Manage YOLO mode: /yolo [on|off] - Show or toggle YOLO mode."""
        import aicoder.config

        if not args:
            # Show current status
            status = "enabled" if aicoder.config.YOLO_MODE else "disabled"
            print(f"\n{config.GREEN}*** YOLO mode is {status}{config.RESET}")
            return False, False

        arg = args[0].lower()
        if arg in ["on", "enable", "1", "true"]:
            # Enable YOLO mode
            import os

            os.environ["YOLO_MODE"] = "1"
            aicoder.config.YOLO_MODE = True
            print(f"\n{config.GREEN}*** YOLO mode enabled{config.RESET}")
        elif arg in ["off", "disable", "0", "false"]:
            # Disable YOLO mode
            import os

            os.environ["YOLO_MODE"] = "0"
            aicoder.config.YOLO_MODE = False
            print(f"\n{config.GREEN}*** YOLO mode disabled{config.RESET}")
        else:
            print(f"\n{config.RED}*** Invalid argument. Use: /yolo [on|off]{config.RESET}")

        return False, False

    def _handle_revoke_approvals(self, args: List[str]) -> Tuple[bool, bool]:
        """Revokes all session approvals and clears the approval cache."""
        self.tool_manager.approval_system.revoke_approvals()
        return False, False

    def _handle_retry(self, args: List[str]) -> Tuple[bool, bool]:
        """Retries the last API call without modifying the conversation history."""
        if len(self.message_history.messages) < 2:
            print(f"\n{config.YELLOW}*** Not enough messages to retry.{config.RESET}")
            return False, False

        print(f"\n{config.GREEN}*** Retrying last request...{config.RESET}")

        # Check if debug mode is enabled and notify user
        import os
        if os.environ.get("DEBUG") == "1" and os.environ.get("STREAM_LOG_FILE"):
            print(f"{config.YELLOW}*** Debug mode is active - will log to: {os.environ.get('STREAM_LOG_FILE')}{config.RESET}")
        
        # Simply resend the current context without modifying history
        return False, True

    def _handle_debug(self, args: List[str]) -> Tuple[bool, bool]:
        """Manage debug mode: /debug [on|off] - Show or toggle debug logging for streaming issues."""
        import os

        # Check current debug state
        current_debug = os.environ.get("DEBUG", "") == "1"
        current_stream_log = os.environ.get("STREAM_LOG_FILE", "")

        if not args:
            # Show current status
            status = "enabled" if current_debug and current_stream_log else "disabled"
            print(f"\n{config.GREEN}*** Debug logging is {status}{config.RESET}")
            if current_debug and current_stream_log:
                print("    - DEBUG mode: ON")
                print(f"    - Stream logging: {current_stream_log}")
            return False, False

        arg = args[0].lower()
        if arg in ["on", "enable", "1", "true"]:
            if current_debug and current_stream_log:
                print(f"\n{config.GREEN}*** Debug logging is already enabled{config.RESET}")
                print("    - DEBUG mode: ON")
                print(f"    - Stream logging: {current_stream_log}")
                return False, False

            # Enable debug logging
            os.environ["DEBUG"] = "1"
            os.environ["STREAM_LOG_FILE"] = "stream_debug.log"

            # Also set longer timeouts to avoid false timeouts during debugging
            os.environ["STREAMING_TIMEOUT"] = "600"
            os.environ["STREAMING_READ_TIMEOUT"] = "120"
            os.environ["HTTP_TIMEOUT"] = "600"

            # Force re-initialization of streaming adapter to pick up new debug settings
            if hasattr(self, "_streaming_adapter"):
                delattr(self, "_streaming_adapter")
                print("    - Streaming adapter reset to pick up debug settings")

            print(f"\n{config.GREEN}*** Debug logging enabled{config.RESET}")
            print("    - DEBUG mode: ON")
            print("    - Stream logging: stream_debug.log")
            print("    - Streaming timeout: 600s")
            print("    - Read timeout: 120s")
            print("    - HTTP timeout: 600s")
            print(f"{config.YELLOW}*** Run /retry or make a request to capture debug data.{config.RESET}")

        elif arg in ["off", "disable", "0", "false"]:
            if not current_debug:
                print(f"\n{config.GREEN}*** Debug logging is already disabled{config.RESET}")
                return False, False

            # Disable debug logging
            os.environ.pop("DEBUG", None)
            os.environ.pop("STREAM_LOG_FILE", None)
            os.environ.pop("STREAMING_TIMEOUT", None)
            os.environ.pop("STREAMING_READ_TIMEOUT", None)
            os.environ.pop("HTTP_TIMEOUT", None)

            # Force re-initialization of streaming adapter to pick up new debug settings
            if hasattr(self, "_streaming_adapter"):
                delattr(self, "_streaming_adapter")
                print("    - Streaming adapter reset to disable debug settings")

            print(f"\n{config.GREEN}*** Debug logging disabled{config.RESET}")
            print("    - DEBUG mode: OFF")
            print("    - Stream logging: OFF")

        else:
            print(f"\n{config.RED}*** Invalid argument. Use: /debug [on|off]{config.RESET}")

        return False, False

    def _handle_quit(self, args: List[str]) -> Tuple[bool, bool]:
        """Exits the application."""
        return True, False
