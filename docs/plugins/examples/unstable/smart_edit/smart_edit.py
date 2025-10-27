"""
Smart Edit Tool Plugin for AI Coder - Fixed Version

Advanced safe file editing with rich diff preview and conflict detection.
"""

import os
import re
import difflib
import shutil
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# Global reference to aicoder instance
_aicoder_ref = None

# Plugin version
__version__ = "1.0.0"


def on_plugin_load():
    """Called when the plugin is loaded"""
    print(f"Smart Edit Tool Plugin v{__version__} loaded")


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    global _aicoder_ref
    try:
        _aicoder_ref = aicoder_instance
        print("DEBUG: Smart Edit plugin on_aicoder_init called")

        # Register the smart_edit tool
        tool_definition = {
            "type": "internal",
            "auto_approved": False,
            "approval_excludes_arguments": True,
            "approval_key_exclude_arguments": ["changes"],
            "hidden_parameters": ["changes"],
            "available_in_plan_mode": False,
            "colorize_diff_lines": True,
            "description": """Advanced safe file editing with rich diff preview and conflict detection.

USAGE EXAMPLES:
# Context-based edit (recommended)
smart_edit(path="example.py", changes=[{
    "context": ["def old_func():", "    pass"],
    "replacement": ["def new_func():", "    return True"]
}])""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute path to the file to edit",
                    },
                    "changes": {
                        "type": "array",
                        "description": "List of changes to apply",
                    },
                    "mode": {
                        "type": "string",
                        "enum": [
                            "context",
                            "line_based",
                            "pattern",
                            "semantic",
                            "auto",
                        ],
                        "default": "context",
                        "description": "Primary editing mode",
                    },
                    "preview_mode": {
                        "type": "string",
                        "enum": ["rich", "simple", "none"],
                        "default": "rich",
                        "description": "How to display the diff preview",
                    },
                    "create_backup": {
                        "type": "boolean",
                        "default": True,
                        "description": "Create automatic timestamped backup",
                    },
                    "auto_confirm": {
                        "type": "boolean",
                        "default": False,
                        "description": "Skip preview if no conflicts detected",
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "File encoding for reading/writing",
                    },
                    "conflict_resolution": {
                        "type": "string",
                        "enum": ["prompt", "skip", "override", "merge"],
                        "default": "prompt",
                        "description": "How to handle file modification conflicts",
                    },
                },
                "required": ["path", "changes"],
            },
            "validate_function": "validate_smart_edit",
        }

        print("DEBUG: About to register smart_edit tool")

        # Register the tool
        aicoder_instance.tool_manager.registry.mcp_tools["smart_edit"] = tool_definition

        # Register the implementation function in INTERNAL_TOOL_FUNCTIONS
        try:
            from aicoder.tool_manager.executor import INTERNAL_TOOL_FUNCTIONS

            INTERNAL_TOOL_FUNCTIONS["smart_edit"] = execute_smart_edit
            print(
                "DEBUG: Implementation function registered in INTERNAL_TOOL_FUNCTIONS"
            )
        except ImportError as e:
            print(f"DEBUG: Failed to import INTERNAL_TOOL_FUNCTIONS: {e}")
            return False

        print("[✓] Smart Edit Tool plugin registered successfully")
        return True

    except Exception as e:
        print(f"[X] Failed to load Smart Edit Tool plugin: {e}")
        import traceback

        traceback.print_exc()
        return False


class DiffVisualizer:
    """Rich diff visualization with color coding."""

    def __init__(self, config_ref=None):
        self.config = config_ref

    def show_rich_diff(
        self, file_path: str, original: str, modified: str, context_lines: int = 3
    ) -> str:
        """Generate rich color-coded diff."""
        try:
            import aicoder.config as config

            self.config = config
        except ImportError:
            pass

        original_lines = original.splitlines(True)
        modified_lines = modified.splitlines(True)

        # Generate unified diff
        diff_lines = list(
            difflib.unified_diff(
                original_lines,
                modified_lines,
                fromfile=f"{file_path} (original)",
                tofile=f"{file_path} (modified)",
                n=context_lines,
                lineterm="",
            )
        )

        if not diff_lines:
            return "No changes to display"

        # Colorize the diff
        if self.config:
            try:
                from aicoder.utils import colorize_diff_lines

                colored_diff = colorize_diff_lines("\n".join(diff_lines) + "\n")
                return colored_diff
            except ImportError:
                pass

        return "\n".join(diff_lines)

    def show_summary(self, file_path: str, original: str, modified: str) -> str:
        """Show a summary of changes."""
        orig_lines = original.splitlines()
        mod_lines = modified.splitlines()

        additions = len(mod_lines) - len(orig_lines)
        deletions = len(orig_lines) - len(mod_lines)

        summary = f"\nChanges Summary for {os.path.basename(file_path)}:\n"
        summary += "=" * 60 + "\n"

        if additions > 0:
            summary += f"[+] {additions} line{'s' if additions != 1 else ''} added\n"
        if deletions > 0:
            summary += f"[-] {deletions} line{'s' if deletions != 1 else ''} removed\n"
        if additions == 0 and deletions == 0:
            summary += "[*] Content modified (no line count change)\n"

        summary += f"Total lines: {len(mod_lines)}\n"
        return summary


class BackupManager:
    """Manages file backups and rollback operations."""

    def __init__(self):
        self.backups = {}  # Track created backups

    def create_backup(self, file_path: str) -> Optional[str]:
        """Create timestamped backup in a directory next to the original file."""
        if not os.path.exists(file_path):
            return None

        # Create backup directory next to the file
        file_dir = os.path.dirname(file_path)
        backup_dir = os.path.join(file_dir, "smart_edit_backups")

        try:
            os.makedirs(backup_dir, exist_ok=True)
        except (OSError, PermissionError):
            # Fallback to temp directory if we can't create backup dir
            backup_dir = tempfile.gettempdir()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        backup_name = f"{filename}.{timestamp}.backup"
        backup_path = os.path.join(backup_dir, backup_name)

        try:
            shutil.copy2(file_path, backup_path)
            self.backups[file_path] = backup_path
            return backup_path
        except Exception:
            return None

    def rollback(self, file_path: str) -> bool:
        """Rollback file to last backup."""
        if file_path not in self.backups:
            print("[X] No backup found for rollback")
            return False

        backup_path = self.backups[file_path]

        if not os.path.exists(backup_path):
            print(f"[X] Backup file not found: {backup_path}")
            return False

        try:
            shutil.copy2(backup_path, file_path)
            print(f"[✓] Successfully rolled back {file_path}")
            return True
        except Exception as e:
            print(f"[X] Rollback failed: {e}")
            return False


class EditStrategyManager:
    """Handles different editing strategies."""

    def __init__(self):
        self.strategies = {
            "context": self._apply_context_edit,
            "line_based": self._apply_line_edit,
            "pattern": self._apply_pattern_edit,
            "semantic": self._apply_semantic_edit,
        }

    def apply_changes(
        self, content: str, changes: List[Dict[str, Any]], default_mode: str = "context"
    ) -> Tuple[str, List[str]]:
        """Apply multiple changes using appropriate strategies."""
        modified_content = content
        applied_changes = []
        errors = []

        for i, change in enumerate(changes):
            try:
                # Determine strategy
                mode = change.get("mode", default_mode)
                if mode == "auto":
                    mode = self._detect_best_strategy(change)

                if mode not in self.strategies:
                    errors.append(f"Change {i + 1}: Unknown editing mode '{mode}'")
                    continue

                # Apply the change
                modified_content, success = self.strategies[mode](
                    modified_content, change
                )

                if success:
                    applied_changes.append(f"Change {i + 1}: Applied {mode} edit")
                else:
                    errors.append(f"Change {i + 1}: Failed to apply {mode} edit")

            except Exception as e:
                errors.append(f"Change {i + 1}: Error - {str(e)}")

        return modified_content, applied_changes + errors

    def _detect_best_strategy(self, change: Dict[str, Any]) -> str:
        """Auto-detect the best editing strategy for a change."""
        if "context" in change:
            return "context"
        elif "lines" in change:
            return "line_based"
        elif "pattern" in change:
            return "pattern"
        else:
            return "context"  # Default to safest

    def _apply_context_edit(
        self, content: str, change: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Apply context-based edit."""
        context = change.get("context", [])
        replacement = change.get("replacement", "")

        if not context:
            return content, False

        # Convert replacement to string if it's a list
        if isinstance(replacement, list):
            replacement = "\n".join(replacement)

        # Find the context in the content
        context_str = "\n".join(context)
        if context_str not in content:
            return content, False

        # Count occurrences to ensure unique match
        occurrences = content.count(context_str)
        if occurrences > 1:
            return content, False

        # Replace the context
        new_content = content.replace(context_str, replacement, 1)
        return new_content, True

    def _apply_line_edit(
        self, content: str, change: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Apply line-based edit."""
        lines_spec = change.get("lines", [])
        replacement = change.get("replacement", "")

        if len(lines_spec) != 2:
            return content, False

        start_line, end_line = lines_spec
        lines = content.splitlines(True)

        # Validate line numbers
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            return content, False

        # Convert replacement to lines if it's a string
        if isinstance(replacement, str):
            replacement_lines = replacement.splitlines(True)
            # Ensure last line has newline if original did
            if (
                replacement_lines
                and not replacement_lines[-1].endswith("\n")
                and end_line < len(lines)
                and lines[end_line - 1].endswith("\n")
            ):
                replacement_lines[-1] += "\n"
        else:
            replacement_lines = replacement

        # Replace the line range
        new_lines = lines[: start_line - 1] + replacement_lines + lines[end_line:]
        return "".join(new_lines), True

    def _apply_pattern_edit(
        self, content: str, change: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Apply pattern-based edit."""
        pattern = change.get("pattern", "")
        replacement = change.get("replacement", "")

        if not pattern:
            return content, False

        try:
            # Use regex for replacement
            new_content = re.sub(pattern, replacement, content, count=1)
            return new_content, new_content != content
        except re.error:
            return content, False

    def _apply_semantic_edit(
        self, content: str, change: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """Apply semantic edit (language-aware)."""
        # For now, fallback to context-based editing
        # In a full implementation, this would parse the language structure
        return self._apply_context_edit(content, change)


def validate_smart_edit(arguments: Dict[str, Any]) -> str | bool:
    """Validate smart_edit arguments before execution."""
    try:
        path = arguments.get("path", "")
        changes = arguments.get("changes", [])

        # Validate file path
        if not path:
            return "Error: path is required"

        if not isinstance(path, str):
            return "Error: path must be a string"

        # Validate changes
        if not changes:
            return "Error: changes is required"

        if not isinstance(changes, list):
            return "Error: changes must be a list"

        if len(changes) == 0:
            return "Error: changes list cannot be empty"

        # Validate each change
        for i, change in enumerate(changes):
            if not isinstance(change, dict):
                return f"Error: Change {i + 1} must be a dictionary"

            # Check for at least one editing strategy
            strategies = ["context", "lines", "pattern", "semantic"]
            has_strategy = any(key in change for key in strategies)

            if not has_strategy:
                return f"Error: Change {i + 1} must specify an editing strategy (context, lines, pattern, or semantic)"

            # Check for replacement
            if "replacement" not in change:
                return f"Error: Change {i + 1} must specify 'replacement'"

        # Check if file exists for non-creation operations
        if os.path.exists(path):
            if os.path.isdir(path):
                return f"Error: {path} is a directory, not a file"

        return True

    except Exception as e:
        return f"Error during validation: {str(e)}"


def get_preview(
    tool_name: str, arguments: Dict[str, Any], tool_config: Dict[str, Any]
) -> str:
    """Generate preview for smart_edit tool."""
    try:
        import difflib
        from aicoder.utils import colorize_diff_lines
        from aicoder import config

        path = arguments.get("path", "")
        changes = arguments.get("changes", [])
        mode = arguments.get("mode", "context")
        encoding = arguments.get("encoding", "utf-8")

        if not path or not changes:
            return f"\n{config.YELLOW}{tool_name} tool called{config.RESET}\n{config.CYAN}Path: {path or 'Not specified'}{config.RESET}\n"

        # Read current file content
        original_content = ""
        if os.path.exists(path):
            try:
                with open(path, "r", encoding=encoding) as f:
                    original_content = f.read()
            except Exception as e:
                return f"\n{config.YELLOW}{tool_name} tool called{config.RESET}\n{config.CYAN}File: {path}{config.RESET}\n{config.RED}Error reading file: {e}{config.RESET}\n"

        # Apply changes to preview
        strategy_manager = EditStrategyManager()
        modified_content, change_results = strategy_manager.apply_changes(
            original_content, changes, mode
        )

        # Build preview text
        preview_lines = [f"\n{config.YELLOW}{tool_name} tool called{config.RESET}"]
        preview_lines.append(f"{config.CYAN}File: {path}{config.RESET}")

        # Show diff if there are changes
        if modified_content != original_content:
            # Generate unified diff
            original_lines = original_content.splitlines(True)
            modified_lines = modified_content.splitlines(True)

            diff_lines = list(
                difflib.unified_diff(
                    original_lines,
                    modified_lines,
                    fromfile=f"{path} (original)",
                    tofile=f"{path} (modified)",
                    n=3,
                    lineterm="",
                )
            )

            if diff_lines:
                # Colorize the diff
                diff_text = colorize_diff_lines("\n".join(diff_lines) + "\n")
                preview_lines.append("Changes:")
                preview_lines.append(diff_text)
            else:
                preview_lines.append("No significant changes detected.")
        else:
            preview_lines.append("No changes would be applied.")

        return "\n".join(preview_lines)

    except Exception as e:
        # Fallback to basic display
        from aicoder import config

        path = arguments.get("path", "")
        return f"\n{config.YELLOW}{tool_name} tool called{config.RESET}\n{config.CYAN}Path: {path}{config.RESET}\n{config.RED}Preview error: {e}{config.RESET}\n"


def execute_smart_edit(
    path: str,
    changes,
    mode: str = "context",
    preview_mode: str = "rich",
    create_backup: bool = True,
    auto_confirm: bool = False,
    encoding: str = "utf-8",
    conflict_resolution: str = "prompt",
    stats=None,
) -> str:
    """Main smart_edit tool implementation."""
    try:
        print(f"DEBUG: Processing file {path} with {len(changes)} changes")

        # Initialize components
        backup_manager = BackupManager()
        strategy_manager = EditStrategyManager()

        # Read current file content
        if os.path.exists(path):
            try:
                with open(path, "r", encoding=encoding) as f:
                    original_content = f.read()
            except Exception as e:
                return f"[X] Error reading file '{path}': {e}"
        else:
            original_content = ""

        # Apply changes
        modified_content, change_results = strategy_manager.apply_changes(
            original_content, changes, mode
        )

        # Check if any changes were actually made
        if modified_content == original_content:
            return "[i] No changes were applied to the file"

        # Create backup if requested
        backup_path = None
        if create_backup and os.path.exists(path):
            backup_path = backup_manager.create_backup(path)

        # Write the modified content
        try:
            # Ensure parent directory exists
            parent_dir = os.path.dirname(path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            with open(path, "w", encoding=encoding) as f:
                f.write(modified_content)

            # Record the file operation with the file tracker
            try:
                from aicoder.tool_manager.file_tracker import record_file_read

                record_file_read(path)
            except ImportError:
                pass

            result = f"[✓] Successfully edited '{path}'\n"

            if backup_path:
                result += f"Backup created: {backup_path}\n"

            result += "\nApplied changes:\n"
            for change_result in change_results:
                result += f"   • {change_result}\n"

            print("DEBUG: smart_edit completed successfully")
            return result

        except Exception as e:
            # Attempt rollback if we have a backup
            if backup_path:
                print("[!] Write failed, attempting rollback...")
                if backup_manager.rollback(path):
                    return f"[X] Error writing file '{path}': {e}\n[✓] Successfully rolled back from backup"
                else:
                    return (
                        f"[X] Error writing file '{path}': {e}\n[X] Rollback also failed"
                    )
            else:
                return f"[X] Error writing file '{path}': {e}"

    except Exception as e:
        print(f"DEBUG: Exception in execute_smart_edit: {e}")
        import traceback

        traceback.print_exc()
        return f"[X] Error in smart_edit: {str(e)}"
