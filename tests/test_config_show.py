"""
Test the improved /config show functionality.
"""

import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from io import StringIO

from aicoder.app import AICoder
from aicoder.commands.settings_command import SettingsCommand
from aicoder import config


class TestConfigShow(unittest.TestCase):
    """Test cases for improved config show functionality."""

    def setUp(self):
        """Set up test environment."""
        # Save original working directory
        self.original_cwd = os.getcwd()
        
        # Clear global app instance to avoid test pollution
        config.set_app_instance(None)

    def tearDown(self):
        """Clean up test environment."""
        # Restore original working directory
        os.chdir(self.original_cwd)
        
        # Clear global app instance to avoid test pollution
        config.set_app_instance(None)

    def test_show_truncation_with_setting(self):
        """Test showing truncation when it's set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            app = AICoder()
            app.persistent_config["truncation"] = 750

            command = SettingsCommand(app)

            # Capture stdout to see output
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                command.execute(["truncation"])

            output = mock_stdout.getvalue()

            # Should show the value and effective limit
            self.assertIn("truncation: 750", output)
            self.assertIn("[EFFECTIVE]", output)

    def test_show_truncation_not_set(self):
        """Test showing truncation when it's not set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            app = AICoder()
            command = SettingsCommand(app)

            # Capture stdout to see output
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                command.execute(["truncation"])

            output = mock_stdout.getvalue()

            # Should show it's not set and give tip
            self.assertIn("[NOT SET]", output)
            self.assertIn("[TIP]", output)


if __name__ == "__main__":
    unittest.main()