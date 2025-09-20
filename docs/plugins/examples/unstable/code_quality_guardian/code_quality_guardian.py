"""
Code Quality Guardian Plugin

This plugin automatically monitors code quality by running linters and formatters
on files that are modified during AI-assisted development. It provides real-time
feedback on code quality issues and can automatically fix formatting issues.

Features:
- Automatic code quality checks on file modifications
- Integration with popular tools (ruff, black, pylint, etc.)
- Automatic formatting fixes
- Quality score tracking
- Customizable rules and thresholds
"""

import json
import subprocess
import threading
from pathlib import Path
from aicoder.tool_manager.internal_tools import write_file
from aicoder.tool_manager.internal_tools import INTERNAL_TOOL_FUNCTIONS
from aicoder.tool_manager.internal_tools import INTERNAL_TOOL_DEFINITIONS
from aicoder.command_handlers import CommandHandler

# Configuration
QUALITY_CONFIG = {
    "enabled": True,
    "auto_format": True,  # Automatically format code
    "show_issues": True,  # Show linting issues
    "tools": {
        "python": {
            "linter": "ruff check",
            "formatter": "ruff format",
            "security": "bandit -r",
        }
    },
    "severity_threshold": "warning",  # info, warning, error
    "auto_fix_formatting": True,  # Automatically fix formatting issues
}


class CodeQualityGuardian:
    def __init__(self):
        self.quality_scores = {}
        self.issues_history = []
        self.watched_files = set()

    def check_file_quality(self, file_path):
        """Check the quality of a file and return issues."""
        if not QUALITY_CONFIG["enabled"]:
            return []

        try:
            file_ext = Path(file_path).suffix.lower()
            issues = []

            # Python files
            if file_ext == ".py":
                issues = self._check_python_quality(file_path)

            # Track issues
            if issues:
                self.issues_history.extend(issues)
                # Keep only recent issues (last 100)
                self.issues_history = self.issues_history[-100:]

            return issues

        except Exception as e:
            print(f"⚠️ Quality check failed for {file_path}: {e}")
            return []

    def _check_python_quality(self, file_path):
        """Check Python file quality using configured tools."""
        issues = []

        try:
            # Run ruff check for linting
            if "ruff" in QUALITY_CONFIG["tools"]["python"]["linter"]:
                result = subprocess.run(
                    ["ruff", "check", file_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0 and result.stdout:
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        if line.strip():
                            issues.append(
                                {
                                    "file": file_path,
                                    "tool": "ruff",
                                    "issue": line.strip(),
                                    "severity": "warning" if "W" in line else "error",
                                }
                            )

            # Run security check with bandit
            try:
                result = subprocess.run(
                    ["bandit", "-r", file_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0 and result.stdout:
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        if "Issue:" in line or "Severity:" in line:
                            issues.append(
                                {
                                    "file": file_path,
                                    "tool": "bandit",
                                    "issue": line.strip(),
                                    "severity": "warning",
                                }
                            )
            except FileNotFoundError:
                # Bandit not installed, skip
                pass

        except subprocess.TimeoutExpired:
            issues.append(
                {
                    "file": file_path,
                    "tool": "timeout",
                    "issue": "Quality check timed out",
                    "severity": "warning",
                }
            )
        except Exception as e:
            issues.append(
                {
                    "file": file_path,
                    "tool": "error",
                    "issue": f"Quality check failed: {str(e)}",
                    "severity": "warning",
                }
            )

        return issues

    def format_file(self, file_path):
        """Automatically format a file."""
        if not QUALITY_CONFIG["auto_format"]:
            return False

        try:
            file_ext = Path(file_path).suffix.lower()

            # Python files
            if file_ext == ".py":
                # Run ruff format
                result = subprocess.run(
                    ["ruff", "format", file_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                return result.returncode == 0

        except Exception as e:
            print(f"⚠️ Auto-format failed for {file_path}: {e}")
            return False

    def get_quality_score(self, file_path):
        """Calculate a quality score for a file (0-100)."""
        # Simple scoring based on recent issues
        recent_issues = [
            issue for issue in self.issues_history[-50:] if issue["file"] == file_path
        ]

        if not recent_issues:
            return 100

        # Count issues by severity
        error_count = sum(1 for issue in recent_issues if issue["severity"] == "error")
        warning_count = sum(
            1 for issue in recent_issues if issue["severity"] == "warning"
        )

        # Calculate score (simple formula)
        score = max(0, 100 - (error_count * 10) - (warning_count * 5))
        return score


# Global quality guardian instance
quality_guardian = CodeQualityGuardian()

# Store original function
_original_write_file = write_file


def quality_monitored_write_file(path, content, **kwargs):
    """Write file with quality monitoring."""

    # Call original function
    result = _original_write_file(path, content, **kwargs)

    # Check quality after writing
    if QUALITY_CONFIG["enabled"]:
        # Run quality checks in background to avoid blocking
        def check_quality():
            issues = quality_guardian.check_file_quality(path)
            if issues and QUALITY_CONFIG["show_issues"]:
                print(f"\n🔍 Code Quality Issues in {path}:")
                for issue in issues[:5]:  # Show first 5 issues
                    print(f"   ⚠️ {issue['tool']}: {issue['issue']}")
                if len(issues) > 5:
                    print(f"   ... and {len(issues) - 5} more issues")

            # Auto-format if enabled
            if QUALITY_CONFIG["auto_fix_formatting"]:
                formatted = quality_guardian.format_file(path)
                if formatted:
                    print(f"   ✨ Auto-formatted {path}")

        # Run in background thread
        thread = threading.Thread(target=check_quality, daemon=True)
        thread.start()

    return result


# Monkey patch
INTERNAL_TOOL_FUNCTIONS["write_file"] = quality_monitored_write_file


# Add quality check tool
def quality_check_tool(file_path: str) -> str:
    """Check the quality of a file."""
    try:
        issues = quality_guardian.check_file_quality(file_path)
        score = quality_guardian.get_quality_score(file_path)

        if not issues:
            return f"✅ {file_path} - Quality score: {score}/100 - No issues found"

        result = [f"📊 {file_path} - Quality score: {score}/100"]
        result.append(f"⚠️ {len(issues)} issues found:")

        for issue in issues[:10]:  # Show first 10 issues
            result.append(f"   - {issue['tool']}: {issue['issue']}")

        if len(issues) > 10:
            result.append(f"   ... and {len(issues) - 10} more issues")

        return "\n".join(result)

    except Exception as e:
        return f"❌ Quality check failed: {str(e)}"


# Register the quality check tool
quality_check_spec = {
    "type": "function",
    "function": {
        "name": "quality_check",
        "description": "Check the code quality of a file using linters and formatters",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to check",
                }
            },
            "required": ["file_path"],
        },
    },
}

INTERNAL_TOOL_DEFINITIONS["quality_check"] = quality_check_spec
INTERNAL_TOOL_FUNCTIONS["quality_check"] = quality_check_tool


# Add commands
def quality_command(self, args):
    """Display code quality information."""
    if not args or args.strip().lower() == "status":
        # Show overall quality status
        if not quality_guardian.issues_history:
            return "✅ No quality issues detected"

        total_issues = len(quality_guardian.issues_history)
        files_with_issues = len(
            set(issue["file"] for issue in quality_guardian.issues_history)
        )

        result = [
            "=== Code Quality Status ===",
            f"Total issues: {total_issues}",
            f"Files with issues: {files_with_issues}",
            "",
            "Recent issues:",
        ]

        # Show recent issues
        for issue in quality_guardian.issues_history[-10:]:
            result.append(f"  {issue['file']} - {issue['tool']}: {issue['issue']}")

        return "\n".join(result)

    elif args.strip().lower() == "config":
        # Show configuration
        return f"Code Quality Guardian Configuration:\n{json.dumps(QUALITY_CONFIG, indent=2)}"

    else:
        return "Usage: /quality [status|config]"


def format_command(self, args):
    """Format a file or all files."""
    if not args:
        return "Usage: /format <file_path> or /format all"

    target = args.strip()

    if target == "all":
        # Format all Python files in current directory
        formatted_count = 0
        for py_file in Path(".").rglob("*.py"):
            if quality_guardian.format_file(str(py_file)):
                formatted_count += 1
        return f"✅ Formatted {formatted_count} Python files"

    else:
        # Format specific file
        if quality_guardian.format_file(target):
            return f"✅ Formatted {target}"
        else:
            return f"❌ Failed to format {target}"


# Add the commands
CommandHandler.quality = quality_command
CommandHandler.format = format_command

print("✅ Code Quality Guardian plugin loaded")
print("   - Automatic code quality checks enabled")
print("   - Auto-formatting enabled")
print("   - Use '/quality' to view quality status")
print("   - Use '/format <file>' to format a file")
print("   - AI can call 'quality_check' tool to analyze files")
