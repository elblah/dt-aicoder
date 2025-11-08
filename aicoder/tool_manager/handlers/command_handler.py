"""
Handler for command tools in AI Coder.
"""

import subprocess
from typing import Dict, Any, Tuple

from ...utils import emsg, colorize_diff_lines
from ...tool_manager.approval_system import CancelAllToolCalls, DENIED_MESSAGE


class CommandToolHandler:
    """Handles execution of command tools."""

    def __init__(self, tool_registry, stats, approval_system):
        self.tool_registry = tool_registry
        self.stats = stats
        self.approval_system = approval_system

    def handle(self, tool_name: str, arguments: Dict[str, Any], config_module) -> Tuple[str, Dict[str, Any], bool]:
        """Handle execution of a command tool."""
        tool_config = self._current_tool_config
        
        # 1) Dynamic description: allow tools to supply a runtime description
        if isinstance(tool_config, dict) and tool_config.get(
            "tool_description_command"
        ):
            try:
                if config_module.DEBUG:
                    print(
                        f"DEBUG: Running tool_description_command for {tool_name}"
                    )
                    print(f"DEBUG: Current working directory: {self.tool_registry.message_history.current_directory if hasattr(self.tool_registry.message_history, 'current_directory') else 'unknown'}")
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
                            if config_module.DEBUG:
                                print(
                                    f"DEBUG: Updated description for {tool_name}"
                                )
                                print(f"DEBUG: Old description: {old_desc}")
                                print(
                                    f"DEBUG: New description length: {len(dynamic_desc)}"
                                )
            except subprocess.TimeoutExpired:
                print(
                    f"ERROR: tool_description_command for {tool_name} timed out"
                )
            except Exception as e:
                print(
                    f"ERROR: Exception in tool_description_command for {tool_name}: {e}"
                )
                if config_module.DEBUG:
                    import traceback

                    traceback.print_exc()

        # 2) Append to system prompt if command specifies it
        if isinstance(tool_config, dict) and tool_config.get(
            "append_to_system_prompt_command"
        ):
            try:
                if config_module.DEBUG:
                    print(
                        f"DEBUG: Running append_to_system_prompt_command for {tool_name}"
                    )
                    print(f"DEBUG: Current working directory: {self.tool_registry.message_history.current_directory if hasattr(self.tool_registry.message_history, 'current_directory') else 'unknown'}")
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
                    if config_module.DEBUG:
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
                if config_module.DEBUG:
                    import traceback

                    traceback.print_exc()

        try:
            # Handle approval
            auto_approved = tool_config.get("auto_approved", False)
            if not auto_approved and not config_module.YOLO_MODE:
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
                            print(
                                f"{config_module.BLUE}--- PREVIEW OUTPUT ---{config_module.RESET}"
                            )
                            # Check if we should colorize the preview output
                            output = preview_result.stdout.rstrip()
                            if should_colorize_diff:
                                output = colorize_diff_lines(output)
                            print(output)
                        if preview_result.stderr.strip():
                            emsg("--- PREVIEW STDERR ---")
                            output = preview_result.stderr.rstrip()
                            if should_colorize_diff:
                                output = colorize_diff_lines(output)
                            print(output)
                    except Exception as e:
                        emsg(f"Error running preview command: {e}")

                prompt_message = self.approval_system.format_tool_prompt(
                    tool_name, arguments, tool_config
                )
                # Check if prompt_message is a validation error
                if prompt_message.startswith("Error:"):
                    # Return validation error directly
                    return prompt_message, tool_config, False
                approved, with_guidance = (
                    self.approval_system.request_user_approval(
                        prompt_message, tool_name, arguments, tool_config
                    )
                )
                if not approved:
                    # For denied tools, return with guidance flag if requested
                    show_main_prompt = with_guidance
                    return DENIED_MESSAGE, tool_config, show_main_prompt

            # Determine if guidance was requested
            show_main_prompt = False
            if not auto_approved and not config_module.YOLO_MODE and with_guidance:
                show_main_prompt = True

            # Prepare arguments for execution
            self._prepare_tool_arguments(arguments)

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
                result_lines.append(
                    f"{config_module.BLUE}--- STDOUT ---{config_module.RESET}"
                )
                output = result.stdout.rstrip()
                if should_colorize_diff:
                    output = colorize_diff_lines(output)
                result_lines.append(output)
            if result.stderr.strip():
                result_lines.append(f"{config_module.RED}--- STDERR ---{config_module.RESET}")
                output = result.stderr.rstrip()
                if should_colorize_diff:
                    output = colorize_diff_lines(output)
                result_lines.append(output)
            result_lines.append(f"--- EXIT CODE: {result.returncode} ---")

            # Handle guidance prompt after successful execution
            if not auto_approved and not config_module.YOLO_MODE and with_guidance:
                self._handle_guidance_prompt(with_guidance)

            return (
                "\n".join(result_lines),
                tool_config,
                show_main_prompt,
            )
        except subprocess.TimeoutExpired:
            self.stats.tool_errors += 1
            return f"Error executing command tool '{tool_name}': Command timed out", tool_config, False
        except CancelAllToolCalls:
            # Properly handle cancellation requests by re-raising the exception
            raise
        except Exception as e:
            self.stats.tool_errors += 1
            # Check if this is the cancellation exception (string or proper exception)
            if str(e) == "CANCEL_ALL_TOOL_CALLS":
                return "CANCEL_ALL_TOOL_CALLS", tool_config, False
            return f"Error executing command tool '{tool_name}': {e}", tool_config, False

    def _handle_guidance_prompt(self, with_guidance):
        """Handle guidance prompt - placeholder that can be implemented by subclasses or handled differently."""
        # This method is expected by the original code but might not be needed
        # in the refactored version. For now, return None to maintain compatibility.
        return None

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
            from ...utils import emsg
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