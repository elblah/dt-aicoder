"""
Test to simulate the actual user experience with /config command.
"""

import os
import tempfile
import json
import unittest
from unittest.mock import patch
from pathlib import Path
from io import StringIO

from aicoder.app import AICoder
from aicoder.commands.settings_command import SettingsCommand


class TestUserConfigExperience(unittest.TestCase):
    """Test cases simulating actual user experience."""

    def test_config_command_simulation(self):
        """Simulate the exact user experience of running /config set truncation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            os.chdir(temp_dir)

            try:
                print(f"Working in directory: {temp_dir}")

                # Create app as user would
                app = AICoder()

                # Verify no initial config exists
                config_file = Path(temp_dir) / ".aicoder" / "settings-local.json"
                print(f"Initial config file exists: {config_file.exists()}")
                if config_file.exists():
                    with open(config_file, "r") as f:
                        content = json.load(f)
                        print(f"Initial config content: {content}")

                # Create settings command
                command = SettingsCommand(app)

                # Simulate the user running: /config set truncation 9999999
                print("\n=== Running: /config set truncation 9999999 ===")
                
                # Capture stdout to see any messages
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    command.execute(["truncation", "9999999"])

                stdout_output = mock_stdout.getvalue()
                print(f"Command output: {stdout_output.strip()}")

                # Check in-memory state
                print(f"\nIn-memory truncation value: {app.persistent_config.get('truncation')}")

                # Check file state
                print(f"Config file exists: {config_file.exists()}")
                if config_file.exists():
                    with open(config_file, "r") as f:
                        content = json.load(f)
                        print(f"Config file content: {content}")

                # Now check if truncation is working by getting effective limit
                from aicoder import config
                config.set_app_instance(app)
                effective_limit = config.get_effective_truncation_limit()
                print(f"Effective truncation limit: {effective_limit}")

                # Simulate user restarting app (creating new instance)
                print("\n=== Creating new app instance ===")
                app2 = AICoder()
                
                config.set_app_instance(app2)
                effective_limit_after_restart = config.get_effective_truncation_limit()
                print(f"Effective truncation limit after restart: {effective_limit_after_restart}")

                self.assertEqual(effective_limit, 9999999)
                self.assertEqual(effective_limit_after_restart, 9999999)

            finally:
                os.chdir(original_cwd)

    def test_config_directory_creation_failure(self):
        """Test what happens when .aicoder directory can't be created."""
        # Mock the mkdir to fail
        with patch('pathlib.Path.mkdir', side_effect=OSError("Permission denied")):
            with tempfile.TemporaryDirectory() as temp_dir:
                original_cwd = os.getcwd()
                os.chdir(temp_dir)

                try:
                    app = AICoder()
                    
                    # Try to set a value
                    app.persistent_config["test"] = "value"
                    
                    # Should not crash, just work in memory
                    print(f"Config in memory despite mkdir failure: {app.persistent_config.get('test')}")

                finally:
                    os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()