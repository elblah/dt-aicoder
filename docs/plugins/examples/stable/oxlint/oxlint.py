"""
Oxlint Plugin for AI Coder - Automatic JavaScript/TypeScript Code Quality Checks

This plugin automatically runs oxlint on JavaScript and TypeScript files when they are saved/edited
and prompts the AI to fix any issues found. Optionally auto-formats code.

Features:
- Automatic oxlint check on .js, .jsx, .ts, .tsx file modifications
- User message generation when issues are found
- Optional auto-formatting with oxlint --fix
- Graceful fallback when oxlint is not installed
- Configurable via environment variables or plugin constants

Environment Variables:
- OXLINT_FORMAT: Enable auto-formatting (default: False)
- OXLINT_ARGS: Additional arguments for oxlint (default: "")

Plugin Constants:
- ENABLE_OXLINT_FORMAT: Override auto-formatting setting (default: False)
- OXLINT_ARGS: Default arguments for oxlint
"""

import os
import shutil
import subprocess


# Plugin configuration
def _parse_bool_env(var_name: str, default: bool = False) -> bool:
    """Parse boolean environment variable that accepts 1/0, true/false, on/off."""
    value = os.getenv(var_name, "").lower()
    return value in {"1", "true", "on"} if value else default


ENABLE_OXLINT_FORMAT = _parse_bool_env("OXLINT_FORMAT", False)
OXLINT_ARGS = os.getenv("OXLINT_ARGS", "")

# Global reference to aicoder instance
_aicoder_ref = None

# Original functions to monkey patch
_original_write_file = None
_original_edit_file = None

# Plugin version
__version__ = "1.0.0"


def _is_oxlint_enabled() -> bool:
    """Check if oxlint checking is enabled (persistent config override)."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        return _aicoder_ref.persistent_config.get("oxlint.enabled", True)
    return True


def _is_oxlint_format_enabled() -> bool:
    """Check if oxlint formatting is enabled (persistent config override)."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        return _aicoder_ref.persistent_config.get(
            "oxlint.format_enabled", ENABLE_OXLINT_FORMAT
        )
    return ENABLE_OXLINT_FORMAT


def _get_oxlint_args() -> str:
    """Get oxlint arguments from persistent config."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        return _aicoder_ref.persistent_config.get("oxlint.args", OXLINT_ARGS)
    return OXLINT_ARGS


def _set_oxlint_config(key: str, value: str) -> None:
    """Set oxlint config in persistent storage."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        _aicoder_ref.persistent_config[f"oxlint.{key}"] = value
        print(f"[✓] Oxlint {key} set to: {value}")
    else:
        print("[X] Persistent config not available")


def _handle_oxlint_command(args: list[str]) -> tuple[bool, bool]:
    """Handle /oxlint commands."""
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
            enabled = _is_oxlint_enabled()
            format_enabled = _is_oxlint_format_enabled()
            oxlint_args = _get_oxlint_args()

            status = f"""Oxlint Plugin Status

- **Checking**: {"[✓] Enabled" if enabled else "[X] Disabled"}
- **Auto-format**: {"[✓] Enabled" if format_enabled else "[X] Disabled"}
- **Args**: `{oxlint_args or "default"}`

**Commands:**
- `/oxlint check on/off` - Enable/disable checking
- `/oxlint format on/off` - Enable/disable auto-formatting
- `/oxlint args <args>` - Set oxlint arguments
- `/oxlint help` - Show this help"""
            imsg(status)
            return False, False

        cmd = args[0].lower()

        if cmd == "check":
            if len(args) >= 2:
                check_cmd = args[1].lower()
                if check_cmd in ["on", "off"]:
                    _set_oxlint_config("enabled", check_cmd == "on")
                    imsg(f"[✓] Oxlint checking turned {check_cmd}")
                    return False, False
                else:
                    emsg("[X] Usage: `/oxlint check on|off`")
                    return False, False
            else:
                emsg("[X] Usage: `/oxlint check on|off`")
                return False, False

        elif cmd == "format":
            if len(args) >= 2:
                format_cmd = args[1].lower()
                if format_cmd in ["on", "off"]:
                    _set_oxlint_config("format_enabled", format_cmd == "on")
                    imsg(f"[✓] Oxlint auto-formatting turned {format_cmd}")
                    return False, False
                else:
                    emsg("[X] Usage: `/oxlint format on|off`")
                    return False, False
            else:
                emsg("[X] Usage: `/oxlint format on|off`")
                return False, False

        elif cmd == "args":
            if len(args) >= 2:
                new_args = " ".join(args[1:])
                _set_oxlint_config("args", new_args)
                imsg(f"[✓] Oxlint arguments set to: `{new_args}`")
                return False, False
            else:
                emsg("[X] Usage: `/oxlint args <arguments>`")
                return False, False

        elif cmd == "help":
            help_text = """Oxlint Plugin Commands

- `/oxlint` - Show current status
- `/oxlint check on|off` - Enable/disable checking
- `/oxlint format on|off` - Enable/disable auto-formatting
- `/oxlint args <args>` - Set oxlint arguments
- `/oxlint help` - Show this help

**Tool Used:**
- `bun x oxlint` - Fast JavaScript/TypeScript linter

**Environment Variables:**
- OXLINT_FORMAT: true/false/on/off/1/0 - Enable auto-formatting
- OXLINT_ARGS: Additional arguments for oxlint"""
            imsg(help_text)
            return False, False
        else:
            emsg(
                f"[X] Unknown oxlint command: {cmd}. Use `/oxlint help` for available commands."
            )
            return False, False

    except Exception as e:
        emsg(f"[X] Error handling oxlint command: {e}")
        return False, False


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    global _aicoder_ref, _original_write_file, _original_edit_file

    _aicoder_ref = aicoder_instance

    # Register command handler directly to command_handlers
    aicoder_instance.command_handlers["/oxlint"] = _handle_oxlint_command

    if not _is_oxlint_available():
        try:
            from aicoder.utils import alert_critical, alert_info
            alert_critical("Oxlint not found - plugin will be disabled")
            alert_info("Install with: bun add -D oxlint")
        except ImportError:
            print("[!] Oxlint not found - plugin will be disabled")
            print("[i] Install with: bun add -D oxlint")
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
            _check_file_with_oxlint(path)
            return result

        def patched_edit_file(
            path: str, old_string: str, new_string: str, stats=None, metadata: bool = False
        ) -> str:
            result = _original_edit_file(path, old_string, new_string, stats, metadata)
            _check_file_with_oxlint(path)
            return result

        # Apply monkey patches
        INTERNAL_TOOL_FUNCTIONS["write_file"] = patched_write_file
        INTERNAL_TOOL_FUNCTIONS["edit_file"] = patched_edit_file

        print(f"[✓] Oxlint plugin activated - Auto-format: {ENABLE_OXLINT_FORMAT}")
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
            alert_critical(f"Failed to initialize Oxlint plugin: {e}")
        except ImportError:
            print(f"[X] Failed to initialize Oxlint plugin: {e}")
        import traceback

        traceback.print_exc()
        return False


# Cache for bun availability (checked once per session)
_bun_available_cache = None

def _is_bun_available() -> bool:
    """Check if bun is installed and available (cached)."""
    global _bun_available_cache
    
    # Return cached result if already computed
    if _bun_available_cache is not None:
        return _bun_available_cache
    
    _bun_available_cache = shutil.which("bun") is not None
    return _bun_available_cache

def _is_oxlint_available() -> bool:
    """Check if oxlint can be used (checks for bun availability only)."""
    return _is_bun_available()


def _check_file_with_oxlint(file_path: str) -> None:
    """Check a file with oxlint and add message if issues found."""
    if not _is_js_ts_file(file_path) or not _is_oxlint_enabled():
        return

    try:
        abs_path = os.path.abspath(file_path)

        # Run oxlint check
        cmd = ["bun", "x", "oxlint"]
        oxlint_args = _get_oxlint_args()
        if oxlint_args:
            cmd.extend(oxlint_args.split())
        cmd.append(abs_path)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0 and result.stdout.strip():
            _add_oxlint_issues_message(abs_path, result.stdout)
            # Don't format if there are issues that need to be fixed first
            return

        # Only run oxlint --fix if no issues were found and formatting is enabled
        if _is_oxlint_format_enabled():
            _format_file_with_oxlint(abs_path)

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Oxlint check failed for {file_path}: {e}")
        except ImportError:
            print(f"[!] Oxlint check failed for {file_path}: {e}")


def _format_file_with_oxlint(file_path: str) -> None:
    """Format a file with oxlint --fix."""
    try:
        cmd = ["bun", "x", "oxlint", "--fix"]
        oxlint_args = _get_oxlint_args()
        if oxlint_args:
            cmd.extend(oxlint_args.split())
        cmd.append(file_path)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Check if any fixes were applied by checking stderr output
            if result.stderr.strip() and "fixed" in result.stderr.lower():
                _add_format_message(file_path)
        else:
            try:
                from aicoder.utils import alert_warning
                alert_warning(f"Oxlint fix failed for {file_path}: {result.stderr}")
            except ImportError:
                print(f"[!] Oxlint fix failed for {file_path}: {result.stderr}")

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Oxlint fix failed for {file_path}: {e}")
        except ImportError:
            print(f"[!] Oxlint fix failed for {file_path}: {e}")


def _is_js_ts_file(file_path: str) -> bool:
    """Check if file is a JavaScript or TypeScript file."""
    return any(file_path.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'])


def _add_format_message(file_path: str) -> None:
    """Add a user message about oxlint formatting that occurred."""
    try:
        # Create a user-friendly message that clearly indicates it's from the plugin
        message_content = f"""[*] Oxlint Plugin: File Formatted

The Oxlint plugin automatically formatted the file to improve code style and consistency:

File: {file_path}
Plugin Action: File was reformatted using oxlint --fix
Status: Formatting completed successfully

The file content has been updated to follow JavaScript/TypeScript formatting standards."""

        # Add to pending tool messages (will be processed after tool results)
        user_message = {"role": "user", "content": message_content}

        # Use the pending_tool_messages system
        _aicoder_ref.tool_manager.executor.pending_tool_messages.append(user_message)
        print("[*] Oxlint formatting completed - AI will be notified")

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Failed to add oxlint format message: {e}")
        except ImportError:
            print(f"[!] Failed to add oxlint format message: {e}")


def _add_oxlint_issues_message(file_path: str, oxlint_output: str) -> None:
    """Add a user message about oxlint issues found."""
    try:
        # Create a user-friendly message that clearly indicates it's from the plugin
        message_content = f"""Oxlint Plugin: Issues Detected in {file_path}

The Oxlint plugin automatically detected code quality issues in the file you just saved and is asking the AI to fix them:

```
{oxlint_output}
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
            alert_critical("Oxlint issues found - AI will be notified")
        except ImportError:
            print("Oxlint issues found - AI will be notified")

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Failed to add oxlint issues message: {e}")
        except ImportError:
            print(f"[!] Failed to add oxlint issues message: {e}")


def cleanup():
    """Clean up the Oxlint plugin by restoring original functions."""
    global _original_write_file, _original_edit_file

    try:
        from aicoder.tool_manager.executor import INTERNAL_TOOL_FUNCTIONS

        if _original_write_file:
            INTERNAL_TOOL_FUNCTIONS["write_file"] = _original_write_file

        if _original_edit_file:
            INTERNAL_TOOL_FUNCTIONS["edit_file"] = _original_edit_file

        print("[✓] Oxlint plugin cleaned up")

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Failed to cleanup Oxlint plugin: {e}")
        except ImportError:
            print(f"[!] Failed to cleanup Oxlint plugin: {e}")


# Plugin metadata
PLUGIN_NAME = "Oxlint Code Quality"
PLUGIN_VERSION = __version__
PLUGIN_DESCRIPTION = "Automatic oxlint checks and formatting for JavaScript/TypeScript files"
PLUGIN_AUTHOR = "AI Coder"