"""
Simple persistent configuration for AI Coder.

A basic dict that loads from and saves to .dt-aicoder/settings-local.json
"""

import json
import os
from pathlib import Path


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
        self.config_file = self.project_dir / ".dt-aicoder" / "settings-local.json"
        self.load()
    
    def load(self):
        """Load config from JSON file."""
        # Ensure directory exists
        self.config_file.parent.mkdir(exist_ok=True)
        
        # Load if file exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
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
        self.config_file.parent.mkdir(exist_ok=True)
        try:
            with open(self.config_file, 'w') as f:
                json.dump(dict(self), f, indent=2)
        except IOError:
            pass  # Silently fail on save errors
    
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