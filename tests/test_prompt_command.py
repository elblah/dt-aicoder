#!/usr/bin/env python3
"""Test the enhanced /prompt command functionality"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure YOLO_MODE is set to prevent hanging on approval prompts
os.environ["YOLO_MODE"] = "1"

# Add the parent directory to the path so we can import aicoder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.prompt_loader import (
    get_user_prompts_directory,
    list_available_prompts,
    load_prompt_from_file,
    _apply_prompt_variables,
)
from aicoder.commands.prompt_command import PromptCommand


class TestPromptCommand(unittest.TestCase):
    """Test the enhanced /prompt command functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.prompts_dir = Path(self.temp_dir) / ".config" / "aicoder" / "prompts"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

        # Create test prompt files
        (self.prompts_dir / "001-gemini.txt").write_text(
            "You are a Gemini AI assistant. {current_directory}"
        )
        (self.prompts_dir / "qwen.md").write_text(
            "You are a Qwen AI expert. Current user: {current_user}"
        )
        (self.prompts_dir / "python-helper.md").write_text(
            "You are a Python expert helper."
        )

        # Mock the home directory
        self.home_patcher = patch("pathlib.Path.home", return_value=Path(self.temp_dir))
        self.home_patcher.start()

    def tearDown(self):
        """Clean up test fixtures."""
        self.home_patcher.stop()
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_user_prompts_directory(self):
        """Test getting the user prompts directory."""
        prompts_dir = get_user_prompts_directory()
        expected = Path(self.temp_dir) / ".config" / "aicoder" / "prompts"
        self.assertEqual(prompts_dir, expected)

    def test_list_available_prompts(self):
        """Test listing available prompts."""
        prompts = list_available_prompts()

        # Should have 3 prompts
        self.assertEqual(len(prompts), 3)

        # Check they are sorted and numbered correctly
        self.assertEqual(prompts[0][0], 1)  # number
        self.assertEqual(prompts[0][1], "001-gemini.txt")  # filename
        self.assertEqual(prompts[1][0], 2)
        self.assertEqual(prompts[1][1], "python-helper.md")  # sorted alphabetically
        self.assertEqual(prompts[2][0], 3)
        self.assertEqual(prompts[2][1], "qwen.md")

    def test_load_prompt_from_file(self):
        """Test loading prompt content from file."""
        gemini_path = self.prompts_dir / "001-gemini.txt"
        content = load_prompt_from_file(gemini_path)

        self.assertIsNotNone(content)
        self.assertIn("You are a Gemini AI assistant.", content)
        self.assertIn(os.getcwd(), content)  # Variable should be replaced

    def test_apply_prompt_variables(self):
        """Test variable replacement in prompts."""
        prompt = "Hello {current_user} in {current_directory} at {current_datetime}"
        result = _apply_prompt_variables(prompt)

        self.assertNotEqual(prompt, result)
        self.assertIn(os.getcwd(), result)
        self.assertNotIn("{current_directory}", result)
        self.assertNotIn("{current_user}", result)
        self.assertNotIn("{current_datetime}", result)

    def test_list_prompts_when_directory_missing(self):
        """Test listing prompts when directory doesn't exist."""
        # Remove the directory
        import shutil

        shutil.rmtree(self.prompts_dir.parent.parent, ignore_errors=True)

        prompts = list_available_prompts()
        self.assertEqual(len(prompts), 0)

    def test_handle_prompt_list(self):
        """Test the /prompt list command."""

        class MockApp:
            def __init__(self):
                self.message_history = MagicMock()

        mock_app = MockApp()
        handler = PromptCommand(mock_app)

        # Capture print output
        with patch("builtins.print") as mock_print:
            handler._handle_prompt_list()

            # Check that print was called with expected content
            mock_print.assert_called()
            # Find the call that contains the prompt listing
            prompt_calls = [
                call
                for call in mock_print.call_args_list
                if "001-gemini.txt" in str(call) or "qwen.md" in str(call)
            ]
            self.assertTrue(len(prompt_calls) > 0, "Should print the available prompts")

    def test_handle_prompt_set_valid(self):
        """Test the /prompt set command with a valid number."""

        class MockApp:
            def __init__(self):
                mock_message_history = MagicMock()
                mock_message_history.messages = [
                    {"role": "system", "content": "old prompt"}
                ]
                self.message_history = mock_message_history

        mock_app = MockApp()
        handler = PromptCommand(mock_app)

        # Capture print output and environment variable
        with patch("builtins.print") as mock_print:
            with patch.dict(os.environ, {}, clear=False):
                result = handler._handle_prompt_set(["set", "1"])

                # Should return (False, False) - don't quit, don't run API call
                self.assertEqual(result, (False, False))

                # Check that environment variable was set
                self.assertIn("AICODER_PROMPT_MAIN", os.environ)

                # Check that system message was updated
                self.assertEqual(mock_app.message_history.messages[0]["role"], "system")
                self.assertIn(
                    "You are a Gemini AI assistant",
                    mock_app.message_history.messages[0]["content"],
                )

    def test_handle_prompt_set_invalid_number(self):
        """Test the /prompt set command with an invalid number."""

        class MockApp:
            def __init__(self):
                self.message_history = MagicMock()

        mock_app = MockApp()
        handler = PromptCommand(mock_app)

        with patch("builtins.print") as mock_print:
            result = handler._handle_prompt_set(["set", "999"])

            # Should return (False, False)
            self.assertEqual(result, (False, False))

            # Should print error message
            error_calls = [
                call
                for call in mock_print.call_args_list
                if "Error:" in str(call) and "not found" in str(call)
            ]
            self.assertTrue(
                len(error_calls) > 0, "Should print error for invalid prompt number"
            )

    def test_handle_prompt_set_no_prompts(self):
        """Test the /prompt set command when no prompts are available."""
        # Remove all prompt files
        for file in self.prompts_dir.glob("*"):
            file.unlink()

        class MockApp:
            def __init__(self):
                self.message_history = MagicMock()

        mock_app = MockApp()
        handler = PromptCommand(mock_app)

        with patch("builtins.print") as mock_print:
            result = handler._handle_prompt_set(["set", "1"])

            # Should return (False, False)
            self.assertEqual(result, (False, False))

            # Should print error about no prompts
            error_calls = [
                call
                for call in mock_print.call_args_list
                if "No prompt files available" in str(call)
            ]
            self.assertTrue(
                len(error_calls) > 0, "Should print error when no prompts available"
            )

    @patch("subprocess.run")
    @patch("builtins.input")
    @patch("tempfile.NamedTemporaryFile")
    def test_handle_prompt_edit_temp_file(
        self, mock_tempfile, mock_input, mock_subprocess
    ):
        """Test the /prompt edit command with a temporary file."""

        class MockApp:
            def __init__(self):
                self.message_history = MagicMock()
                self.message_history.messages = [
                    {"role": "system", "content": "old prompt"}
                ]

        mock_app = MockApp()
        handler = PromptCommand(mock_app)
        handler.app = mock_app  # Set the app reference
        handler._run_editor_in_tmux_popup = MagicMock(
            return_value=False
        )  # Don't use tmux popup

        # Mock the temporary file
        mock_file = MagicMock()
        mock_file.name = "/tmp/test-prompt.md"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        # Mock user input to save to prompts directory
        mock_input.side_effect = ["1", "test-edit.md"]

        # Mock the file writing and reading
        mock_file.write = MagicMock()

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                "Edited prompt content"
            )
            mock_open.return_value.__enter__.return_value.write = MagicMock()

            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.write_text"):
                    with patch.dict(
                        os.environ, {"AICODER_PROMPT_MAIN": ""}, clear=False
                    ):
                        result = handler._handle_prompt_edit(["edit"])

                        # Should return (False, False)
                        self.assertEqual(result, (False, False))

                        # Should have called the editor
                        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    @patch("builtins.input")
    @patch("tempfile.NamedTemporaryFile")
    def test_handle_prompt_edit_cancelled(
        self, mock_tempfile, mock_input, mock_subprocess
    ):
        """Test the /prompt edit command when user cancels."""

        class MockApp:
            def __init__(self):
                self.message_history = MagicMock()

        mock_app = MockApp()
        handler = PromptCommand(mock_app)
        handler.app = mock_app  # Set the app reference
        handler._run_editor_in_tmux_popup = MagicMock(
            return_value=False
        )  # Don't use tmux popup

        # Mock the temporary file
        mock_file = MagicMock()
        mock_file.name = "/tmp/test-prompt.md"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        # Mock user input to discard changes (Ctrl+D/EOFError)
        mock_input.side_effect = EOFError

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                "Edited prompt content"
            )
            mock_open.return_value.__enter__.return_value.write = MagicMock()

            with patch("pathlib.Path.unlink") as mock_unlink:
                result = handler._handle_prompt_edit(["edit"])

                # Should return (False, False)
                self.assertEqual(result, (False, False))

                # Should have cleaned up temp file
                mock_unlink.assert_called()

    def test_update_conversation_prompt(self):
        """Test updating the conversation prompt."""

        class MockApp:
            def __init__(self):
                mock_message_history = MagicMock()
                mock_message_history.messages = [
                    {"role": "system", "content": "old prompt"}
                ]
                self.message_history = mock_message_history

        mock_app = MockApp()
        handler = PromptCommand(mock_app)
        handler.app = mock_app  # Set the app reference

        # Update the prompt
        handler._update_conversation_prompt("new prompt")

        # Check that the system message was updated
        self.assertEqual(mock_app.message_history.messages[0]["content"], "new prompt")


if __name__ == "__main__":
    unittest.main()
