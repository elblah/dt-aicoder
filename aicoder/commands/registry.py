"""
Command registry for AI Coder.
"""

from typing import Dict, Callable
from .help_command import HelpCommand
from .edit_command import EditCommand

from .quit_command import QuitCommand
from .pprint_messages_command import PprintMessagesCommand
from .compact_command import CompactCommand
from .model_command import ModelCommand
from .new_session_command import NewSessionCommand
from .save_session_command import SaveSessionCommand
from .load_session_command import LoadSessionCommand
from .breakpoint_command import BreakpointCommand
from .stats_command import StatsCommand
from .prompt_command import PromptCommand
from .retry_command import RetryCommand
from .debug_command import DebugCommand
from .revoke_approvals_command import RevokeApprovalsCommand
from .yolo_command import YoloCommand
from .plan_command import PlanCommand
from .reset_command import ResetCommand
from .settings_command import SettingsCommand


class CommandRegistry:
    """Registry for all commands."""

    def __init__(self, app_instance=None):
        self.app_instance = app_instance
        self.commands = {}

        # Register all commands
        self._register_commands()

    def _register_commands(self):
        """Register all available commands."""
        command_classes = [
            HelpCommand,
            EditCommand,
            QuitCommand,
            PprintMessagesCommand,
            CompactCommand,
            ModelCommand,
            NewSessionCommand,
            SaveSessionCommand,
            LoadSessionCommand,
            BreakpointCommand,
            StatsCommand,
            PromptCommand,
            RetryCommand,
            DebugCommand,
            RevokeApprovalsCommand,
            YoloCommand,
            PlanCommand,
            ResetCommand,
            SettingsCommand,
        ]

        for cmd_class in command_classes:
            cmd_instance = cmd_class(self.app_instance)
            for alias, handler in cmd_instance.register().items():
                self.commands[alias] = handler

    def get_all_commands(self) -> Dict[str, Callable]:
        """Get all registered commands."""
        return self.commands
