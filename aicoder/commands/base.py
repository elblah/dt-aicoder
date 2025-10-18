"""
Base command class for AI Coder commands.
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Callable


class BaseCommand(ABC):
    """Base class for all commands."""

    def __init__(self, app_instance=None):
        self.app = app_instance
        # Each command should register its own aliases
        self.aliases = []

    @abstractmethod
    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """
        Execute the command.

        Returns:
            Tuple[bool, bool]: (should_quit, run_api_call)
        """
        pass

    @property
    def name(self) -> str:
        """Get the primary command name."""
        return self.aliases[0] if self.aliases else "unknown"

    def register(self) -> Dict[str, Callable]:
        """Register the command aliases and return the mapping."""
        return {alias: self.execute for alias in self.aliases}
