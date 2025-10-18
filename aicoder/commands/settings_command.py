"""
Settings command for managing persistent configuration.
"""

from .base import BaseCommand
from ..utils import imsg, emsg, wmsg


class SettingsCommand(BaseCommand):
    """Command to manage persistent settings."""

    def __init__(self, app_instance=None):
        super().__init__(app_instance)
        self.aliases = ["/settings", "/setting", "/config"]

    def execute(self, args):
        """Execute the settings command."""
        if not args:
            self._show_all_settings()
            return False, False
        
        if len(args) == 1:
            if args[0] in ["show", "list", "ls"]:
                self._show_all_settings()
            elif args[0] in ["help", "-h", "--help"]:
                self._show_help()
            else:
                # Show specific setting
                self._show_setting(args[0])
        elif len(args) >= 2:
            # Set setting: /settings key value [more values...]
            key = args[0]
            value = " ".join(args[1:])
            self._set_setting(key, value)
        else:
            self._show_help()
        
        return False, False

    def _show_all_settings(self):
        """Show all current settings."""
        config = self.app.persistent_config
        
        if not config:
            imsg("No persistent settings configured.")
            return
        
        imsg("Current persistent settings:")
        for key, value in sorted(config.items()):
            imsg(f"  {key}: {value}")

    def _show_setting(self, key):
        """Show a specific setting."""
        config = self.app.persistent_config
        
        if key in config:
            imsg(f"{key}: {config[key]}")
        else:
            emsg(f"Setting '{key}' not found.")

    def _set_setting(self, key, value):
        """Set a setting value."""
        config = self.app.persistent_config
        
        # Convert string to appropriate type
        parsed_value = self._parse_value(value)
        
        old_value = config.get(key)
        config[key] = parsed_value
        
        if old_value is not None:
            wmsg(f"Updated {key}: {old_value} → {parsed_value}")
        else:
            imsg(f"Set {key}: {parsed_value}")

    def _parse_value(self, value):
        """Parse string value to appropriate Python type."""
        # Handle boolean values
        if value.lower() in ["true", "on", "yes", "1"]:
            return True
        elif value.lower() in ["false", "off", "no", "0"]:
            return False
        
        # Handle numeric values
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value

    def _show_help(self):
        """Show help for settings command."""
        imsg("Settings command usage:")
        imsg("  /settings                    - Show all settings")
        imsg("  /settings show               - Show all settings")
        imsg("  /settings <key>              - Show specific setting")
        imsg("  /settings <key> <value>      - Set a setting")
        imsg("")
        imsg("Examples:")
        imsg("  /settings todo.enabled true")
        imsg("  /settings todo.enabled false")
        imsg("  /settings ui.theme dark")
        imsg("")
        imsg("Common settings:")
        imsg("  todo.enabled - Enable/disable todo functionality")
        imsg("  ui.theme - UI theme name")
        imsg("  tools.auto_approve - Auto-approve tool execution")