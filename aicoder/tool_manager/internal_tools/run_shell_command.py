"""
Run shell command internal tool implementation.
"""

import subprocess
import os
import shlex
import re
import signal

# Get default timeout from environment variable, fallback to 30 if not set
DEFAULT_TIMEOUT_SECS = int(os.environ.get("SHELL_COMMAND_TIMEOUT", 30))

# Safe reading commands that can be auto-approved when not in YOLO mode
SAFE_READING_COMMANDS = {
    'rg', 'grep', 'ls', 'cat', 'head', 'tail', 'find', 'file', 'wc', 'du',
    'stat', 'whoami', 'pwd', 'date', 'which', 'whereis', 'type', 'echo',
    'printf', 'basename', 'dirname', 'realpath', 'readlink'
}

# Dangerous patterns that should block auto-approval
DANGEROUS_PATTERNS = [
    r';',            # Semicolon (command separator)
    r'\|',           # Pipe operator
    r'\$\(',         # Command substitution start $( 
    r'`',            # Backtick command substitution
    r'&&',           # Logical AND
    r'\|\|',         # Logical OR
    r'>>',           # Append redirect
    r'&\s*[^&]',     # Background execution (not logical AND)
    r'\s*sudo\s+',   # sudo usage
    r'\s*su\s+',     # su usage
]

# Special patterns that need context checking
CONTEXT_PATTERNS = {
    r'>': r'>',          # Redirect - needs context check  
    r'<': r'<',          # Input redirect - needs context check
}


def has_dangerous_patterns(command: str) -> tuple[bool, str]:
    """
    Check if command has dangerous patterns that require manual approval.
    
    Returns:
        tuple: (has_dangerous, reason)
    """
    # Check simple dangerous patterns first
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return True, f"Dangerous pattern detected: {pattern}"
    
    # Check context-sensitive patterns
    for pattern, full_pattern in CONTEXT_PATTERNS.items():
        matches = list(re.finditer(full_pattern, command))
        for match in matches:
            # Check if this pattern is outside quotes (dangerous) or inside quotes (safe)
            if _is_pattern_outside_quotes(command, match.start(), match.end()):
                return True, f"Dangerous pattern detected: {pattern}"
    
    return False, ""


def _is_pattern_outside_quotes(command: str, start: int, end: int) -> bool:
    """
    Check if a pattern occurrence is outside quotes in the command.
    
    Returns True if the pattern is outside quotes (dangerous), False if inside quotes (safe).
    """
    # Count quotes before this position
    before = command[:start]
    single_quotes = before.count("'")
    double_quotes = before.count('"')
    
    # If odd number of either quote type, we're inside that type of quote
    in_single = single_quotes % 2 == 1
    in_double = double_quotes % 2 == 1
    
    # Pattern is dangerous if we're not inside any quotes
    return not (in_single or in_double)


def analyze_command_safety(command: str, yolo_mode: bool = False) -> tuple[bool, str, str]:
    """
    Analyze a shell command for safety and determine if it should be auto-approved.
    
    Args:
        command: The shell command to analyze
        yolo_mode: Whether YOLO mode is enabled (passed from caller to avoid circular imports)
        
    Returns:
        tuple: (is_safe, reason, main_command)
            - is_safe: True if command is safe for auto-approval
            - reason: Human-readable reason for the decision
            - main_command: The primary command name (first word)
    """
    # Strip whitespace and handle empty command
    command = command.strip()
    if not command:
        return False, "Empty command", ""
    
    # Parse command to extract the main command (first word)
    try:
        # Use shlex to properly handle quotes
        parts = shlex.split(command)
        if not parts:
            return False, "Invalid command syntax", ""
        
        main_command = parts[0]
        # Remove any path components to get just the command name
        main_command = os.path.basename(main_command)
        
    except (ValueError, shlex.SplitError):
        # Fallback to simple split if shlex fails
        main_command = command.split()[0].split('/')[-1]
    
    # If in YOLO mode, everything is auto-approved
    if yolo_mode:
        return True, "YOLO mode enabled - auto-approving all commands", main_command
    
    # Check for dangerous patterns in the full command
    has_dangerous, reason = has_dangerous_patterns(command)
    if has_dangerous:
        return False, reason, main_command
    
    # Check if it's a safe reading command
    if main_command in SAFE_READING_COMMANDS:
        return True, f"Safe reading command: {main_command}", main_command
    
    # Otherwise, command requires manual approval
    return False, f"Command '{main_command}' requires manual approval", main_command


def validate_shell_command(arguments: dict) -> str | bool:
    """
    Validation function for shell commands that enables auto-approval for safe commands.
    
    This function integrates with the existing approval system to provide smart auto-approval:
    1. Safe reading commands: auto-approves immediately (rg, grep, ls, cat, etc.)
    2. Commands with dangerous patterns: requires manual approval every time
    3. Regular commands: goes to normal approval flow (may auto-approve based on session cache)
    
    Args:
        arguments: Tool arguments containing the command to validate
        
    Returns:
        True: Allow tool to proceed (may auto-approve or go to normal approval)
        Error message string: Block execution with error
    """
    command = arguments.get("command", "")
    
    # Strip whitespace and handle empty command
    command = command.strip()
    if not command:
        return "Error: Empty command"
    
    # Parse command to extract the main command (first word)
    try:
        parts = shlex.split(command)
        if not parts:
            return "Error: Invalid command syntax"
        main_command = os.path.basename(parts[0])
    except (ValueError, shlex.SplitError):
        main_command = command.split()[0].split('/')[-1]
    
    # Check for dangerous patterns in the CURRENT command
    # These patterns ALWAYS require manual approval, even if command was previously approved
    has_dangerous, reason = has_dangerous_patterns(command)
    if has_dangerous:
        # Let the executor handle the warning display to avoid duplicates
        return True  # Proceed to normal approval (no auto-approval)
    
    # If we get here, the current command is safe (no dangerous patterns)
    
    # Check if it's a safe reading command (auto-approve immediately)
    if main_command in SAFE_READING_COMMANDS:
        return True  # This signals auto-approval to the approval system
    
    # Current command is safe but not a reading command
    # Let the existing approval system handle session-based approval
    # The approval system will check if this command was previously approved for session
    return True  # Proceed to normal approval flow (may auto-approve based on session cache)

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": False,  # We'll handle auto-approval dynamically
    "hide_arguments": True,
    "approval_excludes_arguments": False,  # We'll customize cache key generation
    "approval_key_exclude_arguments": ["command", "reason"],  # We'll handle command filtering ourselves
    "validate_function": "validate_shell_command",  # Custom validation function
    "description": "Executes a shell command and returns its output.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "reason": {
                "type": "string",
                "description": "Optional reason for running the command.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30). Set to a higher value for long-running commands.",
                "default": DEFAULT_TIMEOUT_SECS,
                "minimum": 1,
            },
        },
        "required": ["command"],
    },
}


def get_dynamic_tool_config(base_config: dict, arguments: dict) -> dict:
    """
    Dynamically modify tool configuration based on command safety.
    
    This function analyzes the command and returns a modified tool configuration
    that can set auto_approved=True for safe commands.
    """
    command = arguments.get("command", "")
    
    # Parse command to extract the main command
    try:
        parts = shlex.split(command.strip())
        if parts:
            main_command = os.path.basename(parts[0])
        else:
            main_command = ""
    except (ValueError, shlex.SplitError):
        main_command = command.split()[0].split('/')[-1] if command else ""
    
    # Check if command has dangerous patterns
    has_dangerous, _ = has_dangerous_patterns(command)
    
    # Check if it's a safe reading command AND has no dangerous patterns
    if main_command in SAFE_READING_COMMANDS and not has_dangerous:
        # Return a copy with auto_approved=True for safe commands
        config_copy = base_config.copy()
        config_copy["auto_approved"] = True
        return config_copy
    
    # Return original config for commands requiring approval
    return base_config


def execute_run_shell_command(
    command: str,
    stats,
    reason: str = None,
    timeout: int = DEFAULT_TIMEOUT_SECS,
    **kwargs,
) -> str:
    """Executes a shell command and returns its output.

    Args:
        command: The shell command to execute
        stats: Statistics object for tracking tool errors
        reason: Optional reason for running the command
        timeout: Timeout in seconds (default: from SHELL_COMMAND_TIMEOUT env var or 30)
        **kwargs: Additional arguments (tool_index, total_tools, etc.) that may be passed but are not used
    """
    process = None
    try:
        shell_cmd = ["bash", "-c", command]

        # Use Popen to have more control over the process
        process = subprocess.Popen(
            shell_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid  # Create a new process group
        )

        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            # Kill the entire process group to ensure all child processes are terminated
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                # Wait a short time for graceful termination
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination didn't work
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except ProcessLookupError:
                # Process already terminated
                pass
            except OSError:
                # Handle case where process group doesn't exist
                try:
                    process.kill()
                except ProcessLookupError:
                    pass

            stats.tool_errors += 1
            return f"Error: Command '{command}' timed out after {timeout} seconds.\nTo retry with a longer timeout, use: run_shell_command(command=\"{command}\", timeout=60)"

        # Format the output - only include return code, stdout, and stderr
        output = f"Return code: {return_code}\n"
        if stdout:
            output += f"Stdout: {stdout}\n"
        if stderr:
            output += f"Stderr: {stderr}\n"

        return output
    except Exception as e:
        stats.tool_errors += 1
        return f"Error executing command '{command}': {e}"
    finally:
        # Ensure process is cleaned up in the finally block
        if process and process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                # Process already terminated or process group doesn't exist
                try:
                    process.kill()
                except (ProcessLookupError, OSError):
                    pass
