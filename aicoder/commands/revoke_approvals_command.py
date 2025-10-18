"""
Revoke approvals command for AI Coder.
"""

from typing import Tuple, List
from .base import BaseCommand


class RevokeApprovalsCommand(BaseCommand):
    """Revokes all session approvals and clears the approval cache."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/revoke_approvals", "/ra"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Revokes all session approvals and clears the approval cache."""
        self.app.tool_manager.approval_system.revoke_approvals()
        return False, False
