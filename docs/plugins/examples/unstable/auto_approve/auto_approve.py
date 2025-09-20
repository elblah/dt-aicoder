"""
Auto-Approve Plugin Example

This plugin automatically approves certain safe operations.
"""

from aicoder.tool_manager.approval_system import ApprovalSystem

# Store original method
_original_request_approval = ApprovalSystem.request_user_approval


def smart_approval(self, prompt_message, tool_name, arguments, tool_config):
    """Auto-approve safe operations."""

    # Auto-approve read-only file operations
    safe_tools = ["read_file", "list_directory", "pwd", "glob"]
    if tool_name in safe_tools:
        print(f"🤖 Auto-approving safe tool: {tool_name}")
        return (True, False)  # (approved, no_guidance)

    # Auto-approve operations in trusted directories
    trusted_paths = ["/tmp", "/home/user/temp"]
    if tool_name in ["write_file", "edit_file"]:
        path = arguments.get("path", "")
        if any(path.startswith(trusted) for trusted in trusted_paths):
            print(f"🤖 Auto-approving trusted path operation: {path}")
            return (True, False)

    # Use original approval for everything else
    return _original_request_approval(
        self, prompt_message, tool_name, arguments, tool_config
    )


# Monkey patch
ApprovalSystem.request_user_approval = smart_approval

print("✅ Auto-approve plugin loaded - safe operations will be auto-approved")
