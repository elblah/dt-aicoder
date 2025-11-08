"""
Handler for internal tools in AI Coder.
"""

import shlex
import os
from typing import Dict, Any, Tuple

from ...utils import emsg, wmsg, imsg
from ...tool_manager.validator import format_validation_error
from ...tool_manager.validator import validate_tool_parameters, validate_function_signature
from ...tool_manager.internal_tools import INTERNAL_TOOL_FUNCTIONS
from ...tool_manager.file_tracker import track_file_edit, track_file_read
from ...tool_manager.approval_utils import check_rule_file
from ...tool_manager.approval_system import CancelAllToolCalls


DENIED_MESSAGE = "EXECUTION DENIED BY THE USER"


class InternalToolHandler:
    """Handles execution of internal tools."""

    def __init__(self, tool_registry, stats, approval_system, main_executor=None):
        self.tool_registry = tool_registry
        self.stats = stats
        self.approval_system = approval_system
        self.main_executor = main_executor
        self._command_info_printed = False

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

    def _normalize_arguments(self, arguments):
        """
        Normalize arguments to ensure they are in dictionary format.

        Note: Arguments should already be parsed by the time this is called,
        but we handle the case where they might still be a string for backward compatibility.
        """
        from ...utils import parse_json_arguments
        import json

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
            # Import config at the module level to avoid circular import issues
            from ... import config
            mode_msg = ""
            if getattr(self, 'yolo_mode', False):  # Use instance attribute
                mode_msg = "YOLO!"
            elif allow_session:
                mode_msg = "ALLOWED FOR SESSION!"
            elif auto_approved:
                mode_msg = "AUTO APPROVED!"
            if mode_msg:
                mode_msg = f"{config.BOLD}{config.RED}**{mode_msg}**{config.RESET}"

            # Check for dangerous patterns and show warning
            from ...tool_manager.internal_tools.run_shell_command import has_dangerous_patterns

            has_dangerous, reason = has_dangerous_patterns(command)
            if has_dangerous:
                print(f"   - [!] {reason} - requires manual approval")

            wmsg(f"\n   AI wants to run a command: {mode_msg}")
            print(f"    {config.BOLD}Command: {command}{config.RESET}")
            print(f"    Timeout: {timeout} seconds")
            self._command_info_printed = True

    def handle(self, tool_name: str, arguments: Dict[str, Any], tool_index: int = 0, total_tools: int = 0, yolo_mode: bool = False) -> Tuple[str, Dict[str, Any], bool]:
        """Handle execution of an internal tool."""

        # Import check_approval_rules here to avoid circular import issues
        from ...tool_manager.approval_utils import check_approval_rules

        # First check if it's in the standard internal tool functions
        func = INTERNAL_TOOL_FUNCTIONS.get(tool_name)

        if not func:
            self.stats.tool_errors += 1
            return (
                f"Error: Internal tool '{tool_name}' has no implementation.",
                self._current_tool_config,
                False,
            )

        # Validate internal tool call before execution
        is_valid, error_message = self._validate_internal_tool_call(
            tool_name,
            self._current_tool_config,
            arguments,
            "internal",
            tool_index,
            total_tools,
        )
        if not is_valid:
            self.stats.tool_errors += 1
            formatted_error = format_validation_error(
                tool_name, error_message, self._current_tool_config, arguments
            )
            return formatted_error, self._current_tool_config, False

        # Handle approval for internal tools
        auto_approved = self._current_tool_config.get("auto_approved", False)
        needs_approval = not auto_approved and not yolo_mode
        yolo_approval = not auto_approved and yolo_mode

        # Reset command info printed flag for this new tool call
        self._command_info_printed = False

        if yolo_approval:
            # YOLO mode - check user rules first
            if tool_name == "run_shell_command":
                command = arguments.get("command", "")
                has_dangerous, reason = check_approval_rules(command)
                if has_dangerous:
                    print(
                        f"   - [!] {reason} - YOLO mode respects user rules"
                    )
                    error_msg = f"Command denied by GLOBAL RULE: {command}"
                    return error_msg, self._current_tool_config, False
                approved, with_guidance = (not has_dangerous, False)
            else:
                approved, with_guidance = True, False
        elif needs_approval:
            prompt_message = self.approval_system.format_tool_prompt(
                tool_name, arguments, self._current_tool_config
            )
            # Check if prompt_message is a validation error
            if prompt_message.startswith("Error:"):
                # Return validation error directly
                return prompt_message, self._current_tool_config, False
            # Special handling for run_shell_command cache key generation
            if tool_name == "run_shell_command":
                # Generate a cache key based on the main command name for session approval
                command = arguments.get("command", "")
                try:
                    parts = shlex.split(command.strip())
                    if parts:
                        main_command = os.path.basename(parts[0])
                        cache_key = f"{tool_name}:{main_command}"
                    else:
                        cache_key = tool_name
                except (ValueError, ImportError):
                    cache_key = tool_name

                # Check for dangerous patterns in the current command (even if session approved)
                from ...tool_manager.internal_tools.run_shell_command import (
                    has_dangerous_patterns,
                )

                # ALWAYS check auto_deny rules first, even in YOLO mode
                auto_deny_file = os.path.expanduser(
                    "~/.config/aicoder/run_shell_command.auto_deny"
                )
                has_deny_match, deny_rule, _ = check_rule_file(
                    auto_deny_file, command, "deny"
                )
                if has_deny_match:
                    print(f"   - [X] Command auto denied: {deny_rule}")
                    print(f"   - Command was: {command}")
                    return DENIED_MESSAGE, self._current_tool_config, False
                has_dangerous, reason = has_dangerous_patterns(command)
                if has_dangerous:
                    # Found dangerous pattern - require manual approval
                    print(f"   - [!] {reason} - requires manual approval")
                else:
                    # Check user-configurable approval rules (ask and auto)
                    has_dangerous, reason = check_approval_rules(command)
                    if has_dangerous:
                        print(
                            f"   - [!] {reason} - requires manual approval"
                        )

                # Check if this specific command was approved for session AND is safe
                if cache_key in self.approval_system.tool_approvals_session:
                    if has_dangerous:
                        # Need to ask for approval despite session approval
                        approved, with_guidance = (
                            self.approval_system.request_user_approval(
                                prompt_message,
                                tool_name,
                                arguments,
                                self._current_tool_config,
                            )
                        )
                    else:
                        # Safe command and session approved - show command info but skip prompt
                        self._print_command_info_once(
                            arguments.get("command", ""),
                            arguments.get("timeout", 30),
                            auto_approved=auto_approved,
                            allow_session=True,
                        )
                        approved, with_guidance = True, False
                else:
                    # Need to ask for approval - temporarily use our cache key
                    original_generate_cache_key = (
                        self.approval_system._generate_approval_cache_key
                    )
                    self.approval_system._generate_approval_cache_key = (
                        lambda tn, args, exclude_args: cache_key
                    )

                    try:
                        approved, with_guidance = (
                            self.approval_system.request_user_approval(
                                prompt_message,
                                tool_name,
                                arguments,
                                self._current_tool_config,
                            )
                        )
                    finally:
                        # Restore original cache key function
                        self.approval_system._generate_approval_cache_key = original_generate_cache_key
            else:
                # Normal approval flow for other tools
                approved, with_guidance = (
                    self.approval_system.request_user_approval(
                        prompt_message,
                        tool_name,
                        arguments,
                        self._current_tool_config,
                    )
                )

            if needs_approval:  # Non-YOLO mode - check approval result
                if not approved:
                    # For denied tools, return with guidance flag if requested
                    show_main_prompt = with_guidance
                    return (
                        DENIED_MESSAGE,
                        self._current_tool_config,
                        show_main_prompt,
                    )

                # Store guidance flag for later use
                if with_guidance:
                    # We'll handle guidance after execution
                    pass
            else:  # YOLO mode - check if user rules denied it
                if not approved:
                    # User rules denied approval even in YOLO mode
                    show_main_prompt = with_guidance
                    return (
                        DENIED_MESSAGE,
                        self._current_tool_config,
                        show_main_prompt,
                    )
                else:
                    wmsg(f"\n{prompt_message}")
                    imsg("Auto approving... running YOLO MODE!")
        # If auto_approved is True, no approval needed - skip approval logic

        # Prepare arguments for execution
        try:
            arguments = self._prepare_tool_arguments(arguments)
        except ValueError as e:
            return str(e), self._current_tool_config, False
        
        # Check if user used diff-edit to modify the file
        if (
            hasattr(self.approval_system, "_diff_edit_result")
            and self.approval_system._diff_edit_result
        ):
            diff_edit_result = self.approval_system._diff_edit_result
            # Note: _diff_edit_result will be cleared in app.py after the notification is added

            # Format the result like a successful tool execution
            formatted_result = f"[✓] SUCCESS: {diff_edit_result['message']}\n\nAI Guidance: {diff_edit_result['ai_guidance']}"

            # Return the diff-edit result immediately
            return formatted_result, self._current_tool_config, False
        
        try:
            # Special handling for run_shell_command to pass tool_index and total_tools
            if tool_name == "run_shell_command":
                # Only show command info if we're not showing an approval
                if not needs_approval:
                    self._print_command_info_once(
                        arguments.get("command", ""),
                        arguments.get("timeout", 30),
                        auto_approved=auto_approved,
                        allow_session=False,
                    )
                    
                # Set yolo_mode flag for the print method
                self.yolo_mode = yolo_mode

                result = func(
                    **arguments,
                    tool_index=tool_index,
                    total_tools=total_tools,
                    stats=self.stats,
                )
            else:
                result = func(**arguments, stats=self.stats)

            # Track efficiency for file operations
            if (
                tool_name in ["edit_file", "write_file", "read_file"]
                and "path" in arguments
            ):
                if tool_name == "edit_file":
                    track_file_edit(
                        arguments["path"], self.tool_registry.message_history
                    )
                elif tool_name == "write_file":
                    track_file_edit(
                        arguments["path"], self.tool_registry.message_history
                    )
                elif tool_name == "read_file":
                    track_file_read(
                        arguments["path"], self.tool_registry.message_history
                    )

            # Handle guidance prompt after successful execution
            # Don't prompt for guidance here anymore - it's handled in the main loop
            # Return whether to show main prompt after execution
            show_main_prompt = False
            if not auto_approved and not yolo_mode and with_guidance:
                show_main_prompt = True

            return result, self._current_tool_config, show_main_prompt
        except CancelAllToolCalls:
            # Properly handle cancellation requests by re-raising the exception
            raise
        except Exception as e:
            # Use the executor's error handling method
            if hasattr(self.main_executor, '_handle_tool_execution_error'):
                return self.main_executor._handle_tool_execution_error(
                    tool_name, "internal", self._current_tool_config, e
                )
            else:
                # Fallback error handling
                self.stats.tool_errors += 1
                return f"Error executing internal tool '{tool_name}': {e}", self._current_tool_config, False