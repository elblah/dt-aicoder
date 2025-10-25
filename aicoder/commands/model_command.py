"""
Model command for AI Coder.
"""

import os
from typing import Tuple, List
from .base import BaseCommand
from .. import config
from ..utils import imsg, emsg


class ModelCommand(BaseCommand):
    """Gets or sets the API model."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/model"]

    def execute(self, args: List[str]) -> Tuple[bool, bool]:
        """Gets or sets the API model."""
        if not args:
            # No arguments - show current model
            current_model = config.get_api_model()
            imsg(f"\n *** Model: {current_model}")
            return False, False

        # Check if it's a set command
        if args[0].lower() == "set" and len(args) >= 2:
            model_name = args[1]
            # Set the model via environment variable
            # Check if we're in planning mode to set the appropriate env var
            try:
                from ..planning_mode import get_planning_mode

                if get_planning_mode().is_plan_mode_active():
                    # If in plan mode, set the planning mode model
                    os.environ["PLAN_OPENAI_MODEL"] = model_name
                    imsg(f"\n *** Planning mode model set to: {model_name}")
                else:
                    # Otherwise, set the regular model
                    os.environ["OPENAI_MODEL"] = model_name
                    imsg(f"\n *** Model set to: {model_name}")
            except (ImportError, RuntimeError):
                # If planning mode is not available, just set the regular model
                os.environ["OPENAI_MODEL"] = model_name
                imsg(f"\n *** Model set to: {model_name}")
            return False, False
        elif args[0].lower() == "set" and len(args) < 2:
            emsg("\n *** Error: Model name required. Usage: /model set <modelname>")
            return False, False
        elif len(args) == 1:
            # Just a model name provided without 'set' - set it
            model_name = args[0]
            # Check if we're in planning mode to set the appropriate env var
            try:
                from ..planning_mode import get_planning_mode

                if get_planning_mode().is_plan_mode_active():
                    # If in plan mode, set the planning mode model
                    os.environ["PLAN_OPENAI_MODEL"] = model_name
                    imsg(f"\n *** Planning mode model set to: {model_name}")
                else:
                    # Otherwise, set the regular model
                    os.environ["OPENAI_MODEL"] = model_name
                    imsg(f"\n *** Model set to: {model_name}")
            except (ImportError, RuntimeError):
                # If planning mode is not available, just set the regular model
                os.environ["OPENAI_MODEL"] = model_name
                imsg(f"\n *** Model set to: {model_name}")
            return False, False
        else:
            emsg(
                "\n *** Error: Invalid arguments. Usage: /model set <modelname> or just /model to show current"
            )
            return False, False
