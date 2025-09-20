"""
Custom Command Plugin Example

This plugin adds a new '/plugins' command to list loaded plugins.
"""

from aicoder.command_handlers import CommandHandler


def list_plugins_command(self, args):
    """List all loaded plugins."""
    if hasattr(self, "loaded_plugins") and self.loaded_plugins:
        return f"Loaded plugins: {', '.join(self.loaded_plugins)}"
    else:
        return "No plugins loaded"


# Add the new command
CommandHandler.plugins = list_plugins_command

print("✅ Custom command plugin loaded - use '/plugins' to list loaded plugins")
