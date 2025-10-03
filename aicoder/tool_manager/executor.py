"""
Tool Executor for AI Coder - Handles execution of tool calls from the AI.
"""

import os
import json
import time
import urllib.request
import subprocess
from typing import Dict, Any, List, Tuple

from ..utils import parse_json_arguments
from datetime import datetime
from .. import config
from ..utils import colorize_diff_lines, make_readline_safe
from .internal_tools import INTERNAL_TOOL_FUNCTIONS
from .validator import (
    validate_tool_parameters,
    format_validation_error,
    validate_function_signature,
)
from .approval_system import ApprovalSystem

# Import readline to enable readline functionality
try:
    import readline
except ImportError:
    # readline is not available on this platform
    pass

DENIED_MESSAGE = "EXECUTION DENIED BY THE USER"


class ToolExecutor:
    """Handles execution of tool calls from the AI."""

    def __init__(self, tool_registry, stats, animator):
        self.animator = animator
        self.tool_registry = tool_registry
        self.stats = stats
        self.approval_system = ApprovalSystem(tool_registry, stats, animator)

    def _log_malformed_tool_call(self, tool_name: str, arguments_raw: str):
        """Log malformed tool calls to a file for debugging purposes."""
        # Only log if debug mode is enabled
        if not config.DEBUG:
            return
            
        try:
            # Create a timestamp for the log file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"malformed_tool_call_{timestamp}.log"

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

            print(f"{config.YELLOW} * Malformed tool call logged to {log_filename}{config.RESET}")
        except Exception as e:
            print(f"{config.RED} * Failed to log malformed tool call: {e}{config.RESET}")

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
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Executes tool calls from an AI message and returns the results."""
        tool_results = []
        guidance_messages = []  # Collect guidance messages separately
        cancel_all_active = False

        # Get total number of tool calls for progress tracking
        total_tools = len(message["tool_calls"]) if message.get("tool_calls") else 0

        for i, tool_call in enumerate(message["tool_calls"]):
            # Update stats
            self.stats.tool_calls += 1

            # Tool index is 1-based for user display
            tool_index = i + 1

            function_info = tool_call["function"]
            func_name = function_info["name"]

            print(f"\n{config.YELLOW}└─ AI wants to call tool: {func_name}{config.RESET}")

            # Handle arguments - parse once at the beginning, use parsed version throughout
            arguments_raw = function_info["arguments"]
            arguments = None

            # Parse JSON once with our utility function
            try:
                arguments = parse_json_arguments(arguments_raw)
            except (json.JSONDecodeError, ValueError) as e:
                # Reject immediately if JSON is invalid
                error_msg = f"Error: Malformed JSON in tool call arguments for '{func_name}'. The AI generated invalid JSON that cannot be parsed. Please ensure your JSON is properly formatted with double quotes and correct syntax. Error details: {str(e)}"
                print(f"{config.RED} * {error_msg}{config.RESET}")
                print(f"{config.RED} * Raw arguments: {arguments_raw}{config.RESET}")
                print(
                    f"{config.YELLOW} * This tool call has been rejected and will not be added to the message history to prevent session corruption.{config.RESET}"
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
                        and len(value) > config.DEFAULT_TRUNCATION_LIMIT
                    ):
                        display_args[key] = (
                            value[:config.DEFAULT_TRUNCATION_LIMIT] + "... [truncated]"
                        )

            # Check if arguments should be hidden completely
            hide_arguments = tool_config_for_display.get("hide_arguments", False)
            if not hide_arguments:
                print(f"   - Arguments: {display_args}")

            # If cancel all is active, skip execution and mark as cancelled
            if cancel_all_active:
                print(f"{config.RED} * Skipping tool call (cancel all active)...{config.RESET}")
                result = "CANCELLED_BY_USER"
                tool_config_for_display = None
                guidance_content = None
            else:
                result, tool_config_for_display, guidance_content = self.execute_tool(
                    func_name, arguments, tool_index, total_tools
                )

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
                    # Truncate result display for cleaner output (increased limit for diffs)
                    result_display = str(result)
                    if len(result_display) > config.DEFAULT_TRUNCATION_LIMIT:
                        result_display = (
                            result_display[:config.DEFAULT_TRUNCATION_LIMIT]
                            + "... [truncated]"
                        )
                    print(f"   - Result: {result_display}")

            # Ensure every tool call has a corresponding result entry (unless it was rejected)
            tool_result_entry = {
                "tool_call_id": tool_call["id"],
                "role": "tool",
                "name": func_name,
                "content": str(result),
            }

            # Verify that the tool_call_id is not None or empty
            if not tool_call["id"]:
                print(f"{config.RED} * Warning: Empty tool_call_id for {func_name}{config.RESET}")

            tool_results.append(tool_result_entry)

            # Collect guidance messages with tool call ID references instead of adding immediately
            if guidance_content and guidance_content.strip():
                guidance_messages.append(
                    {
                        "tool_call_id": tool_call["id"],
                        "content": guidance_content,
                        "tool_name": func_name,
                    }
                )

        # Add all guidance messages after all tool results
        # This ensures proper protocol adherence where tool call requests are immediately followed by results
        for guidance in guidance_messages:
            guidance_message = {
                "role": "user",
                "content": f"User guidance for tool call ID {guidance['tool_call_id']} ({guidance['tool_name']}): {guidance['content']}",
            }
            tool_results.append(guidance_message)

        return tool_results, cancel_all_active

    def _handle_guidance_prompt(self, with_guidance: bool) -> str:
        """Handle guidance prompt for both approved and denied tools.

        Args:
            with_guidance: Whether guidance was requested

        Returns:
            Guidance content or None if not requested or cancelled
        """
        guidance_content = None
        if with_guidance:
            try:
                self.animator.stop_cursor_blinking()
                guidance_prompt = f"{config.BOLD}{config.GREEN}Guidance: {config.RESET}"
                safe_guidance_prompt = make_readline_safe(guidance_prompt)
                guidance_content = input(safe_guidance_prompt).strip()
            except (EOFError, KeyboardInterrupt):
                # If user cancels guidance input, proceed without guidance
                guidance_content = None
            self.animator.start_cursor_blinking()
        return guidance_content

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
    ) -> Tuple[str, Dict[str, Any], str]:
        """Execute an MCP tool based on its configuration."""
        # Track tool execution time
        tool_start_time = time.time()
        tool_config = {}  # Initialize tool_config to empty dict
        try:
            tool_config = self.tool_registry.mcp_tools.get(tool_name)
            if not tool_config:
                # Check if this is a tool from an MCP server
                for server_name, (_, tools) in self.tool_registry.mcp_servers.items():
                    if tool_name in tools:
                        tool_config = {"type": "mcp-stdio", "server": server_name}
                        break

                if not tool_config:
                    return f"Error: Tool '{tool_name}' not found.", {}, None

            if config.DEBUG:
                print(f"DEBUG: Executing tool {tool_name} with config: {tool_config}")

            tool_type = tool_config.get("type")

            if tool_type == "internal":
                # First check if it's in the standard internal tool functions
                func = INTERNAL_TOOL_FUNCTIONS.get(tool_name)
                if not func:
                    # Check if it's a plugin-based internal tool
                    # Plugin tools are registered directly in the executor's INTERNAL_TOOL_FUNCTIONS
                    if hasattr(self, "INTERNAL_TOOL_FUNCTIONS"):
                        func = self.INTERNAL_TOOL_FUNCTIONS.get(tool_name)

                if not func:
                    self.stats.tool_errors += 1
                    return (
                        f"Error: Internal tool '{tool_name}' has no implementation.",
                        tool_config,
                        None,
                    )

                # Validate internal tool call before execution
                is_valid, error_message = self._validate_internal_tool_call(
                    tool_name,
                    tool_config,
                    arguments,
                    tool_type,
                    tool_index,
                    total_tools,
                )
                if not is_valid:
                    self.stats.tool_errors += 1
                    formatted_error = format_validation_error(
                        tool_name, error_message, tool_config, arguments
                    )
                    return formatted_error, tool_config, None

                try:
                    # Handle approval for internal tools
                    auto_approved = tool_config.get("auto_approved", False)
                    needs_approval = not auto_approved and not config.YOLO_MODE
                    yolo_approval = not auto_approved and config.YOLO_MODE
                    
                    if needs_approval or yolo_approval:
                        prompt_message = self.approval_system.format_tool_prompt(
                            tool_name, arguments, tool_config
                        )
                        # Check if prompt_message is a validation error
                        if prompt_message.startswith("Error:"):
                            # Return validation error directly
                            return prompt_message, tool_config, None

                        if needs_approval:  # Non-YOLO mode - ask user
                            approved, with_guidance = (
                                self.approval_system.request_user_approval(
                                    prompt_message, tool_name, arguments, tool_config
                                )
                            )
                            if not approved:
                                # Handle guidance prompt even for denied tools
                                guidance_content = self._handle_guidance_prompt(
                                    with_guidance
                                )
                                return DENIED_MESSAGE, tool_config, guidance_content

                            # Store guidance flag for later use
                            if with_guidance:
                                # We'll handle guidance after execution
                                pass
                        else:  # YOLO mode - auto approve but show the prompt
                            print(f"\n{config.YELLOW}{prompt_message}{config.RESET}")
                            print(f"{config.GREEN}Auto approving... running YOLO MODE!{config.RESET}")

                    # Normalize arguments to ensure they are in dictionary format
                    arguments = self._normalize_arguments(arguments)

                    # Final validation: ensure arguments is a dictionary for tool execution
                    if not isinstance(arguments, dict):
                        error_msg = (
                            f"ERROR: Invalid JSON format in arguments for tool '{tool_name}'. "
                            f"The JSON string could not be parsed into a dictionary. "
                            f"Please ensure your JSON arguments are properly formatted with correct syntax, "
                            f"double quotes for strings, and proper escaping."
                        )
                        print(f"{config.RED} * {error_msg}{config.RESET}")
                        return error_msg, tool_config, None

                    # Special handling for run_shell_command to pass tool_index and total_tools
                    if tool_name == "run_shell_command":
                        result = func(
                            **arguments,
                            tool_index=tool_index,
                            total_tools=total_tools,
                            stats=self.stats,
                        )
                    else:
                        result = func(**arguments, stats=self.stats)

                    # Handle guidance prompt after successful execution
                    guidance_content = None
                    if not auto_approved and not config.YOLO_MODE and with_guidance:
                        guidance_content = self._handle_guidance_prompt(with_guidance)

                    return result, tool_config, guidance_content
                except Exception as e:
                    self.stats.tool_errors += 1
                    if str(e) == "CANCEL_ALL_TOOL_CALLS":
                        return "CANCEL_ALL_TOOL_CALLS", tool_config, None
                    return (
                        f"Error executing internal tool '{tool_name}': {e}",
                        tool_config,
                        None,
                    )

            elif tool_type == "command":
                # 1) Dynamic description: allow tools to supply a runtime description
                if isinstance(tool_config, dict) and tool_config.get(
                    "tool_description_command"
                ):
                    try:
                        if config.DEBUG:
                            print(
                                f"DEBUG: Running tool_description_command for {tool_name}"
                            )
                            print(f"DEBUG: Current working directory: {os.getcwd()}")
                        desc_proc = subprocess.run(
                            tool_config["tool_description_command"],
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=5,
                        )
                        if desc_proc.returncode == 0:
                            desc_lines = (desc_proc.stdout or "").strip().splitlines()
                            if desc_lines:
                                dynamic_desc = "\n".join(desc_lines).strip()
                                if dynamic_desc:
                                    tool_config = dict(tool_config)
                                    old_desc = tool_config.get("description", "")
                                    tool_config["description"] = dynamic_desc
                                    if config.DEBUG:
                                        print(
                                            f"DEBUG: Updated description for {tool_name}"
                                        )
                                        print(f"DEBUG: Old description: {old_desc}")
                                        print(
                                            f"DEBUG: New description length: {len(dynamic_desc)}"
                                        )
                        else:
                            print(
                                f"WARNING: tool_description_command failed for {tool_name} with return code {desc_proc.returncode}"
                            )
                            if config.DEBUG:
                                print(f"DEBUG: stderr: {desc_proc.stderr}")
                                print(f"DEBUG: stdout: {desc_proc.stdout}")
                    except subprocess.TimeoutExpired:
                        print(
                            f"ERROR: tool_description_command for {tool_name} timed out"
                        )
                    except Exception as e:
                        print(
                            f"ERROR: Exception in tool_description_command for {tool_name}: {e}"
                        )
                        if config.DEBUG:
                            import traceback

                            traceback.print_exc()

                # 2) Append to system prompt if command specifies it
                if isinstance(tool_config, dict) and tool_config.get(
                    "append_to_system_prompt_command"
                ):
                    try:
                        if config.DEBUG:
                            print(
                                f"DEBUG: Running append_to_system_prompt_command for {tool_name}"
                            )
                            print(f"DEBUG: Current working directory: {os.getcwd()}")
                        append_proc = subprocess.run(
                            tool_config["append_to_system_prompt_command"],
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=5,
                        )
                        if append_proc.returncode == 0:
                            append_content = (append_proc.stdout or "").strip()
                            if append_content:
                                # Augment the system prompt
                                if (
                                    self.tool_registry.message_history
                                    and hasattr(
                                        self.tool_registry.message_history, "messages"
                                    )
                                    and self.tool_registry.message_history.messages
                                ):
                                    self.tool_registry.message_history.messages[0][
                                        "content"
                                    ] += f"\n\n{append_content}"
                        else:
                            print(
                                f"WARNING: append_to_system_prompt_command failed for {tool_name} with return code {append_proc.returncode}"
                            )
                            if config.DEBUG:
                                print(f"DEBUG: stderr: {append_proc.stderr}")
                                print(f"DEBUG: stdout: {append_proc.stdout}")
                    except subprocess.TimeoutExpired:
                        print(
                            f"ERROR: append_to_system_prompt_command for {tool_name} timed out"
                        )
                    except Exception as e:
                        print(
                            f"ERROR: Exception in append_to_system_prompt_command for {tool_name}: {e}"
                        )
                        if config.DEBUG:
                            import traceback

                            traceback.print_exc()

                try:
                    # Handle approval
                    auto_approved = tool_config.get("auto_approved", False)
                    if not auto_approved and not config.YOLO_MODE:
                        # Check for preview command first
                        preview_command = tool_config.get("preview_command")
                        if preview_command:
                            formatted_preview = preview_command.format(**arguments)
                            # Check if we should colorize the command
                            should_colorize_diff = tool_config.get(
                                "colorize_diff_lines", False
                            )
                            if should_colorize_diff:
                                formatted_preview = colorize_diff_lines(
                                    formatted_preview
                                )
                            print(f"   - Preview command: {formatted_preview}")
                            try:
                                preview_result = subprocess.run(
                                    formatted_preview,
                                    shell=True,
                                    capture_output=True,
                                    text=True,
                                    encoding="utf-8",
                                    timeout=60,
                                )
                                if preview_result.stdout.strip():
                                    print(f"{config.BLUE}--- PREVIEW OUTPUT ---{config.RESET}")
                                    # Check if we should colorize the preview output
                                    output = preview_result.stdout.rstrip()
                                    if should_colorize_diff:
                                        output = colorize_diff_lines(output)
                                    print(output)
                                if preview_result.stderr.strip():
                                    print(f"{config.RED}--- PREVIEW STDERR ---{config.RESET}")
                                    output = preview_result.stderr.rstrip()
                                    if should_colorize_diff:
                                        output = colorize_diff_lines(output)
                                    print(output)
                            except Exception as e:
                                print(f"{config.RED}Error running preview command: {e}{config.RESET}")

                        prompt_message = self.approval_system.format_tool_prompt(
                            tool_name, arguments, tool_config
                        )
                        # Check if prompt_message is a validation error
                        if prompt_message.startswith("Error:"):
                            # Return validation error directly
                            return prompt_message, tool_config, None

                        approved, with_guidance = (
                            self.approval_system.request_user_approval(
                                prompt_message, tool_name, arguments, tool_config
                            )
                        )
                        if not approved:
                            # Handle guidance prompt even for denied tools
                            guidance_content = self._handle_guidance_prompt(
                                with_guidance
                            )
                            return DENIED_MESSAGE, tool_config, guidance_content

                    # Normalize arguments to ensure they are in dictionary format
                    arguments = self._normalize_arguments(arguments)

                    command = tool_config["command"].format(**arguments)
                    # Print the executing command with potential colorization
                    should_colorize_diff = tool_config.get("colorize_diff_lines", False)
                    display_command = command
                    if should_colorize_diff:
                        display_command = colorize_diff_lines(command)
                    print(f"   - Executing command: {display_command}")

                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        timeout=60,
                    )
                    if result.returncode != 0:
                        self.stats.tool_errors += 1

                    # Check if we should colorize the output
                    should_colorize_diff = tool_config.get("colorize_diff_lines", False)

                    # Format command output nicely
                    result_lines = []
                    if result.stdout.strip():
                        result_lines.append(f"{config.BLUE}--- STDOUT ---{config.RESET}")
                        output = result.stdout.rstrip()
                        if should_colorize_diff:
                            output = colorize_diff_lines(output)
                        result_lines.append(output)
                    if result.stderr.strip():
                        result_lines.append(f"{config.RED}--- STDERR ---{config.RESET}")
                        output = result.stderr.rstrip()
                        if should_colorize_diff:
                            output = colorize_diff_lines(output)
                        result_lines.append(output)
                    result_lines.append(f"--- EXIT CODE: {result.returncode} ---")

                    # Handle guidance prompt after successful execution
                    guidance_content = None
                    if not auto_approved and not config.YOLO_MODE and with_guidance:
                        guidance_content = self._handle_guidance_prompt(with_guidance)

                    return "\n".join(result_lines), tool_config, guidance_content
                except Exception as e:
                    self.stats.tool_errors += 1
                    if str(e) == "CANCEL_ALL_TOOL_CALLS":
                        return "CANCEL_ALL_TOOL_CALLS", tool_config, None
                    return (
                        f"Error executing command tool '{tool_name}': {e}",
                        tool_config,
                        None,
                    )

            elif tool_type == "jsonrpc":
                try:
                    # Handle approval
                    auto_approved = tool_config.get("auto_approved", False)
                    if not auto_approved and not config.YOLO_MODE:
                        prompt_message = self.approval_system.format_tool_prompt(
                            tool_name, arguments, tool_config
                        )
                        # Check if prompt_message is a validation error
                        if prompt_message.startswith("Error:"):
                            # Return validation error directly
                            return prompt_message, tool_config, None

                        approved, with_guidance = (
                            self.approval_system.request_user_approval(
                                prompt_message, tool_name, arguments, tool_config
                            )
                        )
                        if not approved:
                            # Handle guidance prompt even for denied tools
                            guidance_content = self._handle_guidance_prompt(
                                with_guidance
                            )
                            return DENIED_MESSAGE, tool_config, guidance_content

                    # Normalize arguments to ensure they are in dictionary format
                    arguments = self._normalize_arguments(arguments)

                    url = tool_config["url"]
                    method = tool_config["method"]
                    payload = {
                        "jsonrpc": "2.0",
                        "method": method,
                        "params": arguments,
                        "id": 1,
                    }
                    print(f"   - Executing JSON-RPC call to {url} with method {method}")
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req) as response:
                        rpc_result = json.loads(response.read().decode("utf-8"))
                        if "error" in rpc_result:
                            self.stats.tool_errors += 1
                            return json.dumps(rpc_result["error"]), tool_config, None
                        result = json.dumps(rpc_result.get("result"))

                        # Handle guidance prompt after successful execution
                        guidance_content = None
                        if not auto_approved and not config.YOLO_MODE and with_guidance:
                            guidance_content = self._handle_guidance_prompt(
                                with_guidance
                            )

                        return result, tool_config, guidance_content
                except Exception as e:
                    self.stats.tool_errors += 1
                    if str(e) == "CANCEL_ALL_TOOL_CALLS":
                        return "CANCEL_ALL_TOOL_CALLS", tool_config, None
                    return (
                        f"Error executing JSON-RPC tool '{tool_name}': {e}",
                        tool_config,
                        None,
                    )

            elif tool_type == "mcp-stdio":
                try:
                    server_name = tool_config.get("server") or tool_name
                    if server_name not in self.tool_registry.mcp_servers:
                        # Discover tools if server not yet initialized
                        self.tool_registry._discover_mcp_server_tools(server_name)

                    if server_name not in self.tool_registry.mcp_servers:
                        raise Exception(f"MCP server {server_name} not available")

                    process, _ = self.tool_registry.mcp_servers[server_name]

                    def send_request(request_data):
                        js = json.dumps(request_data) + "\n"
                        process.stdin.write(js)
                        process.stdin.flush()
                        if request_data.get("id") is not None:
                            response_line = process.stdout.readline()
                            return json.loads(response_line)
                        return None

                    # Handle approval
                    auto_approved = tool_config.get("auto_approved", False)
                    if not auto_approved and not config.YOLO_MODE:
                        prompt_message = self.approval_system.format_tool_prompt(
                            tool_name, arguments, tool_config
                        )
                        # Check if prompt_message is a validation error
                        if prompt_message.startswith("Error:"):
                            # Return validation error directly
                            return prompt_message, tool_config, None

                        approved, with_guidance = (
                            self.approval_system.request_user_approval(
                                prompt_message, tool_name, arguments, tool_config
                            )
                        )
                        if not approved:
                            # Handle guidance prompt even for denied tools
                            guidance_content = self._handle_guidance_prompt(
                                with_guidance
                            )
                            return DENIED_MESSAGE, tool_config, guidance_content

                    # Execute tool call
                    tool_call_request = {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": tool_name, "arguments": arguments},
                    }

                    response = send_request(tool_call_request)
                    if not response or "result" not in response:
                        raise Exception(f"Tool call failed: {response}")

                    result = json.dumps(response["result"])

                    # Handle guidance prompt after successful execution
                    guidance_content = None
                    if not auto_approved and not config.YOLO_MODE and with_guidance:
                        guidance_content = self._handle_guidance_prompt(with_guidance)

                    return result, tool_config, guidance_content
                except Exception as e:
                    self.stats.tool_errors += 1
                    if str(e) == "CANCEL_ALL_TOOL_CALLS":
                        return "CANCEL_ALL_TOOL_CALLS", tool_config, None
                    return (
                        f"Error executing MCP stdio tool '{tool_name}': {e}",
                        tool_config,
                        None,
                    )

            else:
                self.stats.tool_errors += 1
                return (
                    f"Error: Unknown tool type '{tool_type}' for tool '{tool_name}'.",
                    tool_config,
                    None,
                )
        except Exception as e:
            self.stats.tool_errors += 1
            if str(e) == "CANCEL_ALL_TOOL_CALLS":
                return "CANCEL_ALL_TOOL_CALLS", tool_config, None
            return f"Error in tool execution system: {e}", tool_config, None
        finally:
            # Record time spent on tool call
            self.stats.tool_time_spent += time.time() - tool_start_time
