"""
Tests for prompt history manager functionality.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aicoder.prompt_history_manager import PromptHistoryManager


class TestPromptHistoryManager(unittest.TestCase):
    """Test cases for PromptHistoryManager."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.history_file = self.test_dir / ".dt-aicoder" / "history"
        self.manager = PromptHistoryManager(project_dir=self.test_dir, max_history=5)

    def tearDown(self):
        """Clean up test environment."""
        # Clean up test files
        if self.history_file.exists():
            self.history_file.unlink()
        if self.history_file.parent.exists():
            self.history_file.parent.rmdir()

    def test_init_creates_directory(self):
        """Test that initialization creates the .dt-aicoder directory."""
        self.assertTrue(self.history_file.parent.exists())

    def test_save_prompt_creates_file(self):
        """Test that saving a prompt creates the history file."""
        self.manager.save_prompt("test prompt")
        self.assertTrue(self.history_file.exists())

    def test_save_and_load_single_prompt(self):
        """Test saving and loading a single prompt."""
        prompt = "Hello, world!"
        self.manager.save_prompt(prompt)

        loaded_prompts = self.manager.load_history()
        self.assertEqual(len(loaded_prompts), 1)
        self.assertEqual(loaded_prompts[0], prompt)

    def test_save_multiple_prompts(self):
        """Test saving and loading multiple prompts."""
        prompts = ["prompt1", "prompt2", "prompt3"]
        for prompt in prompts:
            self.manager.save_prompt(prompt)

        loaded_prompts = self.manager.load_history()
        self.assertEqual(len(loaded_prompts), 3)
        self.assertEqual(loaded_prompts, prompts)

    def test_max_history_limit(self):
        """Test that history respects the max_history limit."""
        # Save more prompts than the limit (max_history=5 from setUp)
        prompts = [f"prompt{i}" for i in range(10)]
        for prompt in prompts:
            self.manager.save_prompt(prompt)

        loaded_prompts = self.manager.load_history()
        self.assertEqual(len(loaded_prompts), 5)
        self.assertEqual(loaded_prompts, prompts[-5:])  # Should keep the last 5

    def test_empty_prompt_not_saved(self):
        """Test that empty prompts are not saved."""
        self.manager.save_prompt("")
        self.manager.save_prompt("   ")

        loaded_prompts = self.manager.load_history()
        self.assertEqual(len(loaded_prompts), 0)

    def test_duplicate_prompt_handling(self):
        """Test that duplicate prompts are handled correctly."""
        prompt = "same prompt"
        self.manager.save_prompt(prompt)
        self.manager.save_prompt(prompt)  # Duplicate
        self.manager.save_prompt("different prompt")
        self.manager.save_prompt(prompt)  # Duplicate again

        loaded_prompts = self.manager.load_history()
        # Should have: "same prompt", "different prompt", "same prompt"
        self.assertEqual(len(loaded_prompts), 3)
        self.assertEqual(loaded_prompts[0], "same prompt")
        self.assertEqual(loaded_prompts[1], "different prompt")
        self.assertEqual(loaded_prompts[2], "same prompt")

    def test_jsonl_format(self):
        """Test that prompts are saved in JSONL format."""
        prompt = "test prompt"
        self.manager.save_prompt(prompt)

        # Read the file and verify JSONL format
        with open(self.history_file, "r") as f:
            line = f.readline().strip()

        data = json.loads(line)
        self.assertIn("prompt", data)
        self.assertEqual(data["prompt"], prompt)
        self.assertIn("timestamp", data)
        self.assertIn("ts", data)

    def test_load_from_corrupted_file(self):
        """Test loading from a corrupted history file."""
        # Create a corrupted file
        self.history_file.parent.mkdir(exist_ok=True)
        with open(self.history_file, "w") as f:
            f.write("invalid json\n")
            f.write('{"prompt": "valid prompt"}\n')

        loaded_prompts = self.manager.load_history()
        # Should handle the corruption gracefully and load valid entries
        # The invalid line gets treated as a string prompt due to fallback logic
        self.assertEqual(len(loaded_prompts), 2)
        self.assertEqual(loaded_prompts[0], "invalid json")
        self.assertEqual(loaded_prompts[1], "valid prompt")

    def test_clear_history(self):
        """Test clearing history."""
        self.manager.save_prompt("test prompt")
        self.assertTrue(self.history_file.exists())

        result = self.manager.clear_history()
        self.assertTrue(result)
        self.assertFalse(self.history_file.exists())

    def test_get_history_stats(self):
        """Test getting history statistics."""
        # Initially empty
        stats = self.manager.get_history_stats()
        self.assertEqual(stats["total_prompts"], 0)
        self.assertEqual(stats["max_history"], 5)
        self.assertFalse(stats["file_exists"])

        # After adding prompts
        self.manager.save_prompt("prompt1")
        self.manager.save_prompt("prompt2")

        stats = self.manager.get_history_stats()
        self.assertEqual(stats["total_prompts"], 2)
        self.assertTrue(stats["file_exists"])
        self.assertGreater(stats["file_size_bytes"], 0)
        self.assertEqual(stats["format"], "JSONL (one JSON object per line)")

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries."""
        # Save more than max_history prompts
        prompts = [f"prompt{i}" for i in range(10)]
        for prompt in prompts:
            self.manager.save_prompt(prompt)

        # Force cleanup
        result = self.manager._cleanup_old_entries()
        self.assertTrue(result)

        # Verify only max_history entries remain
        loaded_prompts = self.manager.load_history()
        self.assertEqual(len(loaded_prompts), 5)
        self.assertEqual(loaded_prompts, prompts[-5:])

    def test_get_last_prompt(self):
        """Test getting the last prompt efficiently."""
        # Save some prompts
        prompts = ["first", "second", "third"]
        for prompt in prompts:
            self.manager.save_prompt(prompt)

        last_prompt = self.manager._get_last_prompt()
        self.assertEqual(last_prompt, "third")

        # Test with empty history
        self.manager.clear_history()
        last_prompt = self.manager._get_last_prompt()
        self.assertIsNone(last_prompt)

    def test_migration_from_old_format(self):
        """Test migration from old format (simple list)."""
        # Create old format file
        self.history_file.parent.mkdir(exist_ok=True)
        with open(self.history_file, "w") as f:
            json.dump(["old1", "old2", "old3"], f)

        # Load should migrate to new format
        loaded_prompts = self.manager.load_history()
        self.assertEqual(loaded_prompts, ["old1", "old2", "old3"])

        # Verify file was converted to new format
        with open(self.history_file, "r") as f:
            content = f.read()

        # Should now be in JSONL format (not JSON array)
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 3)  # Should have 3 JSONL lines
        for line in lines:
            data = json.loads(line.strip())
            self.assertIn("prompt", data)

    def test_disabled_history(self):
        """Test behavior when history is disabled."""
        # Create a manager with disabled history
        manager = PromptHistoryManager(project_dir=self.test_dir)
        manager.enabled = False

        # Saving should return True but not create file
        result = manager.save_prompt("test prompt")
        self.assertTrue(result)
        self.assertFalse(self.history_file.exists())

        # Loading should return empty list
        loaded = manager.load_history()
        self.assertEqual(loaded, [])

    def test_periodic_cleanup(self):
        """Test that periodic cleanup works after multiple saves."""
        # Save enough prompts to trigger cleanup (every 50 saves)
        for i in range(55):  # More than the cleanup threshold
            self.manager.save_prompt(f"prompt{i}")

        # File should exist and contain recent prompts
        self.assertTrue(self.history_file.exists())
        loaded_prompts = self.manager.load_history()

        # Should have max_history prompts (5) due to cleanup
        self.assertEqual(len(loaded_prompts), 5)
        # Should contain the most recent prompts
        expected = [f"prompt{i}" for i in range(50, 55)]
        self.assertEqual(loaded_prompts, expected)


class TestPromptHistoryManagerIntegration(unittest.TestCase):
    """Integration tests for PromptHistoryManager."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("aicoder.config.PROMPT_HISTORY_ENABLED", True)
    @patch("aicoder.config.PROMPT_HISTORY_MAX_SIZE", 100)
    def test_with_config_values(self):
        """Test manager initialization with config values."""
        manager = PromptHistoryManager(project_dir=self.test_dir)
        self.assertTrue(manager.enabled)
        self.assertEqual(manager.max_history, 100)

    @patch("aicoder.config.PROMPT_HISTORY_ENABLED", False)
    def test_with_disabled_config(self):
        """Test manager with disabled config."""
        manager = PromptHistoryManager(project_dir=self.test_dir)
        self.assertFalse(manager.enabled)

    def test_global_instance(self):
        """Test the global instance functionality."""
        from aicoder.prompt_history_manager import prompt_history_manager

        # Should be able to use the global instance
        self.assertIsNotNone(prompt_history_manager)

        # Should be able to save and load prompts
        test_prompt = "global test prompt"
        result = prompt_history_manager.save_prompt(test_prompt)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
