"""
Tests for the memory system.
"""

import unittest
import tempfile
import os
import shutil
from aicoder.memory import ProjectMemory, reset_memory


class TestProjectMemory(unittest.TestCase):
    """Test the ProjectMemory class."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.memory = ProjectMemory(self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
        reset_memory()

    def test_database_initialization(self):
        """Test that database is created and initialized."""
        self.assertTrue(os.path.exists(self.memory.db_path))

        # Check tables exist
        import sqlite3

        with sqlite3.connect(self.memory.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='notes'"
            )
            self.assertIsNotNone(cursor.fetchone())

            # Check indexes exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_notes_updated_at'"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_create_and_read_note(self):
        """Test creating and reading a note."""
        # Create note
        result = self.memory.create(
            "test_note", "This is test content", ["tag1", "tag2"]
        )
        self.assertIn("Created memory note: test_note", result)

        # Read note
        note = self.memory.read("test_note")
        self.assertIsNotNone(note)
        self.assertEqual(note["name"], "test_note")
        self.assertEqual(note["content"], "This is test content")
        self.assertEqual(note["tags"], ["tag1", "tag2"])
        self.assertEqual(note["access_count"], 1)

    def test_update_note(self):
        """Test updating an existing note."""
        # Create note
        self.memory.create("test_note", "Original content")

        # Update note
        result = self.memory.create("test_note", "Updated content", ["new_tag"])
        self.assertIn("Updated memory note: test_note", result)

        # Check updated content
        note = self.memory.read("test_note")
        self.assertEqual(note["content"], "Updated content")
        self.assertEqual(note["tags"], ["new_tag"])

    def test_read_nonexistent_note(self):
        """Test reading a note that doesn't exist."""
        note = self.memory.read("nonexistent")
        self.assertIsNone(note)

    def test_search_notes(self):
        """Test searching notes."""
        # Create test notes
        self.memory.create(
            "api_setup", "Configure the API with OAuth2", ["api", "auth"]
        )
        self.memory.create(
            "database_issue",
            "Fixed database connection timeout",
            ["database", "debugging"],
        )
        self.memory.create(
            "auth_fix", "Updated authentication middleware", ["auth", "security"]
        )

        # Search for "auth"
        results = self.memory.search("auth")
        self.assertEqual(len(results), 2)

        # Search for "database"
        results = self.memory.search("database")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "database_issue")

    def test_list_notes(self):
        """Test listing all notes."""
        # Create test notes
        self.memory.create("note1", "Content 1")
        self.memory.create("note2", "Content 2")
        self.memory.create("note3", "Content 3")

        # List all notes
        notes = self.memory.list_all()
        self.assertEqual(len(notes), 3)

        # Check sorting (default by updated_at DESC)
        names = [note["name"] for note in notes]
        self.assertIn("note1", names)
        self.assertIn("note2", names)
        self.assertIn("note3", names)

    def test_delete_note(self):
        """Test deleting a note."""
        # Create note
        self.memory.create("test_note", "Content")

        # Verify it exists
        note = self.memory.read("test_note")
        self.assertIsNotNone(note)

        # Delete note
        result = self.memory.delete("test_note")
        self.assertTrue(result)

        # Verify it's gone
        note = self.memory.read("test_note")
        self.assertIsNone(note)

    def test_delete_nonexistent_note(self):
        """Test deleting a note that doesn't exist."""
        result = self.memory.delete("nonexistent")
        self.assertFalse(result)

    def test_get_stats(self):
        """Test getting memory statistics."""
        # Create test notes
        self.memory.create("note1", "Content 1", ["tag1"])
        self.memory.create("note2", "Content 2", ["tag1", "tag2"])

        # Read a note to increase access count
        self.memory.read("note1")
        self.memory.read("note1")

        stats = self.memory.get_stats()

        self.assertEqual(stats["total_notes"], 2)
        self.assertGreater(stats["storage_bytes"], 0)
        self.assertEqual(stats["tag_count"], 2)
        self.assertIn("tag1", stats["unique_tags"])
        self.assertIn("tag2", stats["unique_tags"])

        # Check most accessed
        most_accessed = dict(stats["most_accessed"])
        self.assertIn("note1", most_accessed)
        self.assertEqual(most_accessed["note1"], 2)

    def test_auto_save_decision(self):
        """Test auto-saving decisions."""
        result = self.memory.auto_save_decision(
            "API calls were failing with timeout errors",
            "Increased timeout from 30s to 60s in config.yaml",
            ["debugging", "api"],
        )

        self.assertIn("Created memory note: decision_", result)

        # Verify the note was created correctly
        notes = self.memory.list_all()
        self.assertEqual(len(notes), 1)

        note = self.memory.read(notes[0]["name"])
        self.assertIn("API calls were failing", note["content"])
        self.assertIn("Increased timeout", note["content"])
        self.assertIn("auto-saved", note["tags"])
        self.assertIn("decision", note["tags"])


class TestMemoryTool(unittest.TestCase):
    """Test the memory tool integration."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        from aicoder.memory import get_project_memory, reset_memory

        reset_memory()
        self.memory = get_project_memory(self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
        from aicoder.memory import reset_memory

        reset_memory()

    def test_memory_tool_create(self):
        """Test memory tool create operation."""
        from aicoder.tool_manager.internal_tools.memory import execute_memory

        # Mock stats object
        class MockStats:
            tool_calls = 0
            tool_errors = 0

        stats = MockStats()
        result = execute_memory(
            operation="create",
            name="test_note",
            content="Test content",
            tags=["test"],
            stats=stats,
            project_path=self.test_dir,
        )

        self.assertIn("Created memory note: test_note", result)
        self.assertEqual(stats.tool_calls, 1)
        self.assertEqual(stats.tool_errors, 0)

    def test_memory_tool_update(self):
        """Test memory tool update operation."""
        from aicoder.tool_manager.internal_tools.memory import execute_memory

        # Create a note first
        self.memory.create("test_note", "Original content", ["original"])

        class MockStats:
            tool_calls = 0
            tool_errors = 0

        stats = MockStats()
        result = execute_memory(
            operation="update",
            name="test_note",
            content="Updated content",
            tags=["updated"],
            stats=stats,
            project_path=self.test_dir,
        )

        self.assertIn("Updated memory note: test_note", result)
        self.assertEqual(stats.tool_calls, 1)

        # Verify the update worked
        note = self.memory.read("test_note")
        self.assertEqual(note["content"], "Updated content")
        self.assertEqual(note["tags"], ["updated"])

    def test_memory_tool_read(self):
        """Test memory tool read operation."""
        from aicoder.tool_manager.internal_tools.memory import execute_memory

        # Create a note first
        self.memory.create("test_note", "Test content")

        class MockStats:
            tool_calls = 0
            tool_errors = 0

        stats = MockStats()
        result = execute_memory(operation="read", name="test_note", stats=stats,
            project_path=self.test_dir,
        )

        self.assertIn("Memory Note: test_note", result)
        self.assertIn("Test content", result)
        self.assertEqual(stats.tool_calls, 1)

    def test_memory_tool_search(self):
        """Test memory tool search operation."""
        from aicoder.tool_manager.internal_tools.memory import execute_memory

        # Create test notes
        self.memory.create("api_note", "API configuration details")
        self.memory.create("db_note", "Database setup instructions")

        class MockStats:
            tool_calls = 0
            tool_errors = 0

        stats = MockStats()
        result = execute_memory(operation="search", query="API", stats=stats,
            project_path=self.test_dir,
        )

        self.assertIn("Found 1 memory notes matching 'API'", result)
        self.assertIn("api_note", result)
        self.assertEqual(stats.tool_calls, 1)

    def test_memory_tool_list(self):
        """Test memory tool list operation."""
        from aicoder.tool_manager.internal_tools.memory import execute_memory

        # Create test notes
        self.memory.create("note1", "Content 1")
        self.memory.create("note2", "Content 2")

        class MockStats:
            tool_calls = 0
            tool_errors = 0

        stats = MockStats()
        result = execute_memory(operation="list", stats=stats,
            project_path=self.test_dir,
        )

        self.assertIn("Memory notes (sorted by updated_at)", result)
        self.assertIn("note1", result)
        self.assertIn("note2", result)
        self.assertEqual(stats.tool_calls, 1)

    def test_memory_tool_stats(self):
        """Test memory tool stats operation."""
        from aicoder.tool_manager.internal_tools.memory import execute_memory

        # Create test notes
        self.memory.create("note1", "Content 1")
        self.memory.create("note2", "Content 2")

        class MockStats:
            tool_calls = 0
            tool_errors = 0

        stats = MockStats()
        result = execute_memory(operation="stats", stats=stats,
            project_path=self.test_dir,
        )

        self.assertIn("Memory Statistics:", result)
        self.assertIn("Total notes: 2", result)
        self.assertEqual(stats.tool_calls, 1)

    def test_memory_tool_delete(self):
        """Test memory tool delete operation."""
        from aicoder.tool_manager.internal_tools.memory import execute_memory

        # Create a note first
        self.memory.create("test_note", "Test content")

        class MockStats:
            tool_calls = 0
            tool_errors = 0

        stats = MockStats()
        result = execute_memory(operation="delete", name="test_note", stats=stats,
            project_path=self.test_dir,
        )

        self.assertIn("Deleted memory note: test_note", result)
        self.assertEqual(stats.tool_calls, 1)

        # Verify it's gone
        note = self.memory.read("test_note")
        self.assertIsNone(note)

    def test_memory_tool_error_handling(self):
        """Test memory tool error handling."""
        from aicoder.tool_manager.internal_tools.memory import execute_memory

        class MockStats:
            tool_calls = 0
            tool_errors = 0

        stats = MockStats()

        # Test missing required parameters
        result = execute_memory(operation="create", stats=stats,
            project_path=self.test_dir,
        )
        self.assertIn("Error:", result)
        self.assertEqual(stats.tool_errors, 1)

        # Test unknown operation
        result = execute_memory(operation="unknown", stats=stats,
            project_path=self.test_dir,
        )
        self.assertIn("Unknown operation", result)
        self.assertEqual(stats.tool_errors, 2)


if __name__ == "__main__":
    unittest.main()
