"""
Model command for AI Coder.
"""

from typing import Tuple, List
from .base import BaseCommand
from .. import config
from ..utils import imsg


class ModelCommand(BaseCommand):
    """Gets or sets the API model."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/model"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Gets the current API model."""
        imsg(f"\n *** Model: {config.get_api_model()}")
        return False, False
