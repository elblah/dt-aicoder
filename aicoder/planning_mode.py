"""
Planning Mode module for AI Coder.

This module provides plan mode functionality that allows users to switch between
planning (read-only) and building (read-write) modes, similar to opencode's approach.
"""

import os
from typing import Optional
from . import config


PLAN_MODE_CONTENT = """<system-reminder>
PLANNING MODE ACTIVE - Read-Only Operations Only

CRITICAL: You are currently in PLANNING MODE with restricted access:
ALLOWED: Read files, list directories, search content, analyze code
FORBIDDEN: File edits, modifications, system changes, write operations

IMPORTANT RESTRICTIONS:
- DO NOT use bash commands like: sed, tee, echo, cat with redirection (>), cp, mv, rm, chmod, mkdir, touch
- DO NOT use run_shell_command with arguments that modify files or system
- ONLY use bash commands for: reading (cat, grep, find), checking status, analysis

**FORBIDDEN**: ANY operation that could:
- Modify file content or metadata
- Change system state
- Delete, move, or alter files
- Execute potentially destructive code

You may observe, analyze, plan, and prepare for future execution.

**The use of any tool or shell command that could change the system in any way is STRICTLY FORBIDDEN**
</system-reminder>"""

BUILD_SWITCH_CONTENT = """<system-reminder>
BUILD MODE ACTIVE - Full Tool Access Unlocked

You are now in BUILD MODE with complete access to all tools:
AVAILABLE: File edits, write operations, command execution, system modifications
AVAILABLE: Read operations, analysis, planning (same as planning mode)

All AI Coder tools are now available for execution.
</system-reminder>"""


class PlanningMode:
    """Manages planning mode state and functionality."""

    def __init__(self):
        self._plan_mode_active = False
        self._was_plan_mode_last = False

    def is_plan_mode_active(self) -> bool:
        """Check if planning mode is currently active."""
        return self._plan_mode_active

    def set_plan_mode(self, active: bool) -> None:
        """Set planning mode state."""
        # Only change _was_plan_mode_last if we're actually switching modes
        if self._plan_mode_active != active:
            self._was_plan_mode_last = self._plan_mode_active
        self._plan_mode_active = active

    def toggle_plan_mode(self) -> bool:
        """Toggle planning mode and return new state."""
        # Only change _was_plan_mode_last if we're actually switching modes
        self._was_plan_mode_last = self._plan_mode_active
        self._plan_mode_active = not self._plan_mode_active
        return self._plan_mode_active

    def was_plan_mode_last(self) -> bool:
        """Check if the last assistant message was in plan mode."""
        return self._was_plan_mode_last

    def get_mode_content(self) -> Optional[str]:
        """Get appropriate content to append based on current mode."""
        if self._plan_mode_active:
            return PLAN_MODE_CONTENT
        elif self._was_plan_mode_last and not self._plan_mode_active:
            # Just switched from plan to build mode
            self._was_plan_mode_last = False
            return BUILD_SWITCH_CONTENT
        return None

    def get_writing_tools(self) -> list:
        """Get list of writing tools that should be disabled in plan mode."""
        return ["write_file", "edit_file", "create_backup"]

    def _get_tool_config(self, tool_name: str) -> dict:
        """Get tool configuration for the given tool name."""
        try:
            import os
            import json
            
            # Try to load from mcp_tools.json
            mcp_file = os.path.join(os.path.dirname(__file__), "..", "mcp_tools.json")
            if os.path.exists(mcp_file):
                with open(mcp_file, 'r') as f:
                    mcp_config = json.load(f)
                    for tool_config in mcp_config.get("tools", []):
                        if tool_config.get("name") == tool_name:
                            return tool_config
        except:
            pass
        
        return {}

    def get_active_tools(self, all_tools: list) -> list:
        """Get list of active tools for API requests based on current mode."""
        if not self._plan_mode_active:
            # When not in plan mode, all tools are active
            return [
                tool.get("function", {}).get("name") 
                for tool in all_tools
                if tool.get("function", {}).get("name")
            ]
        
        # When in plan mode, filter out writing tools
        writing_tools = set(self.get_writing_tools())
        return [
            tool.get("function", {}).get("name") 
            for tool in all_tools
            if (tool.get("function", {}).get("name") and 
                tool.get("function", {}).get("name") not in writing_tools)
        ]

    def should_disable_tool(self, tool_name: str) -> bool:
        """Check if a tool should be disabled in plan mode."""
        if not self._plan_mode_active:
            return False
            
        # Check hardcoded writing tools first (backward compatibility)
        if tool_name in self.get_writing_tools():
            return True
            
        # Check tool config for available_in_plan_mode flag
        tool_config = self._get_tool_config(tool_name)
        # Default to True (allow) unless explicitly marked as unavailable
        available_in_plan_mode = tool_config.get("available_in_plan_mode", True)
        
        return not available_in_plan_mode

    def get_prompt_prefix(self) -> str:
        """Get the appropriate prompt prefix based on mode."""
        if self._plan_mode_active:
            return f"{config.BOLD}{config.GREEN}\n[PLAN] >{config.RESET} "
        return f"{config.BOLD}{config.GREEN}\n>{config.RESET} "

    def get_status_text(self) -> str:
        """Get status text for the plan mode."""
        if self._plan_mode_active:
            return f"{config.YELLOW}Planning mode is ACTIVE (read-only){config.RESET}"
        else:
            return f"{config.GREEN}Planning mode is INACTIVE (read-write){config.RESET}"


# Global planning mode instance
_planning_mode = None


def get_planning_mode() -> PlanningMode:
    """Get the global planning mode instance."""
    global _planning_mode
    if _planning_mode is None:
        _planning_mode = PlanningMode()
    return _planning_mode
