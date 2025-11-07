"""
Shared approval utilities for AI Coder tool execution.
"""

import os
import re
from typing import Tuple, Dict, Any
import shlex


def check_approval_rules(command: str) -> tuple[bool, str]:
    """
    Check user-configurable approval rules with priority:
    1. auto_deny (highest) - automatically reject
    2. ask_approval (middle) - require manual approval
    3. auto_approve (lowest) - automatically approve

    Args:
        command: The shell command to check

    Returns:
        tuple: (has_dangerous, reason)
    """
    config_dir = os.path.expanduser("~/.config/aicoder")

    # Priority 1: Auto deny (highest priority)
    has_match, matched_rule, action = check_rule_file(
        os.path.join(config_dir, "run_shell_command.auto_deny"), command, "deny"
    )
    if has_match:
        return True, f"Auto denied. Regex: {matched_rule}"

    # Priority 2: Ask approval (middle priority)
    has_match, matched_rule, action = check_rule_file(
        os.path.join(config_dir, "run_shell_command.ask_approval"), command, "ask"
    )
    if has_match:
        return True, f"Detected in ask approval file. Regex: {matched_rule}"

    # Priority 3: Auto approve (lowest priority)
    has_match, matched_rule, action = check_rule_file(
        os.path.join(config_dir, "run_shell_command.auto_approve"), command, "approve"
    )
    if has_match:
        return False, ""  # Not dangerous, auto-approved

    return False, ""


def check_rule_file(
    rule_file: str, command: str, file_type: str
) -> tuple[bool, str, str]:
    """
    Check a single rule file for matches.

    Args:
        rule_file: Path to the rule file
        command: The shell command to check
        file_type: Type of file (deny/ask/approve)

    Returns:
        tuple: (has_match, matched_rule, file_type)
    """
    if not os.path.exists(rule_file):
        return False, "", file_type

    try:
        with open(rule_file, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines (empty regex would match everything!)
                if not line or line.startswith("#"):
                    continue  # Skip empty lines and comments

                try:
                    # Support negation with ! prefix (for auto_approve only)
                    if line.startswith("!") and file_type == "approve":
                        pattern = line[1:]  # Remove the ! prefix

                        # Skip if negation pattern is empty (would match everything)
                        if not pattern:
                            continue

                        if not re.search(pattern, command):
                            # Negative pattern matched (command doesn't match pattern)
                            return (
                                True,
                                f"Auto approved (negated regex): {pattern}",
                                file_type,
                            )
                    else:
                        # Ensure pattern is not empty before searching
                        if line and re.search(line, command):
                            return True, line, file_type
                except re.error:
                    # Invalid regex, skip it
                    continue
    except (IOError, OSError):
        pass  # File not readable, just skip

    return False, "", file_type


def get_run_shell_command_cache_key(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Generate a cache key for run_shell_command approvals based on the main command name.
    
    Args:
        tool_name: Name of the tool (should be "run_shell_command")
        arguments: Tool arguments containing the command
        
    Returns:
        Cache key string
    """
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
    
    return cache_key


def handle_approval_for_tool(
    approval_system,
    tool_name: str,
    arguments: Dict[str, Any],
    tool_config: Dict[str, Any],
    needs_approval: bool,
    yolo_approval: bool = False,
    auto_approved: bool = False
) -> Tuple[bool, bool, str]:
    """
    Handle approval process for a tool call.
    
    Args:
        approval_system: The approval system instance
        tool_name: Name of the tool being executed
        arguments: Tool arguments
        tool_config: Tool configuration
        needs_approval: Whether approval is needed (not auto-approved and not YOLO)
        yolo_approval: Whether in YOLO mode
        auto_approved: Whether tool is auto-approved
        
    Returns:
        Tuple of (approved: bool, with_guidance: bool, prompt_message: str)
    """
    # Handle approval for internal tools
    if yolo_approval:
        # YOLO mode - check user rules first
        if tool_name == "run_shell_command":
            command = arguments.get("command", "")
            has_dangerous, reason = check_approval_rules(command)
            if has_dangerous:
                print(f"   - [!] {reason} - YOLO mode respects user rules")
                error_msg = f"Command denied by GLOBAL RULE: {command}"
                return False, False, error_msg
            return True, False, "YOLO mode enabled - auto-approving command"
        else:
            return True, False, "YOLO mode enabled - auto-approving tool"
    
    elif needs_approval:
        prompt_message = approval_system.format_tool_prompt(
            tool_name, arguments, tool_config
        )
        # Check if prompt_message is a validation error
        if prompt_message.startswith("Error:"):
            # Return validation error directly
            return False, False, prompt_message
        
        # Special handling for run_shell_command cache key generation
        if tool_name == "run_shell_command":
            # Generate a cache key based on the main command name for session approval
            cache_key = get_run_shell_command_cache_key(tool_name, arguments)
            
            # Check for dangerous patterns in the current command (even if session approved)
            from .internal_tools.run_shell_command import has_dangerous_patterns

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
                return False, False, "EXECUTION DENIED BY THE USER"
            
            has_dangerous, reason = has_dangerous_patterns(command)
            if has_dangerous:
                # Found dangerous pattern - require manual approval
                print(f"   - [!] {reason} - requires manual approval")
            else:
                # Check user-configurable approval rules (ask and auto)
                has_dangerous, reason = check_approval_rules(command)
                if has_dangerous:
                    print(f"   - [!] {reason} - requires manual approval")

            # Check if this specific command was approved for session AND is safe
            if cache_key in approval_system.tool_approvals_session:
                if has_dangerous:
                    # Need to ask for approval despite session approval
                    approved, with_guidance = approval_system.request_user_approval(
                        prompt_message,
                        tool_name,
                        arguments,
                        tool_config,
                    )
                    return approved, with_guidance, prompt_message
                else:
                    # Safe command and session approved - show command info but skip prompt
                    print(f"\n└─ AI wants to call tool: {tool_name}")
                    print(f"   - Command: {command}")
                    return True, False, prompt_message
            else:
                # Need to ask for approval - temporarily use our cache key
                original_generate_cache_key = (
                    approval_system._generate_approval_cache_key
                )
                approval_system._generate_approval_cache_key = (
                    lambda tn, args, exclude_args: cache_key
                )

                try:
                    approved, with_guidance = approval_system.request_user_approval(
                        prompt_message,
                        tool_name,
                        arguments,
                        tool_config,
                    )
                    return approved, with_guidance, prompt_message
                finally:
                    # Restore original cache key function
                    approval_system._generate_approval_cache_key = original_generate_cache_key
        else:
            # Normal approval flow for other tools
            approved, with_guidance = approval_system.request_user_approval(
                prompt_message,
                tool_name,
                arguments,
                tool_config,
            )
            return approved, with_guidance, prompt_message
    
    # If auto_approved is True, no approval needed - return approved
    return True, False, "Tool auto-approved"


def handle_approval_result(
    approved: bool,
    with_guidance: bool,
    approval_system,
    tool_config: Dict[str, Any]
) -> Tuple[str, str, bool]:
    """
    Handle the result of an approval decision.
    
    Args:
        approved: Whether the tool was approved
        with_guidance: Whether guidance was requested
        approval_system: The approval system instance
        tool_config: Tool configuration
        
    Returns:
        Tuple of (result_message, guidance_content, guidance_requested)
    """
    if not approved:
        # Handle guidance prompt even for denied tools
        guidance_content = _handle_guidance_prompt_internal(approval_system, with_guidance)
        return "EXECUTION DENIED BY THE USER", guidance_content, False

    # Store guidance flag for later use
    guidance_requested = False
    if with_guidance:
        guidance_requested = True

    return None, None, guidance_requested


def _handle_guidance_prompt_internal(approval_system, with_guidance: bool) -> str:
    """Internal helper to handle guidance prompt for both approved and denied tools.

    Args:
        approval_system: The approval system instance
        with_guidance: Whether guidance was requested

    Returns:
        Guidance content or None if not requested or cancelled
    """
    from .. import config
    from ..utils import make_readline_safe
    from ..readline_history_manager import prompt_history_manager
    
    guidance_content = None
    if with_guidance:
        try:
            approval_system.animator.stop_cursor_blinking()

            # Switch to user input mode for guidance (share history with user commands)
            prompt_history_manager.setup_user_input_mode()

            guidance_prompt = f"{config.BOLD}{config.GREEN}Guidance: {config.RESET}"
            safe_guidance_prompt = make_readline_safe(guidance_prompt)

            # Enter prompt mode to ensure echo and canonical mode
            from ..terminal_manager import enter_prompt_mode, exit_prompt_mode

            enter_prompt_mode()

            try:
                guidance_content = input(safe_guidance_prompt).strip()
            finally:
                exit_prompt_mode()

            # Save guidance to user input history
            if guidance_content:
                prompt_history_manager.save_user_input(guidance_content)
        except (EOFError, KeyboardInterrupt):
            # If user cancels guidance input, proceed without guidance
            guidance_content = None
        approval_system.animator.start_cursor_blinking()
    return guidance_content