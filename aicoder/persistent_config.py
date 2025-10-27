"""
Simple persistent configuration for AI Coder.

A basic dict that loads from and saves to .aicoder/settings-local.json
"""

import json
from pathlib import Path
from .utils import emsg


class PersistentConfig(dict):
    """Simple dict that automatically loads from and saves to JSON file."""

    def __init__(self, project_dir=None):
        """
        Initialize persistent config.

        Args:
            project_dir: Project directory. If None, uses current working directory.
        """
        super().__init__()
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.config_file = self.project_dir / ".aicoder" / "settings-local.json"
        self._read_only = False
        self.load()

    def load(self):
        """Load config from JSON file."""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(exist_ok=True)
        except OSError as e:
            # Read-only filesystem, continue with in-memory config
            emsg(f"Warning: Could not create history directory: {e}")
            self._read_only = True
            self.clear()
            return

        # Load if file exists
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.clear()
                    self.update(data)
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, start fresh
                self.clear()
        else:
            self.clear()

    def save(self):
        """Save config to JSON file."""
        if self._read_only:
            # Silently skip save operations in read-only mode
            return
            
        try:
            self.config_file.parent.mkdir(exist_ok=True)
        except Exception:
            # Can't create directory, mark as read-only and return early
            self._read_only = True
            return
            
        try:
            with open(self.config_file, "w") as f:
                json.dump(dict(self), f, indent=2)
        except (IOError, TypeError):
            # Silently fail on other save errors
            pass

    def __setitem__(self, key, value):
        """Override to save after any change."""
        super().__setitem__(key, value)
        self.save()

    def update(self, *args, **kwargs):
        """Override to save after update."""
        super().update(*args, **kwargs)
        self.save()

    def clear(self):
        """Override to save after clear."""
        super().clear()
        self.save()