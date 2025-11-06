"""
Simple project memory system for AI Coder.

Provides persistent storage of project-specific knowledge using SQLite.
Focuses on simplicity, readability, and maintainability.
"""

import os
import sqlite3
from typing import Optional, List, Dict, Any


class ProjectMemory:
    """
    Simple project-based memory storage using SQLite.

    Stores project-specific knowledge, decisions, and solutions
    that persist across AI Coder sessions.
    """

    def __init__(self, project_path: str):
        """
        Initialize project memory.

        Args:
            project_path: Root directory of the project
        """
        self.project_path = os.path.abspath(project_path)
        self.db_path = os.path.join(self.project_path, ".aicoder", "memory.db")
        self._disabled = False

        # Ensure .aicoder directory exists
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        except Exception:
            # Can't create directory, disable memory functionality
            self._disabled = True
            return

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database with simple schema."""
        if self._disabled:
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Main notes table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS notes (
                        name TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        tags TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 0,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Indexes for common queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_notes_updated_at
                    ON notes(updated_at DESC)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_notes_last_accessed
                    ON notes(last_accessed DESC)
                """)

                conn.commit()
        except Exception:
            # If database initialization fails, disable memory functionality
            self._disabled = True

    def create(self, name: str, content: str, tags: List[str] = None) -> str:
        """
        Create or update a memory note.

        Args:
            name: Unique identifier for the note
            content: Note content
            tags: Optional list of tags for categorization

        Returns:
            Success message
        """
        if self._disabled:
            return "Memory system is disabled (read-only filesystem)"

        tags_str = ",".join(tags or [])

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if note exists to determine if we're creating or updating
                cursor = conn.execute("SELECT name FROM notes WHERE name = ?", (name,))
                exists = cursor.fetchone() is not None

                # Insert or replace note
                conn.execute(
                    """
                    INSERT OR REPLACE INTO notes (name, content, tags, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (name, content, tags_str),
                )

                conn.commit()

                action = "Updated" if exists else "Created"
                return f"{action} memory note: {name}"
        except Exception:
            return "Failed to save memory note"

    def read(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Read a specific memory note.

        Args:
            name: Note identifier

        Returns:
            Note data or None if not found
        """
        if self._disabled:
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update access statistics first
                conn.execute(
                    """
                    UPDATE notes
                    SET access_count = access_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE name = ?
                """,
                    (name,),
                )

                # Read the note
                cursor = conn.execute(
                    """
                    SELECT name, content, tags, created_at, updated_at, access_count
                    FROM notes
                    WHERE name = ?
                """,
                    (name,),
                )

                row = cursor.fetchone()
                if row:
                    return {
                        "name": row[0],
                        "content": row[1],
                        "tags": row[2].split(",") if row[2] else [],
                        "created_at": row[3],
                        "updated_at": row[4],
                        "access_count": row[5],
                    }

                return None
        except Exception:
            return None

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search memory notes by content or name.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching notes
        """
        if self._disabled:
            return []

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT name, content, tags, created_at, updated_at, access_count
                    FROM notes
                    WHERE name LIKE ? OR content LIKE ?
                    ORDER BY last_accessed DESC
                    LIMIT ?
                """,
                    (f"%{query}%", f"%{query}%", limit),
                )

                results = []
                for row in cursor.fetchall():
                    results.append(
                        {
                            "name": row[0],
                            "content": row[1],
                            "tags": row[2].split(",") if row[2] else [],
                            "created_at": row[3],
                            "updated_at": row[4],
                            "access_count": row[5],
                        }
                    )

                return results
        except Exception:
            return []

    def list(self, limit: int = 20, sort_by: str = "updated_at") -> List[Dict[str, Any]]:
        """
        List all memory notes.

        Args:
            limit: Maximum number of results
            sort_by: Sort column (updated_at, created_at, last_accessed, name)

        Returns:
            List of notes
        """
        if self._disabled:
            return []

        # Validate sort column
        valid_sort_columns = [
            "updated_at",
            "created_at",
            "last_accessed",
            "name",
        ]
        if sort_by not in valid_sort_columns:
            sort_by = "updated_at"

        # Determine sort direction (updated_at desc, others asc)
        sort_direction = "DESC" if sort_by == "updated_at" else "ASC"

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    f"""
                    SELECT name, content, tags, created_at, updated_at, access_count
                    FROM notes
                    ORDER BY {sort_by} {sort_direction}
                    LIMIT ?
                """,
                    (limit,),
                )

                results = []
                for row in cursor.fetchall():
                    results.append(
                        {
                            "name": row[0],
                            "content": row[1],
                            "tags": row[2].split(",") if row[2] else [],
                            "created_at": row[3],
                            "updated_at": row[4],
                            "access_count": row[5],
                        }
                    )

                return results
        except Exception:
            return []

    def delete(self, name: str) -> bool:
        """
        Delete a memory note.

        Args:
            name: Note identifier

        Returns:
            True if deleted, False if not found or error
        """
        if self._disabled:
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM notes WHERE name = ?", (name,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    def stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics.

        Returns:
            Dictionary with stats
        """
        if self._disabled:
            return {"disabled": True, "total_notes": 0}

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get total notes
                cursor = conn.execute("SELECT COUNT(*) FROM notes")
                total_notes = cursor.fetchone()[0]

                # Get storage size
                try:
                    import os
                    storage_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                except Exception:
                    storage_bytes = 0

                # Get tag statistics
                cursor = conn.execute("SELECT tags FROM notes WHERE tags != ''")
                all_tags = set()
                for row in cursor.fetchall():
                    if row[0]:
                        all_tags.update(tag.strip() for tag in row[0].split(',') if tag.strip())

                # Get most accessed notes
                cursor = conn.execute("""
                    SELECT name, access_count 
                    FROM notes 
                    WHERE access_count > 0 
                    ORDER BY access_count DESC 
                    LIMIT 5
                """)
                most_accessed = dict(cursor.fetchall())

                # Get recently updated notes
                cursor = conn.execute("""
                    SELECT name, updated_at 
                    FROM notes 
                    ORDER BY updated_at DESC 
                    LIMIT 5
                """)
                recently_updated = cursor.fetchall()

                return {
                    "disabled": False,
                    "total_notes": total_notes,
                    "storage_bytes": storage_bytes,
                    "tag_count": len(all_tags),
                    "unique_tags": list(all_tags),
                    "most_accessed": most_accessed,
                    "recently_updated": recently_updated
                }
        except Exception:
            return {"disabled": True, "total_notes": 0}

    def get_stats(self) -> Dict[str, Any]:
        """
        Alias for stats() method for backward compatibility.
        """
        return self.stats()

    def list_all(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Alias for list() method for backward compatibility.
        """
        return self.list(limit=limit)

    def auto_save_decision(self, issue: str, solution: str, tags: List[str] = None) -> str:
        """
        Auto-save a decision to memory.

        Args:
            issue: The issue or problem addressed
            solution: The solution implemented
            tags: Optional list of tags

        Returns:
            Success message
        """
        import time
        name = f"decision_{int(time.time())}"
        content = f"Issue: {issue}\nSolution: {solution}"
        # Add auto-saved and decision tags
        all_tags = (tags or []) + ["auto-saved", "decision"]
        return self.create(name, content, all_tags)


# Global memory instance management
_memory_instances = {}


def get_project_memory(project_path: str) -> ProjectMemory:
    """
    Get or create a project memory instance.

    Args:
        project_path: Project directory path

    Returns:
        ProjectMemory instance
    """
    abs_path = os.path.abspath(project_path)
    if abs_path not in _memory_instances:
        _memory_instances[abs_path] = ProjectMemory(abs_path)
    return _memory_instances[abs_path]


def reset_memory():
    """Reset all memory instances (for testing)."""
    global _memory_instances
    _memory_instances.clear()