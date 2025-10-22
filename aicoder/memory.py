"""
Simple project memory system for AI Coder.

Provides persistent storage of project-specific knowledge using SQLite.
Focuses on simplicity, readability, and maintainability.
"""

import os
import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime


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
        
        # Ensure .aicoder directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with simple schema."""
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
        tags_str = ','.join(tags or [])
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if note exists to determine if we're creating or updating
            cursor = conn.execute(
                "SELECT name FROM notes WHERE name = ?", (name,)
            )
            exists = cursor.fetchone() is not None
            
            # Insert or replace note
            conn.execute("""
                INSERT OR REPLACE INTO notes (name, content, tags, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (name, content, tags_str))
            
            conn.commit()
            
            action = "Updated" if exists else "Created"
            return f"{action} memory note: {name}"
    
    def read(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Read a specific memory note.
        
        Args:
            name: Note identifier
            
        Returns:
            Note data or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            # Update access statistics first
            conn.execute("""
                UPDATE notes 
                SET access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE name = ?
            """, (name,))
            
            cursor = conn.execute("""
                SELECT name, content, tags, created_at, updated_at, 
                       access_count, last_accessed
                FROM notes WHERE name = ?
            """, (name,))
            
            row = cursor.fetchone()
            if row:
                conn.commit()
                
                return {
                    'name': row[0],
                    'content': row[1],
                    'tags': row[2].split(',') if row[2] else [],
                    'created_at': row[3],
                    'updated_at': row[4],
                    'access_count': row[5],
                    'last_accessed': row[6]
                }
        
        return None
    
    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search memory notes using simple text matching.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching notes
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name, content, tags, created_at, updated_at,
                       access_count, last_accessed
                FROM notes 
                WHERE content LIKE ? OR name LIKE ? OR tags LIKE ?
                ORDER BY last_accessed DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'name': row[0],
                    'content': row[1],
                    'tags': row[2].split(',') if row[2] else [],
                    'created_at': row[3],
                    'updated_at': row[4],
                    'access_count': row[5],
                    'last_accessed': row[6]
                })
            
            return results
    
    def list_all(self, limit: int = 50, sort_by: str = "updated_at") -> List[Dict[str, Any]]:
        """
        List all memory notes.
        
        Args:
            limit: Maximum number of notes to return
            sort_by: Sort column ('updated_at', 'created_at', 'last_accessed', 'name')
            
        Returns:
            List of all notes
        """
        valid_sort_columns = ['updated_at', 'created_at', 'last_accessed', 'name']
        if sort_by not in valid_sort_columns:
            sort_by = 'updated_at'
        
        order = "DESC" if sort_by != 'name' else "ASC"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT name, content, tags, created_at, updated_at,
                       access_count, last_accessed
                FROM notes 
                ORDER BY {sort_by} {order}
                LIMIT ?
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'name': row[0],
                    'content': row[1][:200] + "..." if len(row[1]) > 200 else row[1],
                    'tags': row[2].split(',') if row[2] else [],
                    'created_at': row[3],
                    'updated_at': row[4],
                    'access_count': row[5],
                    'last_accessed': row[6]
                })
            
            return results
    
    def delete(self, name: str) -> bool:
        """
        Delete a memory note.
        
        Args:
            name: Note identifier
            
        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM notes WHERE name = ?", (name,))
            conn.commit()
            
            return cursor.rowcount > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total notes
            stats['total_notes'] = conn.execute(
                "SELECT COUNT(*) FROM notes"
            ).fetchone()[0]
            
            # Storage usage
            stats['storage_bytes'] = conn.execute(
                "SELECT SUM(LENGTH(content)) FROM notes"
            ).fetchone()[0] or 0
            
            # Most accessed notes
            stats['most_accessed'] = conn.execute("""
                SELECT name, access_count FROM notes 
                WHERE access_count > 0
                ORDER BY access_count DESC LIMIT 5
            """).fetchall()
            
            # Recently updated
            stats['recently_updated'] = conn.execute("""
                SELECT name, updated_at FROM notes 
                ORDER BY updated_at DESC LIMIT 5
            """).fetchall()
            
            # All tags
            tags_result = conn.execute("SELECT tags FROM notes WHERE tags != ''")
            all_tags = set()
            for row in tags_result:
                if row[0]:
                    all_tags.update(row[0].split(','))
            
            stats['unique_tags'] = sorted(list(all_tags))
            stats['tag_count'] = len(all_tags)
            
            return stats
    
    def auto_save_decision(self, context: str, decision: str, tags: List[str] = None) -> str:
        """
        Automatically save an important decision or discovery.
        
        Args:
            context: What led to this decision
            decision: The decision or discovery made
            tags: Optional tags
            
        Returns:
            Result message
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"decision_{timestamp}"
        
        content = f"Context: {context}\n\nDecision: {decision}"
        
        auto_tags = ['auto-saved', 'decision']
        if tags:
            auto_tags.extend(tags)
        
        return self.create(name, content, auto_tags)


# Global memory instance (will be initialized in AICoder)
_memory_instance: Optional[ProjectMemory] = None


def get_project_memory(project_path: str = None) -> ProjectMemory:
    """
    Get or create the project memory instance.
    
    Args:
        project_path: Project directory (uses current working directory if None)
        
    Returns:
        ProjectMemory instance
    """
    global _memory_instance
    
    if _memory_instance is None:
        if project_path is None:
            project_path = os.getcwd()
        _memory_instance = ProjectMemory(project_path)
    
    return _memory_instance


def reset_memory():
    """Reset the global memory instance (for testing)."""
    global _memory_instance
    _memory_instance = None