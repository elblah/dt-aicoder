"""
Internal tools package for AI Coder.
"""

from .write_file import execute_write_file
from .read_file import execute_read_file
from .list_directory import execute_list_directory
from .run_shell_command import execute_run_shell_command
from .grep import execute_grep

from .edit_file import execute_edit_file
# Map tool names to their execution functions
INTERNAL_TOOL_FUNCTIONS = {
    "write_file": execute_write_file,
    "read_file": execute_read_file,
    "list_directory": execute_list_directory,
    "run_shell_command": execute_run_shell_command,
    "grep": execute_grep,

    "edit_file": execute_edit_file,
}