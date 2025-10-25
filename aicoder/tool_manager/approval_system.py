"""
Approval system for tool execution.
"""

import json
from typing import Dict, Any, List
from .. import config
from ..utils import format_tool_prompt, make_readline_safe, wmsg, imsg, emsg
from ..readline_history_manager import prompt_history_manager


class ApprovalSystem:
    """Handles user approval for tool execution."""

    def __init__(self, tool_registry, stats, animator):
        self.tool_registry = tool_registry
        self.stats = stats
        self.tool_approvals_session = set()
        self.animator = animator
        # Get message_history from tool_registry
        self.message_history = getattr(tool_registry, "message_history", None)
        # Store diff-edit results
        self._diff_edit_result = None

    def request_user_approval(
        self,
        prompt_message: str,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_config: Dict[str, Any],
    ) -> tuple[bool, bool]:
        """Request user approval for a tool call with robust error handling.

        Returns:
            Tuple of (approved: bool, with_guidance: bool)
        """
        # Check if prompt_message is actually an error message from validation
        if prompt_message.startswith("Error:"):
            # This is a validation error, don't prompt user
            # The error will be returned to the AI through the normal execution flow
            return (False, False)

        # YOLO Mode - bypass all approval systems
        if config.YOLO_MODE:
            wmsg(f"\n{prompt_message}")
            imsg("Auto approving... running YOLO MODE!")
            return (True, False)

        try:
            # Check if auto-approved
            auto_approved = tool_config.get("auto_approved", False)
            if auto_approved:
                return (True, False)

            # Generate cache key
            approval_excludes_arguments = tool_config.get(
                "approval_excludes_arguments", False
            )
            approval_key_exclude_arguments = tool_config.get(
                "approval_key_exclude_arguments", []
            )

            # If approval excludes arguments, use only tool name
            if approval_excludes_arguments:
                cache_key = tool_name
            else:
                cache_key = self._generate_approval_cache_key(
                    tool_name, arguments, approval_key_exclude_arguments
                )

            # Check if already approved for session
            if cache_key in self.tool_approvals_session:
                return (True, False)

            # Notify plugins before approval prompt
            try:
                from ..plugin_system.loader import notify_plugins_before_approval_prompt

                # Access the main app instance through the stats object which should have reference
                if hasattr(self.stats, "_app_instance"):
                    notify_plugins_before_approval_prompt(
                        self.stats._app_instance.loaded_plugins
                    )
            except Exception as e:
                # Don't let plugin notification errors break the approval process
                if config.DEBUG:
                    print(f"Debug: Plugin notification error: {e}")

            # Reset diff-edit result for each new approval request
            self._diff_edit_result = None

            # Show prompt with error handling
            try:
                wmsg(f"\n{prompt_message}")

                # Show file path for file operations
                if tool_name in ["edit_file", "write_file"] and "path" in arguments:
                    file_path = arguments["path"]
                    print(f"{config.CYAN}📁 File: {file_path}{config.RESET}")
            except Exception as e:
                emsg(f"Error displaying prompt: {e}")
                # Still proceed with approval to maintain security

            # Get user input with validation
            while True:
                try:
                    # Switch to tool approval mode for proper history
                    prompt_history_manager.setup_tool_approval_mode()

                    # Check if this is a file operation that supports external diff
                    has_diff_option = tool_name in ["edit_file", "write_file"]

                    approval_prompt = f"{config.RED}a) Allow once  s) Allow for session  d) Deny  c) Cancel all  YOLO) YOLO  help) Show help\nChoose (a/s/d/c/YOLO/help): {config.RESET}"
                    safe_approval_prompt = make_readline_safe(approval_prompt)

                    # Enter prompt mode to ensure echo and canonical mode
                    from ..terminal_manager import enter_prompt_mode, exit_prompt_mode

                    enter_prompt_mode()

                    try:
                        raw_answer = input(safe_approval_prompt).lower().strip()
                    finally:
                        exit_prompt_mode()

                    # Extract just the letter before ")" (e.g., "a) Allow once" -> "a")
                    answer = (
                        raw_answer.split(")")[0] if ")" in raw_answer else raw_answer
                    )

                    # Start cursor animation
                    self.animator.start_cursor_blinking()

                    # Check for guidance suffix
                    with_guidance = answer.endswith("+")
                    if with_guidance:
                        # Remove the + suffix for processing
                        answer = answer[:-1]

                    if answer in ["yolo"]:
                        import os

                        os.environ["YOLO_MODE"] = "1"
                        config.YOLO_MODE = True
                        return (True, with_guidance)
                    elif answer in ["a", "allow"]:
                        return (True, with_guidance)
                    elif answer in ["s", "session"]:
                        self.tool_approvals_session.add(cache_key)
                        return (True, with_guidance)
                    elif answer in ["d", "deny"]:
                        return (False, with_guidance)
                    elif answer in ["c", "cancel"]:
                        # This is not an error - it's a valid cancellation request
                        raise Exception("CANCEL_ALL_TOOL_CALLS")
                    elif answer in ["diff"]:
                        if has_diff_option:
                            # Ensure terminal is in prompt mode for external editor
                            from ..terminal_manager import enter_prompt_mode

                            enter_prompt_mode()
                            self._show_external_diff(tool_name, arguments)
                        else:
                            wmsg("External diff not available for this tool")
                    elif answer in ["diff-edit"]:
                        if has_diff_option:
                            # Ensure terminal is in prompt mode for external editor
                            from ..terminal_manager import enter_prompt_mode

                            enter_prompt_mode()
                            result = self._show_interactive_diff(tool_name, arguments)
                            if result:  # User modified the diff
                                # Create a success result to return
                                file_path = arguments.get("path", "")
                                success_result = {
                                    "success": True,
                                    "message": f"File '{file_path}' was successfully modified by user during interactive diff editing. The user's changes have been applied directly.",
                                    "file_path": file_path,
                                    "status": "user_modified_via_diff_edit",
                                    "ai_guidance": f"The user chose to edit '{file_path}' interactively. You should read the file again to see what changes were made.",
                                }
                                # Store the success result for later retrieval
                                self._diff_edit_result = success_result
                                # Return APPROVED without guidance
                                return True, False
                        else:
                            wmsg("Interactive diff not available for this tool")
                    elif answer in ["help", "h"]:
                        self._show_approval_help()
                        # Continue the loop to ask for input again
                        continue
                    else:
                        wmsg("Invalid choice. Please enter a, s, d, c, YOLO, or help.")
                except (EOFError, KeyboardInterrupt):
                    emsg("\nInput interrupted. Denying tool call.")
                    return (False, False)
                except Exception as e:
                    # Check if this is a cancellation request
                    if str(e) == "CANCEL_ALL_TOOL_CALLS":
                        raise  # Re-raise cancellation
                    emsg(f"Error reading input: {e}")

            # Fallback deny if we somehow get here
            return (False, False)

        except Exception as e:
            # Check if this is a cancellation request
            if str(e) == "CANCEL_ALL_TOOL_CALLS":
                raise  # Re-raise cancellation
            emsg(f"Error in approval system: {e}")
            # For security, deny by default on errors
            return (False, False)

    def _generate_approval_cache_key(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        approval_key_exclude_arguments: List[str],
    ) -> str:
        """Generate a cache key for tool approvals, excluding specified arguments."""
        try:
            # Handle potential serialization issues with complex arguments
            filtered_args = {}
            for k, v in arguments.items():
                if k not in approval_key_exclude_arguments:
                    # Convert complex objects to string representations
                    if isinstance(v, (dict, list, tuple)):
                        try:
                            filtered_args[k] = json.dumps(v, sort_keys=True)
                        except (TypeError, ValueError):
                            # Fallback to string representation
                            filtered_args[k] = str(v)
                    else:
                        filtered_args[k] = v

            if not filtered_args:
                return tool_name

            # Sort arguments for consistent key generation
            sorted_items = sorted(filtered_args.items())
            args_str = "&".join(f"{k}={v}" for k, v in sorted_items)
            return f"{tool_name}:{args_str}"
        except Exception as e:
            # Fallback to tool name only if key generation fails
            emsg(f"Warning: Failed to generate cache key for {tool_name}: {e}")
            return tool_name

    def format_tool_prompt(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_config: Dict[str, Any],
        raw_arguments: str = None,
    ) -> str:
        """Format a user-friendly prompt for tool approval."""
        # Pre-validation for tools that have a validation function
        validation_result = self._run_tool_validation(tool_name, arguments, tool_config)
        if validation_result is not True:
            # Return validation error instead of prompting
            return validation_result

        # Extract path for write_file and edit_file tools to enable proper diff generation
        path = ""
        if tool_name == "write_file" and "path" in arguments:
            path = arguments["path"]
        elif tool_name == "edit_file" and "path" in arguments:
            path = arguments["path"]

        return format_tool_prompt(
            tool_name, arguments, tool_config, path, raw_arguments
        )

    def _show_interactive_diff(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """Show interactive diff editor and apply user modifications.

        Returns:
            bool: True if user modified the file, False otherwise
        """
        import os
        import subprocess
        import tempfile

        # Get file path
        file_path = arguments.get("path", "")
        if not file_path or not os.path.exists(file_path):
            wmsg("Cannot show diff: file not found or path not available")
            return False

        # Determine diff tool
        diff_tool = os.environ.get("AICODER_DIFF_TOOL_BIN")
        if not diff_tool:
            # Check for common diff tools in order of preference (vimdiff first!)
            for tool in ["vimdiff", "nvim -d", "meld", "kdiff3", "diffuse", "code"]:
                if (
                    tool.split()[0] == "vimdiff"
                    and subprocess.run(["which", "vim"], capture_output=True).returncode
                    == 0
                ):
                    diff_tool = "vimdiff"
                    break
                elif (
                    tool.split()[0] == "nvim"
                    and subprocess.run(
                        ["which", "nvim"], capture_output=True
                    ).returncode
                    == 0
                ):
                    diff_tool = "nvim -d"
                    break
                elif (
                    subprocess.run(["which", tool], capture_output=True).returncode == 0
                ):
                    diff_tool = tool
                    break

        if not diff_tool:
            wmsg("No diff tool found. Install vimdiff or set AICODER_DIFF_TOOL_BIN")
            return False

        # Create temporary file with the new content
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=os.path.basename(file_path),
                dir=os.getcwd(),
                delete=False,
            ) as tmp_file:
                tmp_path = tmp_file.name

                # Write new content based on tool type
                if tool_name == "write_file":
                    new_content = arguments.get("content", "")
                elif tool_name == "edit_file":
                    # For edit_file, we need to simulate the edit to get the new content
                    old_content = ""
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8") as f:
                            old_content = f.read()

                    old_string = arguments.get("old_string", "")
                    new_string = arguments.get("new_string", "")
                    if old_string in old_content:
                        new_content = old_content.replace(old_string, new_string, 1)
                    else:
                        new_content = old_content  # Fallback if no match

                tmp_file.write(new_content)

            # Store original temp content for comparison
            with open(tmp_path, "r", encoding="utf-8") as f:
                original_temp_content = f.read()

            # Run diff tool
            print(
                f"\n{config.CYAN}📝 Opening {diff_tool} for interactive diff editing...{config.RESET}"
            )
            wmsg(f"Original: {file_path}")
            wmsg(f"Temp file: {tmp_path}")
            imsg("💡 Edit the temp file as needed, then save and exit")

            if diff_tool == "vimdiff":
                subprocess.run([diff_tool, file_path, tmp_path])
            elif diff_tool == "nvim -d":
                subprocess.run([diff_tool, file_path, tmp_path])
            elif diff_tool == "code":
                subprocess.run([diff_tool, "--diff", file_path, tmp_path])
            else:
                subprocess.run([diff_tool, file_path, tmp_path])

            # Check if user modified the temp file
            with open(tmp_path, "r", encoding="utf-8") as f:
                modified_temp_content = f.read()

            if modified_temp_content != original_temp_content:
                # User modified the file!
                imsg("\n✨ User modifications detected!")

                # Apply user changes to original file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(modified_temp_content)

                imsg(f"✅ Applied user modifications to {file_path}")

                # Notify user
                print(
                    f"{config.CYAN}🎯 Your changes have been applied successfully!{config.RESET}"
                )

                # Store notification to be added after tool result
                notification = (
                    f"USER MODIFICATION: {file_path} was edited by user during interactive diff editing. "
                    f"The AI's proposed changes were replaced with user modifications. "
                    f"The file content now reflects the user's edits."
                )

                # Store the notification in a separate attribute since _diff_edit_result might be reset
                if not hasattr(self, "_diff_edit_notification"):
                    self._diff_edit_notification = notification
                else:
                    self._diff_edit_notification = notification

                return True
            else:
                print(f"\n{config.BLUE}ℹ️  No modifications detected{config.RESET}")
                return False

        except Exception as e:
            emsg(f"Error running interactive diff: {e}")
            return False
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _show_external_diff(self, tool_name: str, arguments: Dict[str, Any]):
        """Show external diff viewer for file operations."""
        import os
        import subprocess
        import tempfile

        # Get file path
        file_path = arguments.get("path", "")
        if not file_path or not os.path.exists(file_path):
            wmsg("Cannot show diff: file not found or path not available")
            return

        # Determine diff tool
        diff_tool = os.environ.get("AICODER_DIFF_TOOL_BIN")
        if not diff_tool:
            # Check for common diff tools in order of preference (vimdiff first!)
            for tool in ["vimdiff", "nvim -d", "meld", "kdiff3", "diffuse", "code"]:
                if (
                    tool.split()[0] == "vimdiff"
                    and subprocess.run(["which", "vim"], capture_output=True).returncode
                    == 0
                ):
                    diff_tool = "vimdiff"
                    break
                elif (
                    tool.split()[0] == "nvim"
                    and subprocess.run(
                        ["which", "nvim"], capture_output=True
                    ).returncode
                    == 0
                ):
                    diff_tool = "nvim -d"
                    break
                elif (
                    subprocess.run(["which", tool], capture_output=True).returncode == 0
                ):
                    diff_tool = tool
                    break

        if not diff_tool:
            wmsg("No diff tool found. Install meld or set AICODER_DIFF_TOOL_BIN")
            return

        # Create temporary file with the new content
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=os.path.basename(file_path),
                dir=os.getcwd(),
                delete=False,
            ) as tmp_file:
                tmp_path = tmp_file.name

                # Write new content based on tool type
                if tool_name == "write_file":
                    new_content = arguments.get("content", "")
                elif tool_name == "edit_file":
                    # For edit_file, we need to simulate the edit to get the new content
                    old_content = ""
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8") as f:
                            old_content = f.read()

                    old_string = arguments.get("old_string", "")
                    new_string = arguments.get("new_string", "")
                    if old_string in old_content:
                        new_content = old_content.replace(old_string, new_string, 1)
                    else:
                        new_content = old_content  # Fallback if no match

                tmp_file.write(new_content)

            # Run diff tool
            print(f"\n{config.CYAN}Opening {diff_tool} to show diff...{config.RESET}")
            wmsg(f"Original: {file_path}")
            wmsg(f"Modified: {tmp_path}")

            if diff_tool == "meld":
                subprocess.run([diff_tool, file_path, tmp_path])
            elif diff_tool == "code":
                subprocess.run([diff_tool, "--diff", file_path, tmp_path])
            else:
                subprocess.run([diff_tool, file_path, tmp_path])

            imsg("\nDiff viewer closed")

        except Exception as e:
            emsg(f"Error running diff tool: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _show_approval_help(self):
        """Display help information for approval options."""
        imsg("\nApproval Options:")
        wmsg("a) Allow once - Execute this tool call just this one time")
        wmsg(
            "s) Allow for session - Allow this type of tool call for the rest of this session"
        )
        wmsg("d) Deny - Reject this tool call")
        wmsg("c) Cancel all - Cancel all pending tool calls and return to user input")
        if any(
            tool_name in ["edit_file", "write_file"]
            for tool_name in ["edit_file", "write_file"]
        ):
            wmsg("diff) Show external diff - View diff of proposed changes")
            wmsg(
                "diff-edit) Interactive diff edit - Edit proposed changes in diff tool"
            )
        wmsg(
            "YOLO) YOLO mode - Automatically approve all tool calls for the rest of the session"
        )
        wmsg("help) Show help - Display this help message")
        imsg("\nNavigation:")
        wmsg("↑/↓ Arrow keys - Navigate through approval history and select options")
        wmsg("Type directly - Or type the option letter directly")
        imsg("\nGuidance Feature:")
        print(
            "You can add a '+' after any option (except help) to provide guidance to the AI."
        )
        print(
            "Example: 'a+' allows the tool call once but also gives the AI feedback about your decision."
        )
        print(
            "When you use '+', you'll be prompted to enter guidance text after making your choice."
        )
        print(
            "This guidance will be added to the conversation as a user message, helping the AI"
        )
        print("understand your preferences and make better decisions in future steps.")
        imsg("\nDiff Tool:")
        wmsg("Configure - Set AICODER_DIFF_TOOL_BIN environment variable")
        wmsg("Auto-detect - vimdiff, nvim -d, meld, kdiff3, diffuse, or code")
        wmsg("Install - sudo apt install vim (for vimdiff) or meld")
        print(
            "Example: If you type 'a+' and then enter 'Please use more concise responses',"
        )
        print(
            "that feedback will be added to the AI's context for future interactions."
        )

    def _run_tool_validation(
        self, tool_name: str, arguments: Dict[str, Any], tool_config: Dict[str, Any]
    ) -> str | bool:
        """Run tool validation if a validation function is defined.

        Returns:
            True if validation passes or no validation function is defined
            Error message string if validation fails
        """
        try:
            # Check if tool has a validation function defined
            validate_function_name = tool_config.get("validate_function")
            if not validate_function_name:
                # No validation function defined, proceed with normal approval
                return True

            # Import the internal tool module to get the validation function
            if tool_config.get("type") == "internal":
                from . import internal_tools

                tool_module = getattr(internal_tools, tool_name, None)
                if tool_module and hasattr(tool_module, validate_function_name):
                    validate_function = getattr(tool_module, validate_function_name)
                    if callable(validate_function):
                        # Run the validation function
                        return validate_function(arguments)

            # If we couldn't find or run the validation function, proceed with normal approval
            return True

        except Exception:
            # If validation fails due to an error, proceed with normal approval
            # Don't block tool execution due to validation errors
            return True

    def revoke_approvals(self):
        """Clear the session approval cache."""
        self.tool_approvals_session.clear()
        imsg("\n *** All session approvals have been revoked.")
