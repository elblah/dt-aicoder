"""
Test to debug persistent config persistence issue.
"""

import os
import tempfile
import json
import unittest
from pathlib import Path

from aicoder.app import AICoder
from aicoder.commands.settings_command import SettingsCommand


class TestConfigPersistence(unittest.TestCase):
    """Test cases for config persistence debugging."""

    def test_persistent_config_saves_to_disk(self):
        """Test that persistent config actually saves to disk."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            os.chdir(temp_dir)

            try:
                # Create app
                app = AICoder()

                # Verify config file path
                config_file = Path(temp_dir) / ".aicoder" / "settings-local.json"
                print(f"Config file should be at: {config_file}")
                print(f"Directory exists: {config_file.parent.exists()}")
                print(f"File exists: {config_file.exists()}")

                # Set a value
                app.persistent_config["truncation"] = 9999999

                # Check if file was created
                print(f"After setting, file exists: {config_file.exists()}")

                if config_file.exists():
                    with open(config_file, "r") as f:
                        content = json.load(f)
                        print(f"File content: {content}")

                # Create new app instance and check if setting persists
                app2 = AICoder()
                print(f"New app truncation value: {app2.persistent_config.get('truncation', 'NOT_FOUND')}")

            finally:
                os.chdir(original_cwd)

    def test_settings_command_direct(self):
        """Test settings command directly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            os.chdir(temp_dir)

            try:
                # Create app
                app = AICoder()

                # Create settings command
                command = SettingsCommand(app)

                # Execute set command
                command._set_setting("truncation", "9999999")

                # Check if it's in memory
                print(f"In memory: {app.persistent_config.get('truncation')}")

                # Check if file was created
                config_file = Path(temp_dir) / ".aicoder" / "settings-local.json"
                print(f"File exists: {config_file.exists()}")

                if config_file.exists():
                    with open(config_file, "r") as f:
                        content = json.load(f)
                        print(f"File content: {content}")

            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()