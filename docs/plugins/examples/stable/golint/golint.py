"""
Go Lint Plugin for AI Coder - Automatic Go Code Quality Checks

This plugin automatically runs go vet on Go files when they are saved/edited
and prompts the AI to fix any issues found. Optionally auto-formats code with go fmt.

Features:
- Automatic go vet check on .go file modifications
- User message generation when issues are found
- Optional auto-formatting with go fmt
- Graceful fallback when go is not installed
- Configurable via environment variables or plugin constants

Environment Variables:
- GOLINT_FORMAT: Enable auto-formatting (default: False)

Plugin Constants:
- ENABLE_GOLINT_FORMAT: Override auto-formatting setting (default: False)
"""

import os
import shutil
import subprocess


# Plugin configuration
def _parse_bool_env(var_name: str, default: bool = False) -> bool:
    """Parse boolean environment variable that accepts 1/0, true/false, on/off."""
    value = os.getenv(var_name, "").lower()
    return value in {"1", "true", "on"} if value else default


ENABLE_GOLINT_FORMAT = _parse_bool_env("GOLINT_FORMAT", False)

# Global reference to aicoder instance
_aicoder_ref = None

# Original functions to monkey patch
_original_write_file = None
_original_edit_file = None

# Plugin version
__version__ = "1.0.0"

# Cache for Go project detection (checked once per session)
_is_go_project_cache = None


def _is_golint_enabled() -> bool:
    """Check if go vet checking is enabled (persistent config override)."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        return _aicoder_ref.persistent_config.get("golint.enabled", True)
    return True


def _is_golint_format_enabled() -> bool:
    """Check if go fmt formatting is enabled (persistent config override)."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        return _aicoder_ref.persistent_config.get(
            "golint.format_enabled", ENABLE_GOLINT_FORMAT
        )
    return ENABLE_GOLINT_FORMAT


def _set_golint_config(key: str, value: str) -> None:
    """Set golint config in persistent storage."""
    if _aicoder_ref and hasattr(_aicoder_ref, "persistent_config"):
        _aicoder_ref.persistent_config[f"golint.{key}"] = value
        print(f"[✓] Golint {key} set to: {value}")
    else:
        print("[X] Persistent config not available")


def _handle_golint_command(args: list[str]) -> tuple[bool, bool]:
    """Handle /golint commands."""
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
            enabled = _is_golint_enabled()
            format_enabled = _is_golint_format_enabled()

            status = f"""Go Lint Plugin Status

- **Checking**: {"[✓] Enabled" if enabled else "[X] Disabled"}
- **Auto-format**: {"[✓] Enabled" if format_enabled else "[X] Disabled"}

**Commands:**
- `/golint check on/off` - Enable/disable checking
- `/golint format on/off` - Enable/disable auto-formatting
- `/golint help` - Show this help"""
            imsg(status)
            return False, False

        cmd = args[0].lower()

        if cmd == "check":
            if len(args) >= 2:
                check_cmd = args[1].lower()
                if check_cmd in ["on", "off"]:
                    _set_golint_config("enabled", check_cmd == "on")
                    imsg(f"[✓] Go vet checking turned {check_cmd}")
                    return False, False
                else:
                    emsg("[X] Usage: `/golint check on|off`")
                    return False, False
            else:
                emsg("[X] Usage: `/golint check on|off`")
                return False, False

        elif cmd == "format":
            if len(args) >= 2:
                format_cmd = args[1].lower()
                if format_cmd in ["on", "off"]:
                    _set_golint_config("format_enabled", format_cmd == "on")
                    imsg(f"[✓] Go fmt auto-formatting turned {format_cmd}")
                    return False, False
                else:
                    emsg("[X] Usage: `/golint format on|off`")
                    return False, False
            else:
                emsg("[X] Usage: `/golint format on|off`")
                return False, False

        elif cmd == "help":
            help_text = """Go Lint Plugin Commands

- `/golint` - Show current status
- `/golint check on|off` - Enable/disable checking
- `/golint format on|off` - Enable/disable auto-formatting
- `/golint help` - Show this help

**Tools Used:**
- `go vet` - Finds serious bugs and suspicious constructs
- `go fmt` - Formats Go code according to standard style

**Environment Variables:**
- GOLINT_FORMAT: true/false/on/off/1/0 - Enable auto-formatting"""
            imsg(help_text)
            return False, False
        else:
            emsg(
                f"[X] Unknown golint command: {cmd}. Use `/golint help` for available commands."
            )
            return False, False

    except Exception as e:
        emsg(f"[X] Error handling golint command: {e}")
        return False, False


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    global _aicoder_ref, _original_write_file, _original_edit_file

    _aicoder_ref = aicoder_instance

    # Register command handler directly to command_handlers
    aicoder_instance.command_handlers["/golint"] = _handle_golint_command

    # Only show background alerts if this is actually a Go project (cached result)
    is_go_project = _is_go_project()
    
    if not _is_go_available():
        if is_go_project:
            try:
                from aicoder.utils import alert_critical, alert_info
                alert_critical("Go not found - plugin will be disabled")
                alert_info("Install Go: https://golang.org/dl/")
            except ImportError:
                print("[!] Go not found - plugin will be disabled")
                print("[i] Install Go: https://golang.org/dl/")
        else:
            print("[i] Go Lint plugin available (no Go project detected)")
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

            _check_file_with_go_vet(path)
            return result

        def patched_edit_file(
            path: str, old_string: str, new_string: str, stats=None, metadata: bool = False
        ) -> str:
            result = _original_edit_file(path, old_string, new_string, stats, metadata)

            _check_file_with_go_vet(path)
            return result

        # Apply monkey patches
        INTERNAL_TOOL_FUNCTIONS["write_file"] = patched_write_file
        INTERNAL_TOOL_FUNCTIONS["edit_file"] = patched_edit_file

        print(f"[✓] Go Lint plugin activated - Auto-format: {ENABLE_GOLINT_FORMAT}")
        return True

    except ImportError as e:
        if is_go_project:
            try:
                from aicoder.utils import alert_critical
                alert_critical(f"Failed to import internal tools: {e}")
            except ImportError:
                print(f"[X] Failed to import internal tools: {e}")
        else:
            print(f"[i] Go Lint plugin: Failed to import internal tools: {e}")
        return False

    except Exception as e:
        if is_go_project:
            try:
                from aicoder.utils import alert_critical
                alert_critical(f"Failed to initialize Go Lint plugin: {e}")
            except ImportError:
                print(f"[X] Failed to initialize Go Lint plugin: {e}")
        else:
            print(f"[i] Go Lint plugin: Failed to initialize: {e}")
        import traceback

        traceback.print_exc()
        return False


def _is_go_available() -> bool:
    """Check if go is installed and available."""
    return shutil.which("go") is not None


def _is_go_project() -> bool:
    """Fast check if current directory is a Go project (cached)."""
    global _is_go_project_cache
    
    # Return cached result if already computed
    if _is_go_project_cache is not None:
        return _is_go_project_cache
    
    import os
    import glob
    
    # Quick checks for Go project indicators
    current_dir = os.getcwd()
    
    # Check for go.mod (most reliable indicator)
    if os.path.exists(os.path.join(current_dir, "go.mod")):
        _is_go_project_cache = True
        return True
    
    # Check for .go files (fast glob)
    try:
        go_files = glob.glob("*.go", root_dir=current_dir)
        if go_files:
            _is_go_project_cache = True
            return True
    except (OSError, AttributeError):
        # Fallback for older Python versions
        try:
            for item in os.listdir(current_dir):
                if item.endswith('.go'):
                    _is_go_project_cache = True
                    return True
        except OSError:
            pass
    
    _is_go_project_cache = False
    return False


def _check_file_with_go_vet(file_path: str) -> None:
    """Check a file with go vet and add message if issues found."""

    if not file_path.endswith(".go") or not _is_golint_enabled():
        return

    try:
        import time

        file_dir = os.path.dirname(os.path.abspath(file_path))
        file_name = os.path.basename(file_path)

        # Fast syntax check first with go build (much faster than go vet)
        print(f"Running fast syntax check on {file_name}...")  # Debug
        start_time = time.time()

        # Use go build for syntax checking - much faster than go vet
        # We build to /dev/null to avoid creating binaries
        cmd = ["go", "build", "-o", "/dev/null", file_name]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=240,  # Longer timeout for slower systems
            cwd=file_dir,  # Run in the directory containing the Go file
        )

        syntax_elapsed = time.time() - start_time

        # If syntax check fails, report and return
        if result.returncode != 0:
            error_output = result.stderr.strip() or result.stdout.strip()
            print(f"[X] Syntax error in {file_name} ({syntax_elapsed:.2f}s)")
            _add_go_vet_issues_message(file_path, f"Syntax Error: {error_output}")
            return

        # If syntax is OK, do a quick go vet for logic issues (but with shorter timeout)
        vet_start = time.time()

        cmd = ["go", "vet", file_name]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,  # Shorter timeout for vet
            cwd=file_dir,  # Run in the directory containing the Go file
        )

        vet_elapsed = time.time() - vet_start

        if result.returncode != 0 and (result.stdout.strip() or result.stderr.strip()):
            # Combine stdout and stderr for comprehensive error reporting
            vet_output = result.stdout.strip() or result.stderr.strip()
            total_elapsed = syntax_elapsed + vet_elapsed
            print(f"Go vet issues found in {file_name} ({total_elapsed:.2f}s)")
            _add_go_vet_issues_message(file_path, vet_output)
            # Don't format if there are issues that need to be fixed first
            return

        # Success! No issues found
        total_elapsed = syntax_elapsed + vet_elapsed
        print(f"[✓] {file_name} passed all checks ({total_elapsed:.2f}s)")

        # Only run go fmt if no issues were found
        if _is_golint_format_enabled():
            _format_file_with_go_fmt(file_path)

    except subprocess.TimeoutExpired:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Go tools timeout for {file_path} - skipping checks")
        except ImportError:
            print(f"[!] Go tools timeout for {file_path} - skipping checks")
    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Go vet failed for {file_path}: {e}")
        except ImportError:
            print(f"[!] Go vet failed for {file_path}: {e}")


def _format_file_with_go_fmt(file_path: str) -> None:
    """Format a file with go fmt."""
    try:
        file_dir = os.path.dirname(os.path.abspath(file_path))
        file_name = os.path.basename(file_path)

        cmd = ["go", "fmt", file_name]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=file_dir,  # Run in the directory containing the Go file
        )

        # go fmt doesn't output anything if successful, but we can check if file was modified
        if result.returncode == 0:
            # go fmt is silent on success, so we assume formatting happened
            # In a real implementation, you might want to check file modification time
            _add_go_fmt_message(file_path)
        else:
            try:
                from aicoder.utils import alert_warning
                alert_warning(f"Go fmt failed for {file_path}: {result.stderr}")
            except ImportError:
                print(f"[!] Go fmt failed for {file_path}: {result.stderr}")

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Go fmt failed for {file_path}: {e}")
        except ImportError:
            print(f"[!] Go fmt failed for {file_path}: {e}")


def _add_go_fmt_message(file_path: str) -> None:
    """Add a user message about go fmt formatting that occurred."""
    if not _aicoder_ref:
        print("[!] Go fmt completed but no aicoder context available")
        return

    try:
        # Create a user-friendly message that clearly indicates it's from the plugin
        message_content = f"""[*] Go Lint Plugin: File Formatted

The Go Lint plugin automatically formatted the file to improve code style and consistency:

File: {file_path}
Plugin Action: File was reformatted using go fmt
Status: Formatting completed successfully

The file content has been updated to follow Go formatting standards."""

        # Add to pending tool messages (will be processed after tool results)
        user_message = {"role": "user", "content": message_content}

        # Use the pending_tool_messages system
        _aicoder_ref.tool_manager.executor.pending_tool_messages.append(user_message)
        print("[*] Go fmt formatting completed - AI will be notified")

    except Exception as e:
        print(f"[!] Failed to add go fmt message: {e}")


def _add_go_vet_issues_message(file_path: str, vet_output: str) -> None:
    """Add a user message about go vet issues found."""
    if not _aicoder_ref:
        print("[!] Go vet issues found but no aicoder context available")
        return

    try:
        # Create a user-friendly message that clearly indicates it's from the plugin
        message_content = f"""Go Lint Plugin: Issues Detected in {file_path}

The Go Lint plugin automatically detected code quality issues in the file you just saved and is asking the AI to fix them:

```
{vet_output}
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
            alert_critical("Go vet issues found - AI will be notified")
        except ImportError:
            print("Go vet issues found - AI will be notified")

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Failed to add go vet message: {e}")
        except ImportError:
            print(f"[!] Failed to add go vet message: {e}")


def cleanup():
    """Clean up the Go Lint plugin by restoring original functions."""
    global _original_write_file, _original_edit_file

    try:
        from aicoder.tool_manager.executor import INTERNAL_TOOL_FUNCTIONS

        if _original_write_file:
            INTERNAL_TOOL_FUNCTIONS["write_file"] = _original_write_file

        if _original_edit_file:
            INTERNAL_TOOL_FUNCTIONS["edit_file"] = _original_edit_file

        print("[✓] Go Lint plugin cleaned up")

    except Exception as e:
        try:
            from aicoder.utils import alert_warning
            alert_warning(f"Failed to cleanup Go Lint plugin: {e}")
        except ImportError:
            print(f"[!] Failed to cleanup Go Lint plugin: {e}")


# Plugin metadata
PLUGIN_NAME = "Go Lint Code Quality"
PLUGIN_VERSION = __version__
PLUGIN_DESCRIPTION = "Automatic go vet checks and go fmt formatting for Go files"
PLUGIN_AUTHOR = "AI Coder"
