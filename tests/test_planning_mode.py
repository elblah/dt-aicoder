"""
Tests for planning mode functionality.
"""

import unittest
import sys
import os

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.planning_mode import (
    PlanningMode,
    get_planning_mode,
    PLAN_MODE_CONTENT,
    BUILD_SWITCH_CONTENT,
)


class TestPlanningMode(unittest.TestCase):
    """Test cases for the PlanningMode class."""

    def setUp(self):
        """Set up a fresh planning mode instance for each test."""
        # Reset the global instance
        import aicoder.planning_mode

        aicoder.planning_mode._planning_mode = None
        self.planning_mode = PlanningMode()

    def test_initial_state(self):
        """Test that planning mode starts disabled."""
        self.assertFalse(self.planning_mode.is_plan_mode_active())
        # Check internal state - message should be considered sent initially to avoid startup message
        self.assertTrue(self.planning_mode._mode_message_sent)

        # First call should return None (no build message on startup)
        content = self.planning_mode.get_mode_content()
        self.assertIsNone(content)

    def test_set_plan_mode(self):
        """Test setting planning mode on and off."""
        # Enable plan mode (starting from disabled)
        self.planning_mode.set_plan_mode(True)
        self.assertTrue(self.planning_mode.is_plan_mode_active())
        self.assertFalse(self.planning_mode._mode_message_sent)  # Reset on mode change

        # Disable plan mode (switching from plan to build)
        self.planning_mode.set_plan_mode(False)
        self.assertFalse(self.planning_mode.is_plan_mode_active())
        self.assertFalse(self.planning_mode._mode_message_sent)  # Reset on mode change

    def test_toggle_plan_mode(self):
        """Test toggling planning mode."""
        # Start with disabled
        self.assertFalse(self.planning_mode.is_plan_mode_active())

        # Toggle to enabled
        result = self.planning_mode.toggle_plan_mode()
        self.assertTrue(result)
        self.assertTrue(self.planning_mode.is_plan_mode_active())
        self.assertFalse(self.planning_mode._mode_message_sent)  # Reset on toggle

        # Toggle to disabled
        result = self.planning_mode.toggle_plan_mode()
        self.assertFalse(result)
        self.assertFalse(self.planning_mode.is_plan_mode_active())
        self.assertFalse(self.planning_mode._mode_message_sent)  # Reset on toggle

    def test_get_mode_content_plan_mode_transition(self):
        """Test getting content when transitioning TO plan mode."""
        # Initially in build mode, no content should be available (startup state)
        content = self.planning_mode.get_mode_content()
        self.assertIsNone(content)

        # Switch to plan mode - should get plan mode content once
        self.planning_mode.set_plan_mode(True)
        content = self.planning_mode.get_mode_content()
        # Check for the mode marker
        self.assertIn("<aicoder_active_mode>plan</aicoder_active_mode>", content)

        # Second call should return None (no more content for this mode)
        content = self.planning_mode.get_mode_content()
        self.assertIsNone(content)

    def test_get_mode_content_build_mode_transition(self):
        """Test getting content when transitioning TO build mode."""
        # First enable plan mode
        self.planning_mode.set_plan_mode(True)
        # Consume the plan mode content
        self.planning_mode.get_mode_content()

        # Then disable it (should trigger build switch content)
        self.planning_mode.set_plan_mode(False)
        content = self.planning_mode.get_mode_content()
        self.assertIn("<aicoder_active_mode>build</aicoder_active_mode>", content)

        # Second call should return None (no more switch content)
        content = self.planning_mode.get_mode_content()
        self.assertIsNone(content)

    def test_get_mode_content_stay_in_same_mode(self):
        """Test getting content when staying in the same mode."""
        # Force a transition to build mode by toggling from plan mode first
        self.planning_mode.set_plan_mode(True)  # Switch to plan mode
        self.planning_mode.set_plan_mode(
            False
        )  # Switch back to build mode (this is a real transition)
        content = self.planning_mode.get_mode_content()
        # Should get build mode content once
        self.assertIn("<aicoder_active_mode>build</aicoder_active_mode>", content)

        # Second call should return None
        content = self.planning_mode.get_mode_content()
        self.assertIsNone(content)

        # Third call should still return None (no change)
        content = self.planning_mode.get_mode_content()
        self.assertIsNone(content)

    def test_get_mode_content_multiple_transitions(self):
        """Test multiple mode transitions."""
        # Force a transition to build mode by toggling from plan mode first
        self.planning_mode.set_plan_mode(True)  # Switch to plan mode
        self.planning_mode.set_plan_mode(False)  # Switch back to build mode
        content1 = self.planning_mode.get_mode_content()
        self.assertIn("<aicoder_active_mode>build</aicoder_active_mode>", content1)

        # Switch to plan mode
        self.planning_mode.set_plan_mode(True)
        content2 = self.planning_mode.get_mode_content()
        self.assertIn("<aicoder_active_mode>plan</aicoder_active_mode>", content2)

        # Switch back to build mode
        self.planning_mode.set_plan_mode(False)
        content3 = self.planning_mode.get_mode_content()
        self.assertIn("<aicoder_active_mode>build</aicoder_active_mode>", content3)

        # All subsequent calls should return None until next mode change
        for _ in range(3):
            self.assertIsNone(self.planning_mode.get_mode_content())

    def test_writing_tools(self):
        """Test that writing tools are properly identified."""
        writing_tools = self.planning_mode.get_writing_tools()
        expected_tools = ["write_file", "edit_file", "create_backup"]
        self.assertEqual(set(writing_tools), set(expected_tools))

    def test_should_disable_tool(self):
        """Test tool disabling logic."""
        # When plan mode is off, no tools should be disabled
        self.planning_mode.set_plan_mode(False)
        self.assertFalse(self.planning_mode.should_disable_tool("write_file"))
        self.assertFalse(self.planning_mode.should_disable_tool("read_file"))
        self.assertFalse(self.planning_mode.should_disable_tool("run_shell_command"))

        # When plan mode is on, writing tools should be disabled
        self.planning_mode.set_plan_mode(True)
        self.assertTrue(self.planning_mode.should_disable_tool("write_file"))
        self.assertTrue(self.planning_mode.should_disable_tool("edit_file"))
        self.assertTrue(self.planning_mode.should_disable_tool("create_backup"))

        # But read-only tools should still work
        self.assertFalse(self.planning_mode.should_disable_tool("read_file"))
        self.assertFalse(self.planning_mode.should_disable_tool("list_directory"))
        self.assertFalse(self.planning_mode.should_disable_tool("grep"))

    def test_get_active_tools(self):
        """Test getting active tools list for API requests."""
        # Mock tool definitions
        all_tools = [
            {"function": {"name": "write_file"}},
            {"function": {"name": "edit_file"}},
            {"function": {"name": "read_file"}},
            {"function": {"name": "list_directory"}},
            {"function": {"name": "grep"}},
            {"function": {"name": "run_shell_command"}},
            {"function": {"name": "create_backup"}},
        ]

        # When plan mode is off, all tools should be active
        self.planning_mode.set_plan_mode(False)
        active_tools = self.planning_mode.get_active_tools(all_tools)
        expected_active = [
            "write_file",
            "edit_file",
            "read_file",
            "list_directory",
            "grep",
            "run_shell_command",
            "create_backup",
        ]
        self.assertEqual(set(active_tools), set(expected_active))

        # When plan mode is on, writing tools should be filtered out
        self.planning_mode.set_plan_mode(True)
        active_tools = self.planning_mode.get_active_tools(all_tools)
        expected_active = ["read_file", "list_directory", "grep", "run_shell_command"]
        self.assertEqual(set(active_tools), set(expected_active))

    def test_prompt_prefix(self):
        """Test prompt prefix based on mode."""
        # Normal mode
        self.planning_mode.set_plan_mode(False)
        prefix = self.planning_mode.get_prompt_prefix()
        self.assertIn(">", prefix)
        self.assertNotIn("[PLAN]", prefix)

        # Plan mode
        self.planning_mode.set_plan_mode(True)
        prefix = self.planning_mode.get_prompt_prefix()
        self.assertIn("[PLAN] >", prefix)

    def test_status_text(self):
        """Test status text generation."""
        # Normal mode
        self.planning_mode.set_plan_mode(False)
        status = self.planning_mode.get_status_text()
        self.assertIn("INACTIVE", status)
        self.assertIn("read-write", status)

        # Plan mode
        self.planning_mode.set_plan_mode(True)
        status = self.planning_mode.get_status_text()
        self.assertIn("ACTIVE", status)
        self.assertIn("read-only", status)


class TestGlobalPlanningMode(unittest.TestCase):
    """Test cases for the global planning mode instance."""

    def setUp(self):
        """Reset global instance before each test."""
        import aicoder.planning_mode

        aicoder.planning_mode._planning_mode = None

    def test_get_planning_mode_singleton(self):
        """Test that get_planning_mode returns the same instance."""
        instance1 = get_planning_mode()
        instance2 = get_planning_mode()
        self.assertIs(instance1, instance2)
        self.assertIsInstance(instance1, PlanningMode)


class TestPlanModeContent(unittest.TestCase):
    """Test cases for plan mode content constants."""

    def test_plan_mode_content(self):
        """Test that plan mode content contains expected text."""
        self.assertIn("PLANNING MODE", PLAN_MODE_CONTENT)
        self.assertIn("READ-ONLY ACCESS", PLAN_MODE_CONTENT)
        self.assertIn("FORBIDDEN", PLAN_MODE_CONTENT)
        self.assertIn("file, directory, or system state", PLAN_MODE_CONTENT)

    def test_build_switch_content(self):
        """Test that build switch content contains expected text."""
        self.assertIn("BUILD MODE ACTIVE", BUILD_SWITCH_CONTENT)
        self.assertIn("Full Tool Access Unlocked", BUILD_SWITCH_CONTENT)
        self.assertIn("File edits", BUILD_SWITCH_CONTENT)
        self.assertIn("All AI Coder tools are now available", BUILD_SWITCH_CONTENT)


class TestSessionModeDetection(unittest.TestCase):
    """Test cases for session mode detection."""

    def setUp(self):
        """Reset global instance before each test."""
        import aicoder.planning_mode

        aicoder.planning_mode._planning_mode = None

    def test_detect_planning_mode_from_session_planning(self):
        """Test detecting planning mode from session messages."""
        from aicoder.message_history import MessageHistory

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "I'll help you plan this"},
            {
                "role": "user",
                "content": "<aicoder_active_mode>plan</aicoder_active_mode>\n\nPlanning mode: Read-only tools only",
            },
        ]

        history = MessageHistory()
        detected = history.detect_planning_mode_from_session(messages)
        self.assertTrue(detected)

    def test_detect_planning_mode_from_session_build(self):
        """Test detecting build mode from session messages."""
        from aicoder.message_history import MessageHistory

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "I'll help you implement this"},
            {"role": "user", "content": "Make the changes"},
        ]

        history = MessageHistory()
        detected = history.detect_planning_mode_from_session(messages)
        self.assertFalse(detected)

    def test_detect_planning_mode_from_empty_session(self):
        """Test detecting mode from empty session."""
        from aicoder.message_history import MessageHistory

        history = MessageHistory()
        detected = history.detect_planning_mode_from_session([])
        self.assertFalse(detected)


if __name__ == "__main__":
    unittest.main()
