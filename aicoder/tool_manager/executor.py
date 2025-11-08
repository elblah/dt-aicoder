"""
Tool Executor for AI Coder - Handles execution of tool calls from the AI.
"""

import os
import json
import time
import urllib.request
import subprocess
import shlex
from typing import Dict, Any, List, Tuple

from ..utils import parse_json_arguments, emsg, wmsg, imsg
from datetime import datetime
from .. import config
from ..utils import colorize_diff_lines, make_readline_safe
from ..readline_history_manager import prompt_history_manager
from .internal_tools import INTERNAL_TOOL_FUNCTIONS
from .validator import (
    validate_tool_parameters,
    format_validation_error,
    validate_function_signature,
)
from .approval_system import ApprovalSystem
from .approval_utils import (
    check_approval_rules,
    check_rule_file
)
from .handlers import InternalToolHandler, CommandToolHandler, JsonRpcToolHandler, McpStdioToolHandler

# Global message queue for tools - simple and easy to access
pending_tool_messages = []

# readline functionality is handled by utils.make_readline_safe()

DENIED_MESSAGE = "EXECUTION DENIED BY THE USER"


class ToolExecutor:
    """Handles execution of tool calls from the AI."""

    def __init__(self, tool_registry, stats, animator):
        self.animator = animator
        self.tool_registry = tool_registry
        self.stats = stats
        self.approval_system = ApprovalSystem(tool_registry, stats, animator)
        # Simple list for tools to queue messages that should be added after tool results
        self.pending_tool_messages = pending_tool_messages
        # Initialize command info printed flag
        self._command_info_printed = False
        # Initialize handlers
        self.internal_handler = InternalToolHandler(tool_registry, stats, self.approval_system, self)
        self.command_handler = CommandToolHandler(tool_registry, stats, self.approval_system)
        self.jsonrpc_handler = JsonRpcToolHandler(tool_registry, stats, self.approval_system)
        self.mcp_stdio_handler = McpStdioToolHandler(tool_registry, stats, self.approval_system)

    def _handle_tool_execution_error(
        self, tool_name: str, tool_type: str, tool_config: Dict[str, Any], e: Exception, show_main_prompt: bool = False
    ) -> Tuple[str, Dict[str, Any], bool]:
        """
        Standardized error handling for tool execution.

        Returns:
            Tuple of (error_result, tool_config, show_main_prompt)
        """
        from .approval_system import CancelAllToolCalls
        
        self.stats.tool_errors += 1
        if isinstance(e, CancelAllToolCalls) or str(e) == "CANCEL_ALL_TOOL_CALLS":
            return "CANCEL_ALL_TOOL_CALLS", tool_config, False
        return (
            f"Error executing {tool_type} tool '{tool_name}': {e}",
            tool_config,
            show_main_prompt,
        )

    def _prepare_tool_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize and validate arguments for tool execution.

        Returns:
            Normalized arguments dictionary
        """
        # Normalize arguments to ensure they are in dictionary format
        arguments = self._normalize_arguments(arguments)

        # Final validation: ensure arguments is a dictionary for tool execution
        if not isinstance(arguments, dict):
            error_msg = (
                "ERROR: Invalid JSON format in arguments. "
                "The JSON string could not be parsed into a dictionary. "
                "Please ensure your JSON arguments are properly formatted with correct syntax, "
                "double quotes for strings, and proper escaping."
            )
            emsg(f" * {error_msg}")
            raise ValueError(error_msg)

        return arguments

    def _log_malformed_tool_call(self, tool_name: str, arguments_raw: str):
        """Log malformed tool calls to a file for debugging purposes."""
        # Only log if debug mode is enabled
        if not config.DEBUG:
            return

        try:
            # Create a timestamp for the log file and put it in /tmp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"/tmp/malformed_tool_call_{timestamp}.log"

            # Create the log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "tool_name": tool_name,
                "raw_arguments": arguments_raw,
                "error_type": "Malformed JSON",
            }

            # Write to log file
            with open(log_filename, "w") as f:
                json.dump(log_entry, f, indent=2)

            # File is automatically closed when exiting 'with' block

            wmsg(f" * Malformed tool call logged to {log_filename}")

        except Exception as e:
            emsg(f" * Failed to log malformed tool call: {e}")

    def _improved_json_parse(self, json_string):
        """
        Strict JSON parser that rejects malformed JSON rather than trying to fix it.
        This ensures that only properly formatted JSON is accepted.
        """
        if not isinstance(json_string, str):
            return json_string

        # Only attempt standard JSON parsing - no attempts to fix malformed JSON
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            # Raise the original error to reject malformed JSON outright
            raise json.JSONDecodeError(
                f"Invalid JSON format: {str(e)}. Please ensure your JSON is properly formatted with double quotes and correct syntax.",
                json_string,
                e.pos,
            )

    def _normalize_arguments(self, arguments):
        """
        Normalize arguments to ensure they are in dictionary format.

        Note: Arguments should already be parsed by the time this is called,
        but we handle the case where they might still be a string for backward compatibility.
        """
        # Handle any remaining string arguments (shouldn't happen if we parse earlier)
        if isinstance(arguments, str):
            try:
                arguments = parse_json_arguments(arguments)
            except (json.JSONDecodeError, ValueError):
                # If parsing fails, return the original value
                pass

        # Ensure arguments is a dictionary before using **
        if not isinstance(arguments, dict):
            # If arguments is still not a dict, try to convert common types
            if isinstance(arguments, list) and len(arguments) > 0:
                # If it's a list, use the first element if it's a dict
                if isinstance(arguments[0], dict):
                    arguments = arguments[0]
                else:
                    # Wrap the list in a dict
                    arguments = {"value": arguments}
            elif isinstance(arguments, (int, float, bool, type(None))):
                # If it's a primitive, wrap it in a dict
                arguments = {"value": arguments}
            elif isinstance(arguments, str):
                # If it's still a string, wrap it in a dict as content
                arguments = {"content": arguments}
            else:
                # Default to empty dict as fallback
                arguments = {}

        return arguments

    def execute_tool_calls(
        self, message: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], bool, bool]:
        """Executes tool calls from an AI message and returns the results."""
        tool_results = []
        cancel_all_active = False
        show_main_prompt = False  # Flag to indicate if we should return to main prompt after execution

        # Get total number of tool calls for progress tracking
        total_tools = len(message["tool_calls"]) if message.get("tool_calls") else 0

        for i, tool_call in enumerate(message["tool_calls"]):
            # Update stats
            self.stats.tool_calls += 1

            # Tool index is 1-based for user display
            tool_index = i + 1

            function_info = tool_call["function"]
            func_name = function_info["name"]

            wmsg(f"\n└─ AI wants to call tool: {func_name}")

            # Handle arguments - parse once at the beginning, use parsed version throughout
            arguments_raw = function_info["arguments"]
            arguments = None

            # Parse JSON once with our utility function
            try:
                arguments = parse_json_arguments(arguments_raw)
            except (json.JSONDecodeError, ValueError) as e:
                # Reject immediately if JSON is invalid
                error_msg = f"Error: Malformed JSON in tool call arguments for '{func_name}'. The AI generated invalid JSON that cannot be parsed. Please ensure your JSON is properly formatted with double quotes and correct syntax. Error details: {str(e)}"
                emsg(f" * {error_msg}")
                emsg(f" * Raw arguments: {arguments_raw}")
                wmsg(
                    " * This tool call has been rejected and will not be added to the message history to prevent session corruption."
                )

                # Log the malformed tool call to a file for debugging
                self._log_malformed_tool_call(func_name, arguments_raw)

                # Create an educational message for the AI (not a tool result)
                educational_message = {
                    "role": "user",
                    "content": f"SYSTEM ERROR: Your tool call for '{func_name}' was rejected due to invalid JSON format.\n\n"
                    f"Please ensure your JSON arguments are properly formatted:\n"
                    f' - Use double quotes (") for all strings and keys\n'
                    f" - Properly escape special characters\n"
                    f" - Check for missing commas and brackets\n"
                    f" - Validate JSON structure before sending\n\n"
                    f"Please correct your tool call and try again.",
                }
                tool_results.append(educational_message)

                # Skip processing this tool call entirely (no tool result will be generated)
                continue

                # Create an educational message for the AI
                educational_message = {
                    "role": "user",
                    "content": f"SYSTEM ERROR: Your tool call for '{func_name}' was rejected because it contained invalid arguments. Expected JSON string or parsed object.\n"
                    f"Please correct your tool call and try again.",
                }
                tool_results.append(educational_message)

                # Skip processing this tool call entirely
                continue

            # If arguments is None, we had an error and already continued
            if arguments is None:
                continue

            # Get tool configuration to handle parameter hiding and truncation
            tool_config_for_display = self.tool_registry.mcp_tools.get(func_name, {})

            # Handle parameter hiding and truncation generically for display only
            hidden_parameters = tool_config_for_display.get("hidden_parameters", [])
            display_args = (
                arguments.copy() if isinstance(arguments, dict) else arguments
            )

            # Apply parameter hiding for display (only if arguments is a dict)
            if isinstance(display_args, dict):
                for param in hidden_parameters:
                    if param in display_args:
                        display_args[param] = "[HIDDEN]"

                # Apply truncation for long string values (but not for hidden parameters)
                for key, value in display_args.items():
                    if (
                        key not in hidden_parameters
                        and isinstance(value, str)
                        and len(value) > config.get_effective_truncation_limit()
                    ):
                        display_args[key] = (
                            value[: config.get_effective_truncation_limit()]
                            + "... [truncated]"
                        )

            # Check if arguments should be hidden completely
            hide_arguments = tool_config_for_display.get("hide_arguments", False)
            if not hide_arguments:
                print(f"   - Arguments: {display_args}")

            # If cancel all is active, skip execution and mark as cancelled
            if cancel_all_active:
                emsg(" * Skipping tool call (cancel all active)...")
                result = "CANCELLED_BY_USER"
                tool_config_for_display = None
                show_main_prompt_for_tool = False
            else:
                (
                    result,
                    tool_config_for_display,
                    show_main_prompt_for_tool,
                ) = self.execute_tool(func_name, arguments, tool_index, total_tools)

                # Check if this result indicates cancel all
                if result == "CANCEL_ALL_TOOL_CALLS":
                    cancel_all_active = True
                    print(
                        f"{config.RED} * Cancel all activated for remaining tool calls{config.RESET}"
                    )

            # Check if we added an educational message for this tool call (indicating rejection)
            educational_messages = [
                tr
                for tr in tool_results
                if tr.get("role") == "user" and "SYSTEM ERROR" in tr.get("content", "")
            ]
            if (
                educational_messages
                and educational_messages[-1].get("content", "").find(func_name) != -1
            ):
                # This tool call was rejected, so we don't create a tool result entry
                # The educational message is already in tool_results
                continue

            if not cancel_all_active:
                # Check if results should be hidden based on tool configuration
                hide_results = False
                if tool_config_for_display:
                    hide_results = tool_config_for_display.get("hide_results", False)

                if hide_results:
                    # Don't print anything for hidden results
                    pass
                else:
                    # Truncate result display for cleaner output (but not if guidance is requested)
                    result_display = str(result)
                    # Don't truncate if guidance is enabled - user needs full output for context
                    if (
                        len(result_display) > config.get_effective_truncation_limit()
                        and show_main_prompt_for_tool
                    ):
                        result_display = (
                            result_display[: config.get_effective_truncation_limit()]
                            + "... [truncated]"
                        )
                    print(f"   - Result: {result_display}")

            # Ensure every tool call has a corresponding result entry (unless it was rejected)
            # Even if cancel_all is active, we still add the result for the tool that triggered it
            tool_result_entry = {
                "tool_call_id": tool_call["id"],
                "role": "tool",
                "name": func_name,
                "content": str(result),
            }

            # Verify that the tool_call_id is not None or empty
            if not tool_call["id"]:
                emsg(f" * Warning: Empty tool_call_id for {func_name}")

            tool_results.append(tool_result_entry)

            # If any tool requested to show main prompt, set the flag
            if show_main_prompt_for_tool:
                show_main_prompt = True

        # Add any pending tool messages (for plugins, ruff, etc.)
        for message in pending_tool_messages:
            tool_results.append(message)
        # Clear the pending messages list
        pending_tool_messages.clear()

        return tool_results, cancel_all_active, show_main_prompt

    def _print_command_info_once(
        self,
        command: str,
        timeout: int = 30,
        auto_approved: bool = False,
        allow_session: bool = False,
    ):
        """Print command information only once per tool call.

        Args:
            command: The shell command being executed
            timeout: Timeout in seconds (default: 30)
        """
        if command and not self._command_info_printed:
            mode_msg = ""
            if config.YOLO_MODE:
                mode_msg = "YOLO!"
            elif allow_session:
                mode_msg = "ALLOWED FOR SESSION!"
            elif auto_approved:
                mode_msg = "AUTO APPROVED!"
            if mode_msg:
                mode_msg = f"{config.BOLD}{config.RED}**{mode_msg}**{config.RESET}"

            # Check for dangerous patterns and show warning
            from .internal_tools.run_shell_command import has_dangerous_patterns

            has_dangerous, reason = has_dangerous_patterns(command)
            if has_dangerous:
                print(f"   - [!] {reason} - requires manual approval")

            wmsg(f"\n   AI wants to run a command: {mode_msg}")
            print(f"    {config.BOLD}Command: {command}{config.RESET}")
            print(f"    Timeout: {timeout} seconds")
            self._command_info_printed = True

    def _validate_internal_tool_call(
        self,
        tool_name: str,
        tool_config: Dict[str, Any],
        arguments: Dict[str, Any],
        tool_type: str,
        tool_index: int = 0,
        total_tools: int = 0,
    ) -> Tuple[bool, str]:
        """
        Validate an internal tool call before execution.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate tool parameters against schema
        is_valid, error_message = validate_tool_parameters(
            tool_name, tool_config, arguments
        )
        if not is_valid:
            return False, error_message

        # Validate function signature
        # Define parameters that are automatically provided by the executor
        additional_params = ["stats"]
        if tool_name == "run_shell_command":
            additional_params.extend(["tool_index", "total_tools"])

        is_valid, error_message = validate_function_signature(
            tool_name, tool_config, arguments, additional_params
        )
        if not is_valid:
            return False, error_message

        return True, ""

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_index: int = 0,
        total_tools: int = 0,
    ) -> Tuple[str, Dict[str, Any], bool]:
        """Execute an MCP tool based on its configuration."""
        # Check if tool is disabled due to planning mode
        try:
            from ..planning_mode import get_planning_mode

            planning_mode = get_planning_mode()
            if planning_mode.should_disable_tool(tool_name):
                return (
                    f"Error: Tool '{tool_name}' is disabled in planning mode. Planning mode only allows read-only operations. You **MUST** respect planning mode and **NOT** even **TRY ANY** write operation.",
                    {},
                    False,
                )
        except ImportError:
            pass  # Planning mode not available

        # Track tool execution time
        tool_start_time = time.time()
        tool_config = {}  # Initialize tool_config to empty dict
        try:
            tool_config = self.tool_registry.mcp_tools.get(tool_name)

            # Special handling for run_shell_command to enable dynamic auto-approval
            if tool_name == "run_shell_command" and tool_config:
                from .internal_tools.run_shell_command import get_dynamic_tool_config

                tool_config = get_dynamic_tool_config(tool_config, arguments)

            if not tool_config:
                # Check if this is a tool from an MCP server
                for server_name, (_, tools) in self.tool_registry.mcp_servers.items():
                    if tool_name in tools:
                        tool_config = {"type": "mcp-stdio", "server": server_name}
                        break

                if not tool_config:
                    return f"Error: Tool '{tool_name}' not found.", {}, False

            if config.DEBUG:
                print(f"DEBUG: Executing tool {tool_name} with config: {tool_config}")

            tool_type = tool_config.get("type")

            if tool_type == "internal":
                # Special handling for run_shell_command to enable dynamic auto-approval
                if tool_name == "run_shell_command" and tool_config:
                    from .internal_tools.run_shell_command import get_dynamic_tool_config
                    tool_config = get_dynamic_tool_config(tool_config, arguments)

                # Use the internal handler
                self.internal_handler._current_tool_config = tool_config
                self.internal_handler.yolo_mode = config.YOLO_MODE
                return self.internal_handler.handle(tool_name, arguments, tool_index, total_tools, config.YOLO_MODE)

            elif tool_type == "command":
                # Use the command handler
                self.command_handler._current_tool_config = tool_config
                return self.command_handler.handle(tool_name, arguments, config)

            elif tool_type == "jsonrpc":
                # Use the JSON-RPC handler
                self.jsonrpc_handler._current_tool_config = tool_config
                return self.jsonrpc_handler.handle(tool_name, arguments, config)

            elif tool_type == "mcp-stdio":
                # Use the MCP stdio handler
                self.mcp_stdio_handler._current_tool_config = tool_config
                return self.mcp_stdio_handler.handle(tool_name, arguments, config)

            else:
                self.stats.tool_errors += 1
                return (
                    f"Error: Unknown tool type '{tool_type}' for tool '{tool_name}'.",
                    tool_config,
                    False,
                )
        except Exception as e:
            self.stats.tool_errors += 1
            # Check if this is the cancellation exception from approval system
            from .approval_system import CancelAllToolCalls
            if isinstance(e, CancelAllToolCalls) or str(e) == "CANCEL_ALL_TOOL_CALLS":
                return "CANCEL_ALL_TOOL_CALLS", tool_config, False
            return f"Error in tool execution system: {e}", tool_config, False
        finally:
            # Record time spent on tool call
            self.stats.tool_time_spent += time.time() - tool_start_time