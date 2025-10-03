"""
Approval system for tool execution.
"""

import json
from typing import Dict, Any, List
from .. import config
from ..utils import format_tool_prompt, make_readline_safe

# Import readline to enable readline functionality
try:
    import readline
except ImportError:
    # readline is not available on this platform
    pass


class ApprovalSystem:
    """Handles user approval for tool execution."""

    def __init__(self, tool_registry, stats, animator):
        self.tool_registry = tool_registry
        self.stats = stats
        self.tool_approvals_session = set()
        self.animator = animator

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
            print(f"\n{config.YELLOW}{prompt_message}{config.RESET}")
            print(f"{config.GREEN}Auto approving... running YOLO MODE!{config.RESET}")
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

            # Show prompt with error handling
            try:
                print(f"\n{config.YELLOW}{prompt_message}{config.RESET}")
            except Exception as e:
                print(f"{config.RED}Error displaying prompt: {e}{config.RESET}")
                # Still proceed with approval to maintain security

            # Get user input with validation
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    approval_prompt = f"{config.RED}a) Allow once  s) Allow for session  d) Deny  c) Cancel all  YOLO) YOLO  help) Show help\nChoose (a/s/d/c/YOLO/help): {config.RESET}"
                    safe_approval_prompt = make_readline_safe(approval_prompt)
                    answer = (
                        input(safe_approval_prompt)
                        .lower()
                        .strip()
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
                    elif answer in ["help", "h"]:
                        self._show_approval_help()
                        # Continue the loop to ask for input again
                        continue
                    else:
                        print(
                            f"{config.YELLOW}Invalid choice. Please enter a, s, d, c, YOLO, or help.{config.RESET}"
                        )
                        if attempt == max_attempts - 1:
                            print(
                                f"{config.RED}Max attempts reached. Denying tool call.{config.RESET}"
                            )
                            return (False, False)
                except (EOFError, KeyboardInterrupt):
                    print(f"\n{config.RED}Input interrupted. Denying tool call.{config.RESET}")
                    return (False, False)
                except Exception as e:
                    # Check if this is a cancellation request
                    if str(e) == "CANCEL_ALL_TOOL_CALLS":
                        raise  # Re-raise cancellation
                    print(f"{config.RED}Error reading input: {e}{config.RESET}")
                    if attempt == max_attempts - 1:
                        print(f"{config.RED}Max attempts reached. Denying tool call.{config.RESET}")
                        return (False, False)

            # Fallback deny if we somehow get here
            return (False, False)

        except Exception as e:
            # Check if this is a cancellation request
            if str(e) == "CANCEL_ALL_TOOL_CALLS":
                raise  # Re-raise cancellation
            print(f"{config.RED}Error in approval system: {e}{config.RESET}")
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
            print(
                f"{config.RED}Warning: Failed to generate cache key for {tool_name}: {e}{config.RESET}"
            )
            return tool_name

    def format_tool_prompt(
        self, tool_name: str, arguments: Dict[str, Any], tool_config: Dict[str, Any], raw_arguments: str = None
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

        return format_tool_prompt(tool_name, arguments, tool_config, path, raw_arguments)

    def _show_approval_help(self):
        """Display help information for approval options."""
        print(f"\n{config.GREEN}Approval Options:{config.RESET}")
        print(
            f"{config.YELLOW}a) Allow once{config.RESET} - Execute this tool call just this one time"
        )
        print(
            f"{config.YELLOW}s) Allow for session{config.RESET} - Allow this type of tool call for the rest of this session"
        )
        print(f"{config.YELLOW}d) Deny{config.RESET} - Reject this tool call")
        print(
            f"{config.YELLOW}c) Cancel all{config.RESET} - Cancel all pending tool calls and return to user input"
        )
        print(
            f"{config.YELLOW}YOLO) YOLO mode{config.RESET} - Automatically approve all tool calls for the rest of the session"
        )
        print(f"{config.YELLOW}help) Show help{config.RESET} - Display this help message")
        print(f"\n{config.GREEN}Guidance Feature:{config.RESET}")
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
        print(f"\n{config.GREEN} *** All session approvals have been revoked.{config.RESET}")
