"""
Glob Plugin for AI Coder

This plugin provides file pattern matching capabilities with:
1. A /glob command for users to search for files using patterns
2. A glob tool implementation for the AI to find files
3. Support for multiple tools: ripgrep, fd-find, and Python glob as fallback
"""

import os
import glob
import subprocess

from typing import Optional, List

# Import the shared utility function from the main aicoder package
try:
    from aicoder.utils import check_tool_availability
except ImportError:
    # Fallback for standalone testing
    def check_tool_availability(tool_name: str) -> bool:
        """Check if a tool is available in PATH."""
        try:
            result = subprocess.run(["which", tool_name], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

# Default limit for number of files to return
DEFAULT_FILE_LIMIT = 2000

# Custom glob tool definition
GLOB_TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "approval_excludes_arguments": False,
    "approval_key_exclude_arguments": [],
    "name": "glob",
    "description": f"Find files matching a pattern using ripgrep when available, Python glob as fallback. Supports ** for recursive matching. Returns max {DEFAULT_FILE_LIMIT} files.",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Pattern to search for (e.g., '*.py', 'test_*', '**/*.py', 'aicoder/**/*.py'). Supports ** for recursive directory matching.",
            }
        },
        "required": ["pattern"],
        "additionalProperties": False,
    },
}


def _search_with_rg(pattern: str, file_limit: int = DEFAULT_FILE_LIMIT) -> str:
    """Search for files using ripgrep with glob patterns."""
    try:
        # Use rg --files --glob for file listing with glob patterns (safe against injection)
        cmd = [
            "bash",
            "-c",
            f'{{ "$1" --files --glob "$2"; }} | head -n {file_limit}',
            "_",
            "rg",
            pattern,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if (
            result.returncode == 0 or result.returncode == 1
        ):  # 0 = files found, 1 = no files
            lines = result.stdout.strip().split("\n")
            output = (
                "\n".join(lines)
                if lines and lines[0]
                else "No files found matching pattern"
            )
            # Check if we hit the limit
            if len(lines) >= file_limit:
                output += f"\n... (showing first {file_limit} lines)"
            return output
        else:
            return f"Error running rg: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing rg: {e}"


def _search_with_fd(
    pattern: str, file_limit: int = DEFAULT_FILE_LIMIT, command_name: str = "fd"
) -> str:
    """Search for files using fd-find."""
    try:
        # Use fd/fdfind with --glob for glob patterns and file count limit
        cmd = [
            "bash",
            "-c",
            f"{command_name} --glob '{pattern}' | head -n {file_limit}",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if (
            result.returncode == 0 or result.returncode == 1
        ):  # 0 = matches found, 1 = no matches
            lines = result.stdout.strip().split("\n")
            output = (
                "\n".join(lines)
                if lines and lines[0]
                else "No files found matching pattern"
            )
            # Check if we hit the limit
            if len(lines) >= file_limit:
                output += f"\n... (showing first {file_limit} lines)"
            return output
        else:
            return f"Error running {command_name}: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing {command_name}: {e}"


def _search_with_python_glob(pattern: str, file_limit: int = DEFAULT_FILE_LIMIT) -> str:
    """Search for files using Python's glob module."""
    try:
        # Use recursive=True for patterns containing **
        if "**" in pattern:
            matches = glob.glob(pattern, recursive=True)
        else:
            matches = glob.glob(pattern)

        # Filter to only include files (not directories)
        files = [match for match in matches if os.path.isfile(match)]

        if files:
            # Limit results
            if len(files) > file_limit:
                files = files[:file_limit]
                output = "\n".join(files)
                output += (
                    f"\n... (showing first {file_limit} files of {len(files)} total)"
                )
            else:
                output = "\n".join(files)
            return output
        else:
            return "No files found matching pattern"
    except Exception as e:
        return f"Error searching with glob: {e}"


def execute_glob(pattern: str, stats=None) -> str:
    """Find files matching a pattern using fd-find when available, Python glob as fallback."""
    try:
        # Validate input
        if not pattern:
            return "Error: Pattern cannot be empty."

        # Try ripgrep first (compatible glob behavior), fallback to Python glob
        if check_tool_availability("rg"):
            return _search_with_rg(pattern, DEFAULT_FILE_LIMIT)
        elif check_tool_availability("fd"):
            return _search_with_fd(pattern, DEFAULT_FILE_LIMIT, "fd")
        elif check_tool_availability("fdfind"):
            return _search_with_fd(pattern, DEFAULT_FILE_LIMIT, "fdfind")
        else:
            # Fallback to Python glob for consistent behavior
            return _search_with_python_glob(pattern, DEFAULT_FILE_LIMIT)
    except Exception as e:
        return f"Error searching for files with pattern '{pattern}': {e}"


# Global reference to store the aicoder instance
_aicoder_ref = None


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        # Store reference to aicoder instance
        global _aicoder_ref
        _aicoder_ref = aicoder_instance

        # Add /glob command to the command registry
        aicoder_instance.command_handlers["/glob"] = _handle_glob_command
        aicoder_instance.command_handlers["/g"] = _handle_glob_command  # Alias

        # Register the glob tool
        if hasattr(aicoder_instance, "tool_manager") and hasattr(
            aicoder_instance.tool_manager, "registry"
        ):
            # Add the tool definition to the registry
            aicoder_instance.tool_manager.registry.mcp_tools["glob"] = (
                GLOB_TOOL_DEFINITION
            )

            # Override the tool execution to use our implementation
            original_execute_tool = aicoder_instance.tool_manager.executor.execute_tool

            def patched_execute_tool(tool_name, arguments, tool_index=0, total_tools=0):
                if tool_name == "glob":
                    try:
                        # Extract arguments
                        pattern = arguments.get("pattern")

                        if not pattern:
                            return "Error: Pattern cannot be empty.", GLOB_TOOL_DEFINITION, False

                        result = execute_glob(pattern)

                        return result, GLOB_TOOL_DEFINITION, False
                    except Exception as e:
                        return f"Error executing glob: {e}", GLOB_TOOL_DEFINITION, False
                else:
                    return original_execute_tool(tool_name, arguments, tool_index, total_tools)

            aicoder_instance.tool_manager.executor.execute_tool = patched_execute_tool

        print("[✓] Glob plugin loaded successfully")
        print("   - /glob and /g commands available")
        print("   - glob tool registered for AI use")
        return True
    except Exception as e:
        print(f"[X] Failed to load glob plugin: {e}")
        return False


def _show_glob_help():
    """Show help for glob command."""
    print("\nGlob Pattern Matching Help")
    print("==========================")
    print("Available commands:")
    print("  /glob                - Show glob tool status")
    print("  /glob help           - Show this help")
    print("  /glob <pattern>      - Find files matching pattern")
    print("\nPattern Examples:")
    print("  *.py                 - All Python files in current directory")
    print("  **/*.py              - All Python files recursively")
    print("  test_*               - Files starting with 'test_'")
    print("  aicoder/**/*.py     - All Python files in aicoder directory")
    print("  *.md                - All Markdown files")
    print("  src/**/*.js          - All JavaScript files in src directory")
    print("\nAI Tool Usage:")
    print("  The AI can use the glob tool to find files matching patterns")
    print("  Supports recursive matching with **")
    print("\nNote: Uses ripgrep/fd when available, Python glob as fallback")


def _handle_glob_command(args):
    """Handle /glob command."""
    if not args:
        # Show status
        rg_available = check_tool_availability("rg")
        fd_available = check_tool_availability("fd") or check_tool_availability("fdfind")
        
        print("\nGlob Tool Status:")
        print("=" * 20)
        print(f"ripgrep (rg): {'✓' if rg_available else '✗'}")
        print(f"fd-find (fd): {'✓' if fd_available else '✗'}")
        print("Python glob: ✓ (always available)")
        print(f"File limit: {DEFAULT_FILE_LIMIT}")
        print("\nUse '/glob help' for commands")
        print("The AI can use the glob tool to find files")
        return False, False

    # Handle subcommands
    subcommand = args[0].lower()

    if subcommand in ["help", "-h", "--help"]:
        _show_glob_help()
        return False, False
    else:
        # Treat as pattern
        pattern = " ".join(args)
        print(f"\nSearching for files matching: {pattern}")
        print("-" * 50)
        result = execute_glob(pattern)
        print(result)
        return False, False


# Plugin metadata
PLUGIN_NAME = "glob"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "File pattern matching plugin with AI integration"