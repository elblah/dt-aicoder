"""
Main application module for AI Coder.
"""

import os
import sys
import json
import time
import traceback
import signal

from . import config
from .stats import Stats
from .message_history import MessageHistory, NoMessagesToCompactError
from .tool_manager import MCPToolManager
from .animator import Animator

from .api_handler import APIHandlerMixin
from .tool_call_executor import ToolCallExecutorMixin
from .input_handler import InputHandlerMixin
from .command_handlers import CommandHandlerMixin
from .plugin_system.loader import load_plugins, notify_plugins_of_aicoder_init
from .utils import parse_markdown
from .planning_mode import get_planning_mode


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Global exception handler to catch unhandled exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't handle KeyboardInterrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Print the error
    print(f"\n{config.RED}*** UNHANDLED EXCEPTION ***{config.RESET}", file=sys.stderr)
    print(f"{config.RED}Type: {exc_type.__name__}{config.RESET}", file=sys.stderr)
    print(f"{config.RED}Value: {exc_value}{config.RESET}", file=sys.stderr)

    # Save session if possible
    try:
        # Try to save the current session
        save_crash_session()
        print(
            f"{config.YELLOW}Session saved to session_crash.json{config.RESET}",
            file=sys.stderr,
        )
    except Exception as save_error:
        print(
            f"{config.RED}Failed to save crash session: {save_error}{config.RESET}",
            file=sys.stderr,
        )

    # Print traceback
    print(f"\n{config.RED}Full traceback:{config.RESET}", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)

    print(
        f"\n{config.YELLOW}The application has crashed unexpectedly. Session data has been saved to session_crash.json{config.RESET}",
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
        self.stats._app_instance = self  # Store reference for plugin access
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
            "/debug": self._handle_debug,
            "/d": self._handle_debug,
            "/revoke_approvals": self._handle_revoke_approvals,
            "/ra": self._handle_revoke_approvals,
            "/yolo": self._handle_yolo,
            "/plan toggle": self._handle_plan,
            "/plan": self._handle_plan,
        }

        # Notify plugins that AICoder is initialized
        notify_plugins_of_aicoder_init(loaded_plugins, self)

        # Print streaming status at startup only if disabled (since it's enabled by default)
        if not config.ENABLE_STREAMING:
            print(f"{config.GREEN}*** Streaming mode disabled{config.RESET}")

        # Print auto-compaction status at startup if enabled
        if config.AUTO_COMPACT_ENABLED:
            print(
                f"{config.GREEN}*** Auto-compaction enabled (context: {config.CONTEXT_SIZE} tokens, triggers at {config.CONTEXT_COMPACT_PERCENTAGE}%){config.RESET}"
            )

    def _signal_handler(self, sig, frame):
        """Handle SIGINT (Ctrl+C) signal gracefully."""
        print(f"\n{config.RED}Received interrupt signal. Exiting...{config.RESET}")
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

    def _check_and_handle_large_tool_results(self, tool_results):
        """Check if any tool result is too large and needs truncation or replacement."""
        # Check if any tool result is too large and needs handling
        for result in tool_results:
            if "content" in result and result["content"]:
                content_size = len(str(result["content"]))
                if content_size > config.MAX_TOOL_RESULT_SIZE:
                    original_size = content_size
                    tool_name = result.get("name", "unknown")

                    # Provide clear, informative error messages without being prescriptive
                    if tool_name == "read_file":
                        result["content"] = (
                            f"ERROR: File content too large ({original_size} bytes). Maximum {config.MAX_TOOL_RESULT_SIZE} bytes allowed. Use alternative approach to read specific portions of the file."
                        )
                    elif tool_name == "run_shell_command":
                        result["content"] = (
                            f"ERROR: Command output too large ({original_size} bytes). Maximum {config.MAX_TOOL_RESULT_SIZE} bytes allowed. Use command options to limit output size."
                        )
                    elif tool_name == "list_directory":
                        result["content"] = (
                            f"ERROR: Directory listing too large ({original_size} bytes). Maximum {config.MAX_TOOL_RESULT_SIZE} bytes allowed. Navigate to a more specific subdirectory or filter results."
                        )
                    else:
                        result["content"] = (
                            f"ERROR: Tool result too large ({original_size} bytes). Maximum {config.MAX_TOOL_RESULT_SIZE} bytes allowed."
                        )

                    if config.DEBUG:
                        print(
                            f"{config.YELLOW} *** Tool result from '{tool_name}' replaced due to size ({original_size} chars > {config.MAX_TOOL_RESULT_SIZE} limit){config.RESET}"
                        )

    def _check_auto_compaction(self):
        """Check if auto-compaction should be triggered based on context percentage."""
        # If auto-compaction is disabled, return early
        if not config.AUTO_COMPACT_ENABLED:
            return

        # Check if current prompt size exceeds the threshold
        if self.stats.current_prompt_size >= config.AUTO_COMPACT_THRESHOLD:
            # Check if the message history has the compaction flag (for backward compatibility with tests)
            # If the flag doesn't exist, assume compaction is allowed (original behavior)
            # If the flag exists and is False, compaction is allowed
            # If the flag exists and is True, compaction is blocked until a new message is added
            if not getattr(self.message_history, "_compaction_performed", False):
                percentage = (
                    self.stats.current_prompt_size / config.CONTEXT_SIZE
                ) * 100
                print(
                    f"\n{config.GREEN} *** Auto-compaction triggered (context: {self.stats.current_prompt_size:,}/{config.CONTEXT_SIZE:,} tokens, {percentage:.1f}%) {config.RESET}"
                )
                try:
                    self.message_history.compact_memory()
                except NoMessagesToCompactError:
                    # This is normal - no messages to compact (all recent or already compacted)
                    if config.DEBUG:
                        print(
                            f"{config.YELLOW} *** Skipping compaction: no messages to compact{config.RESET}"
                        )
                except Exception as e:
                    # CRITICAL: Compaction failed - preserve user data and inform user
                    print(
                        f"\n{config.RED} ❌ Compaction failed: {str(e)}{config.RESET}"
                    )
                    print(
                        f"{config.YELLOW} *** Your conversation history has been preserved.{config.RESET}"
                    )
                    print(
                        f"{config.YELLOW} *** Options: Try '/compact' again, save with '/save', or continue with a new message.{config.RESET}"
                    )
                    # Reset compaction flag to allow retry
                    self.message_history._compaction_performed = False

    def _initialize_mcp_servers(self):
        """Initialize all MCP stdio servers at startup."""
        init_printed = False
        for name, tool_config in self.tool_manager.mcp_tools.items():
            if tool_config.get("type") == "mcp-stdio":
                try:
                    if not init_printed:
                        print(
                            f"{config.GREEN}*** Initializing MCP servers...{config.RESET}"
                        )
                        init_printed = True
                    tools = self.tool_manager.registry._discover_mcp_server_tools(name)
                    print(
                        f"{config.GREEN}*** Initialized MCP server '{name}' with {len(tools)} tools{config.RESET}"
                    )
                except Exception as e:
                    print(
                        f"{config.RED}*** Failed to initialize MCP server '{name}': {e}{config.RESET}"
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

    def _print_startup_info(self):
        """Print startup time (includes python interpreter + sandbox startup)"""
        start_str = os.environ.get("AICODER_START_TIME")
        if start_str:
            start = float(start_str)
            now = time.time()
            elapsed = now - start
            print(f"Total startup time: {elapsed:.2f} seconds")

    def run(self):
        """Main application loop."""
        try:
            self._print_startup_info()
            while True:
                try:
                    run_api_call = False

                    self._check_auto_compaction()

                    # Auto-save session if enabled before showing prompt
                    self.message_history.autosave_if_enabled()

                    # Use the new multi-line input function
                    user_input = self._get_multiline_input()
                    user_input = user_input.strip()
                    if not user_input:
                        continue

                    # Handle prompt append functionality
                    user_input = self._handle_prompt_append(user_input)
                    
                    # Handle planning mode content
                    user_input = self._handle_planning_mode_content(user_input)

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
                                f"\n{config.RED}Request cancelled. Returning to user input.{config.RESET}"
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

                        self._check_auto_compaction()

                        if message.get("tool_calls"):
                            if config.DEBUG:
                                print(
                                    f"DEBUG: Message has tool calls: {message['tool_calls']}"
                                )

                            tool_results, cancel_all_active = self._execute_tool_calls(
                                message
                            )
                            # Ensure we're adding all tool results to messages
                            if tool_results:
                                # Check and handle large tool results for size limiting
                                self._check_and_handle_large_tool_results(tool_results)
                                self.message_history.add_tool_results(tool_results)
                            else:
                                print(
                                    f"{config.RED} * Warning: No tool results to add{config.RESET}"
                                )

                            # If cancel all was activated, break out of the tool loop and return to user input
                            if cancel_all_active:
                                print(
                                    f"\n{config.RED} *** Cancel all activated - returning to user input{config.RESET}"
                                )
                                break
                            continue
                        else:
                            # Check if this is a streaming response - if so, don't print the content again
                            # as it was already printed during streaming
                            if not message.get("_streaming_response"):
                                # Notify plugins before AI response
                                if hasattr(self, "loaded_plugins"):
                                    from .plugin_system.loader import (
                                        notify_plugins_before_ai_prompt,
                                    )

                                    notify_plugins_before_ai_prompt(self.loaded_plugins)

                                # Display token information before AI response if enabled
                                if config.ENABLE_TOKEN_INFO_DISPLAY:
                                    from .utils import display_token_info

                                    display_token_info(
                                        self.stats, config.AUTO_COMPACT_THRESHOLD
                                    )
                                    print()  # Add newline after token info so AI response appears on next line

                                # Check if content is empty - this indicates an error condition
                                if not message["content"].strip():
                                    # Empty content is an error - check finish reason for details
                                    finish_reason = response["choices"][0].get(
                                        "finish_reason"
                                    )
                                    if finish_reason:
                                        print(
                                            f"\n{config.RED}AI Error: Empty response (finish_reason: {finish_reason}){config.RESET}"
                                        )
                                        if finish_reason == "content_filter":
                                            print(
                                                f"{config.YELLOW}The response was filtered by content safety systems.{config.RESET}"
                                            )
                                        elif finish_reason == "length":
                                            print(
                                                f"{config.YELLOW}The response was truncated due to token limits before any content was generated.{config.RESET}"
                                            )
                                        else:
                                            print(
                                                f"{config.YELLOW}The API returned an empty response. This may indicate an issue with the request.{config.RESET}"
                                            )
                                    else:
                                        print(
                                            f"\n{config.RED}AI Error: Empty response with no finish reason{config.RESET}"
                                        )
                                        print(
                                            f"{config.YELLOW}This may indicate a network issue or API problem.{config.RESET}"
                                        )

                                    # Don't continue with empty content - break the loop
                                    break
                                else:
                                    # Normal content - print it
                                    # Add [PLAN] prefix if planning mode is active
                                    from .planning_mode import get_planning_mode
                                    planning_mode = get_planning_mode()
                                    plan_prefix = "[PLAN] " if planning_mode.is_plan_mode_active() else ""
                                    print(
                                        f"{config.BOLD}{config.GREEN}{plan_prefix}AI:{config.RESET} {parse_markdown(message['content'])}"
                                    )

                            break

                    # Check for auto-compaction after each complete interaction cycle (before showing prompt to user)
                    self._check_auto_compaction()

                except (KeyboardInterrupt, EOFError):
                    print(f"\n{config.RED}Received interrupt. Exiting...{config.RESET}")
                    self._print_exit_stats()
                    break
        except Exception:
            # Re-raise the exception so the global exception handler can catch it
            raise


def main():
    """Main entry point."""
    
    # Simple tab completion - always suggest /plan
    import readline
    def tab_complete(text, state):
        return "/plan toggle" if state == 0 else None
    
    readline.set_completer(tab_complete)
    readline.parse_and_bind('tab: complete')
    
    # Check for crash session
    if os.path.exists("session_crash.json"):
        print(
            f"{config.YELLOW}Found a crash session from a previous run.{config.RESET}"
        )
        print(f"{config.YELLOW}File: session_crash.json{config.RESET}")
        response = (
            input(
                f"{config.GREEN}Do you want to load this session? (y/N/d): {config.RESET}"
            )
            .strip()
            .lower()
        )
        if response in ["d", "delete"]:
            # Delete the crash session file
            try:
                os.remove("session_crash.json")
                print(f"{config.GREEN}Crash session file deleted.{config.RESET}")
            except Exception as e:
                print(
                    f"{config.RED}Failed to delete crash session file: {e}{config.RESET}"
                )
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

                print(f"{config.GREEN}Crash session loaded successfully.{config.RESET}")
                # Optionally rename the crash file to indicate it's been loaded
                os.rename("session_crash.json", "session_crash_loaded.json")
                print(
                    f"{config.YELLOW}Crash file renamed to session_crash_loaded.json{config.RESET}"
                )

                # Run the app with loaded data
                app.run()
                return
            except Exception as e:
                print(f"{config.RED}Failed to load crash session: {e}{config.RESET}")
                print(f"{config.RED}Starting fresh session instead.{config.RESET}")

    app = AICoder()
    app.run()


if __name__ == "__main__":
    if "container" in os.environ:
        print("Sandbox:", os.environ.get("container", "unknown"))

    main()
