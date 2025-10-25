"""
Tests for persistent configuration functionality.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from aicoder.persistent_config import PersistentConfig


class TestPersistentConfig(unittest.TestCase):
    """Test cases for PersistentConfig class."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.config_file = Path(self.test_dir) / ".aicoder" / "settings-local.json"

    def tearDown(self):
        """Clean up test environment."""
        # Remove test directory
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init_creates_config_directory(self):
        """Test that initialization creates config directory."""
        PersistentConfig(self.test_dir)
        self.assertTrue(self.config_file.parent.exists())

    def test_init_with_nonexistent_file(self):
        """Test initialization when config file doesn't exist."""
        config = PersistentConfig(self.test_dir)
        self.assertEqual(len(config), 0)
        # The config file should be created (but empty) when init is called
        # This ensures the directory structure is in place
        self.assertTrue(self.config_file.exists())

        # Verify file is empty (just contains empty dict {})
        with open(self.config_file, "r") as f:
            data = json.load(f)
            self.assertEqual(data, {})

    def test_save_and_load(self):
        """Test saving and loading config."""
        config = PersistentConfig(self.test_dir)

        # Set some values
        config["test.key"] = "test_value"
        config["todo.enabled"] = True
        config["some.number"] = 42

        # Verify file was created
        self.assertTrue(self.config_file.exists())

        # Load config in new instance
        config2 = PersistentConfig(self.test_dir)

        self.assertEqual(config2["test.key"], "test_value")
        self.assertEqual(config2["todo.enabled"], True)
        self.assertEqual(config2["some.number"], 42)

    def test_update_saves(self):
        """Test that update() method saves to file."""
        config = PersistentConfig(self.test_dir)

        # Update with dict
        config.update({"new.key": "new_value", "another.key": True})

        # Verify file was created and contains data
        self.assertTrue(self.config_file.exists())

        with open(self.config_file, "r") as f:
            data = json.load(f)

        self.assertEqual(data["new.key"], "new_value")
        self.assertEqual(data["another.key"], True)

    def test_clear(self):
        """Test clearing config."""
        config = PersistentConfig(self.test_dir)
        config["test.key"] = "test_value"

        # Clear and check file is updated
        config.clear()

        with open(self.config_file, "r") as f:
            data = json.load(f)

        self.assertEqual(data, {})

    def test_load_corrupted_file(self):
        """Test loading when config file is corrupted."""
        # Create corrupted JSON file
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            f.write("invalid json content")

        # Should load without error and be empty
        config = PersistentConfig(self.test_dir)
        self.assertEqual(len(config), 0)

    def test_dict_operations(self):
        """Test standard dict operations."""
        config = PersistentConfig(self.test_dir)

        # Test __contains__
        self.assertFalse("key" in config)

        # Test __setitem__ and __getitem__
        config["key"] = "value"
        self.assertTrue("key" in config)
        self.assertEqual(config["key"], "value")

        # Test get()
        self.assertEqual(config.get("key"), "value")
        self.assertEqual(config.get("nonexistent", "default"), "default")

        # Test keys(), values(), items()
        self.assertIn("key", list(config.keys()))
        self.assertIn("value", list(config.values()))
        self.assertIn(("key", "value"), list(config.items()))

    def test_nested_dict_values(self):
        """Test storing nested dictionaries."""
        config = PersistentConfig(self.test_dir)

        nested = {"level1": {"level2": "deep_value"}}
        config["nested"] = nested

        # Load in new instance
        config2 = PersistentConfig(self.test_dir)
        self.assertEqual(config2["nested"]["level1"]["level2"], "deep_value")

    def test_current_working_directory_default(self):
        """Test that default project directory is current working directory."""
        original_cwd = os.getcwd()

        try:
            # Change to test directory
            os.chdir(self.test_dir)

            # Create config without specifying directory
            config = PersistentConfig()

            # Should create in current directory
            expected_file = Path.cwd() / ".aicoder" / "settings-local.json"
            self.assertEqual(str(config.config_file), str(expected_file))

        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
