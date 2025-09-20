"""
Main application module for AI Coder.
"""

import os
import sys
import json
import time
import traceback
import signal

from .config import (
    DEBUG,
    GREEN,
    RED,
    RESET,
    BOLD,
    YELLOW,
    ENABLE_STREAMING,
)
from .stats import Stats
from .message_history import MessageHistory
from .tool_manager import MCPToolManager
from .animator import Animator

from .api_handler import APIHandlerMixin
from .tool_call_executor import ToolCallExecutorMixin
from .input_handler import InputHandlerMixin
from .command_handlers import CommandHandlerMixin
from .plugin_system.loader import load_plugins, notify_plugins_of_aicoder_init
from .utils import parse_markdown


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Global exception handler to catch unhandled exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't handle KeyboardInterrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Print the error
    print(f"\n{RED}*** UNHANDLED EXCEPTION ***{RESET}", file=sys.stderr)
    print(f"{RED}Type: {exc_type.__name__}{RESET}", file=sys.stderr)
    print(f"{RED}Value: {exc_value}{RESET}", file=sys.stderr)

    # Save session if possible
    try:
        # Try to save the current session
        save_crash_session()
        print(f"{YELLOW}Session saved to session_crash.json{RESET}", file=sys.stderr)
    except Exception as save_error:
        print(
            f"{RED}Failed to save crash session: {save_error}{RESET}", file=sys.stderr
        )

    # Print traceback
    print(f"\n{RED}Full traceback:{RESET}", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)

    print(
        f"\n{YELLOW}The application has crashed unexpectedly. Session data has been saved to session_crash.json{RESET}",
        file=sys.stderr,
    )


def save_crash_session():
    """Save the current session to a crash file."""
    # This function will be populated by the AICoder instance when it's created
    pass


class AICoder(
    APIHandlerMixin,
    ToolCallExecutorMixin,
    InputHandlerMixin,
    CommandHandlerMixin,
):
    """Main application class for AI Coder."""

    def __init__(self):
        # Set up global exception handler
        global save_crash_session
        save_crash_session = self._save_crash_session
        sys.excepthook = global_exception_handler

        # Load plugins first, before anything else
        self.loaded_plugins = load_plugins()
        loaded_plugins = self.loaded_plugins

        # Set up signal handler for SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, self._signal_handler)

        self.stats = Stats()
        self.message_history = MessageHistory()
        self.animator = Animator()

        # Initialize parent classes properly
        super().__init__()

        self.tool_manager = MCPToolManager(
            self.stats, self.message_history, animator=self.animator
        )
        self._initialize_mcp_servers()

        # Set up the API handler reference in message history
        self.message_history.api_handler = self

        # Centralized command registry to eliminate duplication
        self.command_handlers = {
            "/help": self._handle_help,
            "/edit": self._handle_edit,
            "/e": self._handle_edit,
            "/memory": self._handle_edit_memory,
            "/m": self._handle_edit_memory,
            "/quit": self._handle_quit,
            "/q": self._handle_quit,
            "/pprint_messages": self._handle_print_messages,
            "/pm": self._handle_print_messages,
            "/compact": self._handle_summary,
            "/c": self._handle_summary,
            "/model": self._handle_model,
            "/new": self._handle_new_session,
            "/save": self._handle_save_session,
            "/load": self._handle_load_session,
            "/breakpoint": self._handle_breakpoint,
            "/bp": self._handle_breakpoint,
            "/stats": self._handle_stats,
            "/retry": self._handle_retry,
            "/r": self._handle_retry,
            "/revoke_approvals": self._handle_revoke_approvals,
            "/ra": self._handle_revoke_approvals,
            "/yolo": self._handle_yolo,
        }

        # Notify plugins that AICoder is initialized
        notify_plugins_of_aicoder_init(loaded_plugins, self)

        # Print streaming status at startup only if disabled (since it's enabled by default)
        if not ENABLE_STREAMING:
            print(f"{GREEN}*** Streaming mode disabled{RESET}")

        # Print auto-compaction status at startup if enabled
        from .config import AUTO_COMPACT_THRESHOLD

        if AUTO_COMPACT_THRESHOLD > 0:
            print(
                f"{GREEN}*** Auto-compaction enabled (threshold: {AUTO_COMPACT_THRESHOLD} tokens){RESET}"
            )

    def _signal_handler(self, sig, frame):
        """Handle SIGINT (Ctrl+C) signal gracefully."""
        print(f"\n{RED}Received interrupt signal. Exiting...{RESET}")
        self._print_exit_stats()

        # Save cost data if the tiered cost plugin is loaded
        try:
            import atexit

            # Force run all exit handlers to save cost data
            for handler in atexit._exithandlers:
                try:
                    handler[0](*handler[1], **handler[2])
                except Exception:
                    pass  # Ignore errors in exit handlers
        except Exception:
            pass  # Ignore if atexit module is not available or other issues

        sys.exit(0)

    def _check_auto_compaction(self):
        """Check if auto-compaction should be triggered based on current prompt size."""
        from .config import AUTO_COMPACT_THRESHOLD

        # If threshold is 0 or negative, auto-compaction is disabled
        if AUTO_COMPACT_THRESHOLD <= 0:
            return

        # Check if current prompt size exceeds the threshold
        if self.stats.current_prompt_size >= AUTO_COMPACT_THRESHOLD:
            print(
                f"\n{GREEN} *** Auto-compaction threshold reached (current: {self.stats.current_prompt_size} >= threshold: {AUTO_COMPACT_THRESHOLD} tokens){RESET}"
            )
            self.message_history.compact_memory()

    def _initialize_mcp_servers(self):
        """Initialize all MCP stdio servers at startup."""
        init_printed = False
        for name, config in self.tool_manager.mcp_tools.items():
            if config.get("type") == "mcp-stdio":
                try:
                    if not init_printed:
                        print(f"{GREEN}*** Initializing MCP servers...{RESET}")
                        init_printed = True
                    tools = self.tool_manager.registry._discover_mcp_server_tools(name)
                    print(
                        f"{GREEN}*** Initialized MCP server '{name}' with {len(tools)} tools{RESET}"
                    )
                except Exception as e:
                    print(
                        f"{RED}*** Failed to initialize MCP server '{name}': {e}{RESET}"
                    )

    def _save_crash_session(self):
        """Save the current session to a crash file."""
        try:
            # Create crash session data
            crash_data = {
                "messages": self.message_history.messages,
                "stats": {
                    "api_requests": self.stats.api_requests,
                    "api_success": self.stats.api_success,
                    "api_errors": self.stats.api_errors,
                    "api_time_spent": self.stats.api_time_spent,
                    "tool_calls": self.stats.tool_calls,
                    "tool_errors": self.stats.tool_errors,
                    "tool_time_spent": self.stats.tool_time_spent,
                    "messages_sent": self.stats.messages_sent,
                    "tokens_processed": self.stats.tokens_processed,
                    "compactions": self.stats.compactions,
                    "prompt_tokens": self.stats.prompt_tokens,
                    "completion_tokens": self.stats.completion_tokens,
                },
                "timestamp": time.time(),
                "note": "This session was automatically saved due to an unexpected crash",
            }

            # Save to crash file
            with open("session_crash.json", "w", encoding="utf-8") as f:
                json.dump(crash_data, f, indent=2, default=str)

        except Exception as e:
            # If we can't save the crash session, print an error but don't raise
            print(f"Failed to save crash session: {e}", file=sys.stderr)

    def _print_exit_stats(self):
        """Print statistics on exit."""
        self.stats.print_stats()

    def run(self):
        """Main application loop."""
        try:
            while True:
                try:
                    run_api_call = False

                    # Use the new multi-line input function
                    user_input = self._get_multiline_input()
                    user_input = user_input.strip()
                    if not user_input:
                        continue

                    # Handle prompt append functionality
                    user_input = self._handle_prompt_append(user_input)

                    if user_input.startswith("/"):
                        should_quit, run_api_call = self._handle_command(user_input)
                        if should_quit:
                            self._print_exit_stats()
                            break

                        if not run_api_call:
                            continue

                    if not run_api_call:
                        self.message_history.add_user_message(user_input)

                    # Reset retry counter for new API requests
                    self.retry_handler.reset_retry_counter()

                    while True:
                        response = self._make_api_request(self.message_history.messages)
                        if response is None:
                            # User cancelled the request
                            print(
                                f"\n{RED}Request cancelled. Returning to user input.{RESET}"
                            )
                            break
                        if (
                            not response
                            or "choices" not in response
                            or not response["choices"]
                        ):
                            print("API call failed.")
                            break

                        message = response["choices"][0]["message"]
                        self.message_history.add_assistant_message(message)

                        if message.get("tool_calls"):
                            if DEBUG:
                                print(
                                    f"DEBUG: Message has tool calls: {message['tool_calls']}"
                                )
                            tool_results, cancel_all_active = self._execute_tool_calls(
                                message
                            )
                            # Ensure we're adding all tool results to messages
                            if tool_results:
                                self.message_history.add_tool_results(tool_results)
                            else:
                                print(f"{RED} * Warning: No tool results to add{RESET}")

                            # If cancel all was activated, break out of the tool loop and return to user input
                            if cancel_all_active:
                                print(
                                    f"\n{RED} *** Cancel all activated - returning to user input{RESET}"
                                )
                                break
                            continue
                        else:
                            # Check if this is a streaming response - if so, don't print the content again
                            # as it was already printed during streaming
                            if not message.get("_streaming_response"):
                                # Check if content is empty - this indicates an error condition
                                if not message["content"].strip():
                                    # Empty content is an error - check finish reason for details
                                    finish_reason = response["choices"][0].get(
                                        "finish_reason"
                                    )
                                    if finish_reason:
                                        print(
                                            f"\n{RED}AI Error: Empty response (finish_reason: {finish_reason}){RESET}"
                                        )
                                        if finish_reason == "content_filter":
                                            print(
                                                f"{YELLOW}The response was filtered by content safety systems.{RESET}"
                                            )
                                        elif finish_reason == "length":
                                            print(
                                                f"{YELLOW}The response was truncated due to token limits before any content was generated.{RESET}"
                                            )
                                        else:
                                            print(
                                                f"{YELLOW}The API returned an empty response. This may indicate an issue with the request.{RESET}"
                                            )
                                    else:
                                        print(
                                            f"\n{RED}AI Error: Empty response with no finish reason{RESET}"
                                        )
                                        print(
                                            f"{YELLOW}This may indicate a network issue or API problem.{RESET}"
                                        )

                                    # Don't continue with empty content - break the loop
                                    break
                                else:
                                    # Normal content - print it
                                    print(
                                        f"\n{BOLD}{GREEN}AI:{RESET} {parse_markdown(message['content'])}"
                                    )

                            # Check for auto-compaction after each response
                            self._check_auto_compaction()

                            break

                except (KeyboardInterrupt, EOFError):
                    print(f"\n{RED}Received interrupt. Exiting...{RESET}")
                    self._print_exit_stats()
                    break
        except Exception:
            # Re-raise the exception so the global exception handler can catch it
            raise


def main():
    """Main entry point."""
    # Check for crash session
    if os.path.exists("session_crash.json"):
        print(f"{YELLOW}Found a crash session from a previous run.{RESET}")
        print(f"{YELLOW}File: session_crash.json{RESET}")
        response = (
            input(f"{GREEN}Do you want to load this session? (y/N/d): {RESET}")
            .strip()
            .lower()
        )
        if response in ["d", "delete"]:
            # Delete the crash session file
            try:
                os.remove("session_crash.json")
                print(f"{GREEN}Crash session file deleted.{RESET}")
            except Exception as e:
                print(f"{RED}Failed to delete crash session file: {e}{RESET}")
            # Continue with fresh session
            app = AICoder()
            app.run()
            return
        elif response in ["y", "yes"]:
            try:
                # Load the crash session
                with open("session_crash.json", "r", encoding="utf-8") as f:
                    crash_data = json.load(f)

                # Initialize the app first
                app = AICoder()

                # Restore messages and stats
                app.message_history.messages = crash_data.get("messages", [])
                app.message_history.initial_system_prompt = (
                    app.message_history.messages[0]
                    if app.message_history.messages
                    else None
                )

                # Restore stats if available
                stats_data = crash_data.get("stats", {})
                app.stats.api_requests = stats_data.get("api_requests", 0)
                app.stats.api_success = stats_data.get("api_success", 0)
                app.stats.api_errors = stats_data.get("api_errors", 0)
                app.stats.api_time_spent = stats_data.get("api_time_spent", 0)
                app.stats.tool_calls = stats_data.get("tool_calls", 0)

                print(f"{GREEN}Crash session loaded successfully.{RESET}")
                # Optionally rename the crash file to indicate it's been loaded
                os.rename("session_crash.json", "session_crash_loaded.json")
                print(f"{YELLOW}Crash file renamed to session_crash_loaded.json{RESET}")

                # Run the app with loaded data
                app.run()
                return
            except Exception as e:
                print(f"{RED}Failed to load crash session: {e}{RESET}")
                print(f"{RED}Starting fresh session instead.{RESET}")

    app = AICoder()
    app.run()


if __name__ == "__main__":
    if "container" in os.environ:
        print("Sandbox:", os.environ.get("container", "unknown"))

    main()
