"""
Ruff Plugin for AI Coder - Automatic Python Code Quality Checks

This plugin automatically runs ruff checks on Python files when they are saved/edited
and prompts the AI to fix any serious issues found. Optionally auto-formats code with ruff format.

Features:
- Automatic ruff check on .py file modifications (serious-only mode by default)
- User message generation when serious issues are found
- Optional auto-formatting with ruff format
- Graceful fallback when ruff is not installed
- Configurable via environment variables or plugin constants

Default Behavior:
- Serious-only mode enabled by default to focus on functional errors only
- Ignores minor linting issues like unused variables (F841), line length (E501), etc.
- Use `/ruff check-only-serious off` to enable full linting mode

Environment Variables:
- RUFF_FORMAT: Enable auto-formatting (default: False)
- RUFF_CHECK_ARGS: Additional arguments for ruff check (default: "")
- RUFF_FORMAT_ARGS: Additional arguments for ruff format (default: "")

Plugin Constants:
- ENABLE_RUFF_FORMAT: Override auto-formatting setting (default: False)
- RUFF_CHECK_ARGS: Default arguments for ruff check
- RUFF_FORMAT_ARGS: Default arguments for ruff format
"""

import os
import shutil
import subprocess


# Plugin configuration
def _parse_bool_env(var_name: str, default: bool = False) -> bool:
    """Parse boolean environment variable that accepts 1/0, true/false, on/off."""
    value = os.getenv(var_name, "").lower()
    return value in {"1", "true", "on"} if value else default


ENABLE_RUFF_FORMAT = _parse_bool_env("RUFF_FORMAT", False)
RUFF_CHECK_ARGS = os.getenv("RUFF_CHECK_ARGS", "")
RUFF_FORMAT_ARGS = os.getenv("RUFF_FORMAT_ARGS", "")

# Global reference to aicoder instance
_aicoder_ref = None

# Original functions to monkey patch
_original_write_file = None
_original_edit_file = None

# Plugin version
__version__ = "1.1.0"


def _is_ruff_enabled() -> bool:
    """Check if ruff checking is enabled (persistent config override)."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        return _aicoder_ref.persistent_config.get("ruff.enabled", True)
    return True


def _is_ruff_format_enabled() -> bool:
    """Check if ruff formatting is enabled (persistent config override)."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        return _aicoder_ref.persistent_config.get(
            "ruff.format_enabled", ENABLE_RUFF_FORMAT
        )
    return ENABLE_RUFF_FORMAT


def _get_ruff_check_args() -> str:
    """Get ruff check arguments from persistent config."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        return _aicoder_ref.persistent_config.get("ruff.check_args", RUFF_CHECK_ARGS)
    return RUFF_CHECK_ARGS


def _get_ruff_format_args() -> str:
    """Get ruff format arguments from persistent config."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        return _aicoder_ref.persistent_config.get("ruff.format_args", RUFF_FORMAT_ARGS)
    return RUFF_FORMAT_ARGS


def _is_ruff_serious_only_enabled() -> bool:
    """Check if ruff serious-only mode is enabled (persistent config override)."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        return _aicoder_ref.persistent_config.get("ruff.serious_only", True)
    return True


def _get_effective_check_args() -> str:
    """Get the effective ruff check arguments based on current mode."""
    if _is_ruff_serious_only_enabled():
        return "--select E,F --ignore E501,F841,E712,F401,E722,F541"
    else:
        return _get_ruff_check_args()  # User custom args or default


def _set_ruff_config(key: str, value: str) -> None:
    """Set ruff config in persistent storage."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        _aicoder_ref.persistent_config[f"ruff.{key}"] = value
        print(f"[✓] Ruff {key} set to: {value}")
    else:
        print("[X] Persistent config not available")


def _handle_ruff_command(args: list[str]) -> tuple[bool, bool]:
    """Handle /ruff commands."""
    try:
        from aicoder.utils import imsg, emsg
    except ImportError:
        # Fallback for testing
        def imsg(msg):
            print(f"INFO: {msg}")

        def emsg(msg):
            print(f"ERROR: {msg}")

    try:
        if not args:
            # Show status
            enabled = _is_ruff_enabled()
            format_enabled = _is_ruff_format_enabled()
            serious_only = _is_ruff_serious_only_enabled()
            check_args = _get_ruff_check_args()
            format_args = _get_ruff_format_args()

            status = f"""Ruff Plugin Status

- **Checking**: {"[✓] Enabled" if enabled else "[X] Disabled"}
- **Serious-only mode**: {"[✓] Enabled" if serious_only else "[X] Disabled"} (default: enabled)
- **Auto-format**: {"[✓] Enabled" if format_enabled else "[X] Disabled"}
- **Check args**: `{check_args or "default"}`
- **Format args**: `{format_args or "default"}`

**Commands:**
- `/ruff check on/off` - Enable/disable checking
- `/ruff check-only-serious on/off` - Enable/disable serious-only mode
- `/ruff format on/off` - Enable/disable auto-formatting
- `/ruff check args <args>` - Set check arguments
- `/ruff format args <args>` - Set format arguments
- `/ruff help` - Show this help"""
            imsg(status)
            return False, False

        cmd = args[0].lower()

        if cmd == "check":
            if len(args) >= 2:
                check_cmd = args[1].lower()
                if check_cmd in ["on", "off"]:
                    _set_ruff_config("enabled", check_cmd == "on")
                    imsg(f"[✓] Ruff checking turned {check_cmd}")
                    return False, False
                elif check_cmd == "args":
                    check_args = " ".join(args[2:])
                    _set_ruff_config("check_args", check_args)
                    imsg(f"[✓] Ruff check arguments set to: `{check_args}`")
                    return False, False
                else:
                    emsg(
                        "[X] Usage: `/ruff check on|off` or `/ruff check args <arguments>`"
                    )
                    return False, False
            else:
                emsg("[X] Usage: `/ruff check on|off` or `/ruff check args <arguments>`")
                return False, False

        elif cmd == "check-only-serious":
            if len(args) >= 2:
                serious_cmd = args[1].lower()
                if serious_cmd in ["on", "off"]:
                    _set_ruff_config("serious_only", serious_cmd == "on")
                    if serious_cmd == "on":
                        imsg("[✓] Ruff serious-only mode enabled - using predefined serious error filter")
                    else:
                        imsg("[✓] Ruff serious-only mode disabled - all linting issues will be reported")
                    return False, False
                else:
                    emsg("[X] Usage: `/ruff check-only-serious on|off`")
                    return False, False
            else:
                emsg("[X] Usage: `/ruff check-only-serious on|off`")
                return False, False

        elif cmd == "format":
            if len(args) >= 2:
                format_cmd = args[1].lower()
                if format_cmd in ["on", "off"]:
                    _set_ruff_config("format_enabled", format_cmd == "on")
                    imsg(f"[✓] Ruff auto-formatting turned {format_cmd}")
                    return False, False
                else:
                    emsg("[X] Usage: `/ruff format on|off`")
                    return False, False
            else:
                emsg("[X] Usage: `/ruff format on|off`")
                return False, False

        elif cmd == "check":
            if len(args) >= 2 and args[1].lower() == "args":
                check_args = " ".join(args[2:])
                _set_ruff_config("check_args", check_args)
                imsg(f"[✓] Ruff check arguments set to: `{check_args}`")
                return False, False
            else:
                emsg("[X] Usage: `/ruff check args <arguments>`")
                return False, False

        elif cmd == "format" and len(args) >= 2 and args[1].lower() == "args":
            format_args = " ".join(args[2:])
            _set_ruff_config("format_args", format_args)
            imsg(f"[✓] Ruff format arguments set to: `{format_args}`")
            return False, False

        elif cmd == "help":
            help_text = """Ruff Plugin Commands

- `/ruff` - Show current status
- `/ruff check on|off` - Enable/disable checking
- `/ruff check-only-serious on|off` - Enable/disable serious-only mode (default: enabled)
- `/ruff format on|off` - Enable/disable auto-formatting
- `/ruff check args <args>` - Set check arguments
- `/ruff format args <args>` - Set format arguments
- `/ruff help` - Show this help

**Priority Order:** Commands > Environment Variables > Plugin Constants

**Default Behavior:** Serious-only mode is enabled by default to focus on functional errors only. Use `/ruff check-only-serious off` to enable full linting.

**Environment Variables:**
- RUFF_FORMAT: true/false/on/off/1/0 - Enable auto-formatting
- RUFF_CHECK_ARGS: Additional arguments for ruff check
- RUFF_FORMAT_ARGS: Additional arguments for ruff format"""
            imsg(help_text)
            return False, False
        else:
            emsg(
                f"[X] Unknown ruff command: {cmd}. Use `/ruff help` for available commands."
            )
            return False, False

    except Exception as e:
        emsg(f"[X] Error handling ruff command: {e}")
        return False, False


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    global _aicoder_ref, _original_write_file, _original_edit_file

    _aicoder_ref = aicoder_instance

    # Register command handler directly to command_handlers
    aicoder_instance.command_handlers["/ruff"] = _handle_ruff_command

    if not _is_ruff_available():
        try:
            from aicoder.utils import alert_critical, alert_info
            alert_critical("Ruff not found - plugin will be disabled")
            alert_info("Install with: pip install ruff")
        except ImportError:
            print("[!] Ruff not found - plugin will be disabled")
            print("[i] Install with: pip install ruff")
        return False

    try:
        # Import and monkey patch the internal tool functions
        from aicoder.tool_manager.executor import INTERNAL_TOOL_FUNCTIONS

        # Get the CURRENT functions (might already be patched by other plugins!)
        _original_write_file = INTERNAL_TOOL_FUNCTIONS.get("write_file")
        _original_edit_file = INTERNAL_TOOL_FUNCTIONS.get("edit_file")

        # Create patched functions
        def patched_write_file(path: str, content: str, stats) -> str:
            result = _original_write_file(path, content, stats)
            _check_file_with_ruff(path)
            return result

        def patched_edit_file(
            path: str, old_string: str, new_string: str, stats=None
        ) -> str:
            result = _original_edit_file(path, old_string, new_string, stats)
            _check_file_with_ruff(path)
            return result

        # Apply monkey patches
        INTERNAL_TOOL_FUNCTIONS["write_file"] = patched_write_file
        INTERNAL_TOOL_FUNCTIONS["edit_file"] = patched_edit_file

        serious_mode = _is_ruff_serious_only_enabled()
        mode_text = "serious-only mode" if serious_mode else "full linting mode"
        print(f"[✓] Ruff plugin activated - Auto-format: {ENABLE_RUFF_FORMAT}, Mode: {mode_text}")
        return True

    except ImportError as e:
        try:
            from aicoder.utils import alert_critical
            alert_critical(f"Failed to import internal tools: {e}")
        except ImportError:
            print(f"[X] Failed to import internal tools: {e}")
        return False

    except Exception as e:
        try:
            from aicoder.utils import alert_critical
            alert_critical(f"Failed to initialize Ruff plugin: {e}")
        except ImportError:
            print(f"[X] Failed to initialize Ruff plugin: {e}")
        import traceback

        traceback.print_exc()
        return False


def _is_ruff_available() -> bool:
    """Check if ruff is installed and available."""
    return shutil.which("ruff") is not None


def _check_file_with_ruff(file_path: str) -> None:
    """Check a file with ruff and add message if issues found."""
    if not file_path.endswith(".py") or not _is_ruff_enabled():
        return

    try:
        abs_path = os.path.abspath(file_path)

        # Run ruff check
        cmd = ["ruff", "check", abs_path]
        check_args = _get_effective_check_args()
        if check_args:
            cmd.extend(check_args.split())

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0 and result.stdout.strip():
            _add_ruff_issues_message(abs_path, result.stdout)
            # Don't format if there are issues that need to be fixed first
            return

        # Only run ruff format if no issues were found
        if _is_ruff_format_enabled():
            _format_file_with_ruff(abs_path)

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Ruff check failed for {file_path}: {e}")
        except ImportError:
            print(f"[!] Ruff check failed for {file_path}: {e}")


def _format_file_with_ruff(file_path: str) -> None:
    """Format a file with ruff format."""
    try:
        cmd = ["ruff", "format", file_path]
        format_args = _get_ruff_format_args()
        if format_args:
            cmd.extend(format_args.split())

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            if (
                "reformatted" in result.stderr.lower()
                or "reformatted" in result.stdout.lower()
            ):
                _add_format_message(file_path)
        else:
            try:
                from aicoder.utils import alert_warning
                alert_warning(f"Ruff format failed for {file_path}: {result.stderr}")
            except ImportError:
                print(f"[!] Ruff format failed for {file_path}: {result.stderr}")

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Ruff format failed for {file_path}: {e}")
        except ImportError:
            print(f"[!] Ruff format failed for {file_path}: {e}")


def _add_format_message(file_path: str) -> None:
    """Add a user message about ruff formatting that occurred."""
    try:
        # Create a user-friendly message that clearly indicates it's from the plugin
        message_content = f"""[*] Ruff Plugin: File Formatted

The Ruff plugin automatically formatted the file to improve code style and consistency:

File: {file_path}
Plugin Action: File was reformatted using ruff format
Status: Formatting completed successfully

The file content has been updated to follow Python formatting standards."""

        # Add to pending tool messages (will be processed after tool results)
        user_message = {"role": "user", "content": message_content}

        # Use the pending_tool_messages system
        _aicoder_ref.tool_manager.executor.pending_tool_messages.append(user_message)
        print("[*] Ruff formatting completed - AI will be notified")

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Failed to add ruff format message: {e}")
        except ImportError:
            print(f"[!] Failed to add ruff format message: {e}")


def _add_ruff_issues_message(file_path: str, ruff_output: str) -> None:
    """Add a user message about ruff issues found."""
    try:
        # Create a user-friendly message that clearly indicates it's from the plugin
        message_content = f"""Ruff Plugin: Issues Detected in {file_path}

The Ruff plugin automatically detected code quality issues in the file you just saved and is asking the AI to fix them:

```
{ruff_output}
```

Plugin Action: The AI will now attempt to fix these issues automatically.
File: {file_path}
Tool: Use edit_file or write_file to resolve the problems

The file has already been saved, so the AI needs to edit it again to resolve the issues."""

        # Add to pending tool messages (will be processed after tool results)
        user_message = {"role": "user", "content": message_content}

        # Use the pending_tool_messages system
        _aicoder_ref.tool_manager.executor.pending_tool_messages.append(user_message)
        try:
            from aicoder.utils import alert_critical
            alert_critical("Ruff issues found - AI will be notified")
        except ImportError:
            print("Ruff issues found - AI will be notified")

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Failed to add ruff issues message: {e}")
        except ImportError:
            print(f"[!] Failed to add ruff issues message: {e}")


def cleanup():
    """Clean up the Ruff plugin by restoring original functions."""
    global _original_write_file, _original_edit_file

    try:
        from aicoder.tool_manager.executor import INTERNAL_TOOL_FUNCTIONS

        if _original_write_file:
            INTERNAL_TOOL_FUNCTIONS["write_file"] = _original_write_file

        if _original_edit_file:
            INTERNAL_TOOL_FUNCTIONS["edit_file"] = _original_edit_file

        print("[✓] Ruff plugin cleaned up")

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Failed to cleanup Ruff plugin: {e}")
        except ImportError:
            print(f"[!] Failed to cleanup Ruff plugin: {e}")


# Plugin metadata
PLUGIN_NAME = "Ruff Code Quality"
PLUGIN_VERSION = __version__
PLUGIN_DESCRIPTION = "Automatic ruff checks and formatting for Python files"
PLUGIN_AUTHOR = "AI Coder"
