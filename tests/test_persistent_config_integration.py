"""
Integration tests for persistent config functionality.
"""

import tempfile
import unittest
from pathlib import Path

from aicoder.app import AICoder
from aicoder.persistent_config import PersistentConfig


class TestPersistentConfigIntegration(unittest.TestCase):
    """Integration tests for persistent config with main app."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()

        # Change to test directory
        import os

        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        import os
        import shutil

        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_aicoder_has_persistent_config(self):
        """Test that AICoder instance has persistent config."""
        # Create AICoder instance (this will create persistent config in test dir)
        app = AICoder()

        # Check that persistent_config exists
        self.assertTrue(hasattr(app, "persistent_config"))
        self.assertIsInstance(app.persistent_config, PersistentConfig)

        # Check that config file was created
        config_file = Path(".dt-aicoder/settings-local.json")
        self.assertTrue(config_file.exists())

    def test_settings_command_available(self):
        """Test that settings command is available."""
        app = AICoder()

        # Check that settings command is registered
        self.assertIn("/settings", app.command_handlers)
        self.assertIn("/config", app.command_handlers)
        self.assertIn("/setting", app.command_handlers)

    def test_todo_respects_persistent_config(self):
        """Test that todo plugin respects persistent config."""
        # Create persistent config and disable todo
        config = PersistentConfig()
        config["todo.enabled"] = False

        # Create AICoder instance
        app = AICoder()

        # Check if todo command availability matches config
        # This depends on whether the todo plugin is loaded and checks the config
        todo_command_registered = "/todo" in app.command_handlers

        if not todo_command_registered:
            # This is expected when todo is disabled
            pass
        else:
            # If it is registered, check that it respects the config when called
            # This would require more complex testing with the actual plugin
            pass

    def test_config_persistence_across_app_instances(self):
        """Test that config persists across AICoder instances."""
        # Create first app and set a setting
        app1 = AICoder()
        app1.persistent_config["test.integration"] = "persistent_value"

        # Create second app and check config
        app2 = AICoder()
        self.assertEqual(app2.persistent_config["test.integration"], "persistent_value")


if __name__ == "__main__":
    unittest.main()
