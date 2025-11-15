"""
Memory Plugin for AI Coder

This plugin provides project memory management system with:
1. A memory tool implementation for the AI to store/retrieve project knowledge
2. SQLite-based storage for persistent project memory
"""

import os
import json
import sqlite3
from typing import Optional, List, Dict, Any

# Global memory instances
_memory_instances = {}

# Custom memory tool definition
MEMORY_TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "hide_results": True,
    "hide_arguments": False,
    "approval_excludes_arguments": True,
    "name": "memory",
    "description": "Manage project-specific knowledge and decisions that persist across AI Coder sessions. Store important information about the project structure, patterns, decisions, and context.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["create", "update", "read", "search", "delete", "list", "stats", "auto_save"],
                "description": "Memory operation to perform"
            },
            "name": {
                "type": "string",
                "description": "Name/identifier for the memory note (required for create, update, read, delete, auto_save)"
            },
            "content": {
                "type": "string",
                "description": "Content of the memory note (required for create, update, auto_save)"
            },
            "query": {
                "type": "string",
                "description": "Search query (required for search)"
            },
            "context": {
                "type": "string",
                "description": "Context for auto_save decision (required for auto_save)"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorizing memory notes"
            }
        },
        "required": ["operation"]
    }
}


class ProjectMemory:
    """Memory storage for a specific project."""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.memory_dir = os.path.join(project_path, ".aicoder")
        self.db_path = os.path.join(self.memory_dir, "memory.db")
        self._disabled = False
        
        # Create memory directory and database if needed
        try:
            os.makedirs(self.memory_dir, exist_ok=True)
            self._init_database()
        except Exception as e:
            print(f"[X] Failed to initialize memory system: {e}")
            self._disabled = True

    def _init_database(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,  -- JSON array
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def create(self, name: str, content: str, tags: Optional[List[str]] = None) -> bool:
        """Create a new memory note."""
        if self._disabled:
            return False
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO memory_notes (name, content, tags) VALUES (?, ?, ?)",
                    (name, content, json.dumps(tags) if tags else None)
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"[X] Failed to create memory note: {e}")
            return False

    def read(self, name: str) -> Optional[Dict[str, Any]]:
        """Read a memory note by name."""
        if self._disabled:
            return None
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT name, content, tags, created_at, updated_at, access_count FROM memory_notes WHERE name = ?",
                    (name,)
                )
                row = cursor.fetchone()
                if row:
                    # Increment access count
                    conn.execute(
                        "UPDATE memory_notes SET access_count = access_count + 1 WHERE name = ?",
                        (name,)
                    )
                    conn.commit()
                    
                    return {
                        "name": row[0],
                        "content": row[1],
                        "tags": json.loads(row[2]) if row[2] else [],
                        "created_at": row[3],
                        "updated_at": row[4],
                        "access_count": row[5]
                    }
            return None
        except Exception as e:
            print(f"[X] Failed to read memory note: {e}")
            return None

    def update(self, name: str, content: str, tags: Optional[List[str]] = None) -> bool:
        """Update an existing memory note."""
        if self._disabled:
            return False
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "UPDATE memory_notes SET content = ?, tags = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
                    (content, json.dumps(tags) if tags else None, name)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[X] Failed to update memory note: {e}")
            return False

    def delete(self, name: str) -> bool:
        """Delete a memory note."""
        if self._disabled:
            return False
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM memory_notes WHERE name = ?", (name,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[X] Failed to delete memory note: {e}")
            return False

    def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search memory notes by content or name."""
        if self._disabled:
            return []
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """SELECT name, content, tags, created_at, updated_at, access_count 
                       FROM memory_notes 
                       WHERE name LIKE ? OR content LIKE ? 
                       ORDER BY updated_at DESC 
                       LIMIT ?""",
                    (f"%{query}%", f"%{query}%", limit)
                )
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "name": row[0],
                        "content": row[1],
                        "tags": json.loads(row[2]) if row[2] else [],
                        "created_at": row[3],
                        "updated_at": row[4],
                        "access_count": row[5]
                    })
                return results
        except Exception as e:
            print(f"[X] Failed to search memory notes: {e}")
            return []

    def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all memory notes."""
        if self._disabled:
            return []
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """SELECT name, content, tags, created_at, updated_at, access_count 
                       FROM memory_notes 
                       ORDER BY updated_at DESC 
                       LIMIT ?""",
                    (limit,)
                )
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "name": row[0],
                        "content": row[1],
                        "tags": json.loads(row[2]) if row[2] else [],
                        "created_at": row[3],
                        "updated_at": row[4],
                        "access_count": row[5]
                    })
                return results
        except Exception as e:
            print(f"[X] Failed to list memory notes: {e}")
            return []

    def stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        if self._disabled:
            return {"disabled": True}
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total notes
                cursor = conn.execute("SELECT COUNT(*) FROM memory_notes")
                total_notes = cursor.fetchone()[0]
                
                # Storage size
                storage_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                # Unique tags
                cursor = conn.execute("SELECT DISTINCT tags FROM memory_notes WHERE tags IS NOT NULL")
                all_tags = set()
                for row in cursor.fetchall():
                    tags = json.loads(row[0]) if row[0] else []
                    all_tags.update(tags)
                
                # Most accessed notes
                cursor = conn.execute(
                    "SELECT name, access_count FROM memory_notes WHERE access_count > 0 ORDER BY access_count DESC LIMIT 5"
                )
                most_accessed = dict(cursor.fetchall())
                
                # Recently updated
                cursor = conn.execute(
                    "SELECT name, updated_at FROM memory_notes ORDER BY updated_at DESC LIMIT 5"
                )
                recently_updated = dict(cursor.fetchall())
                
                return {
                    "total_notes": total_notes,
                    "storage_bytes": storage_bytes,
                    "tag_count": len(all_tags),
                    "unique_tags": sorted(list(all_tags)),
                    "most_accessed": most_accessed,
                    "recently_updated": recently_updated,
                    "disabled": False
                }
        except Exception as e:
            print(f"[X] Failed to get memory stats: {e}")
            return {"disabled": True}

    def auto_save(self, name: str, content: str, context: str, tags: Optional[List[str]] = None) -> bool:
        """Automatically save a memory note if it doesn't exist or has meaningful changes."""
        if self._disabled:
            return False
            
        try:
            # Check if note exists
            existing = self.read(name)
            if not existing:
                # Create new note
                auto_tags = ["auto-saved"] + (tags or [])
                return self.create(name, content, auto_tags)
            
            # Only update if there's a meaningful difference (simple heuristic)
            if len(content.strip()) > len(existing["content"].strip()) * 1.2:
                updated_tags = ["auto-saved", "updated"] + (tags or [])
                return self.update(name, content, updated_tags)
            
            return True  # No update needed
        except Exception as e:
            print(f"[X] Failed to auto-save memory note: {e}")
            return False


def get_project_memory(project_path: str) -> ProjectMemory:
    """Get or create memory instance for a project."""
    if project_path not in _memory_instances:
        _memory_instances[project_path] = ProjectMemory(project_path)
    return _memory_instances[project_path]


# Global reference to AI Coder instance for tool integration
_aicoder_ref = None


def memory_tool_handler(arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle memory tool calls."""
    global _aicoder_ref
    
    if not _aicoder_ref:
        return {"error": "Memory functionality not available"}
    
    operation = arguments.get("operation")
    if not operation:
        return {"error": "Missing operation parameter"}
    
    # Get current project path
    project_path = getattr(_aicoder_ref, 'current_project_path', os.getcwd())
    memory = get_project_memory(project_path)
    
    try:
        if operation == "create":
            name = arguments.get("name")
            content = arguments.get("content")
            tags = arguments.get("tags")
            
            if not name or not content:
                return {"error": "Missing name or content for create operation"}
            
            success = memory.create(name, content, tags)
            return {"success": success, "message": f"Memory note '{name}' created" if success else f"Failed to create '{name}'"}
        
        elif operation == "read":
            name = arguments.get("name")
            if not name:
                return {"error": "Missing name for read operation"}
            
            note = memory.read(name)
            if note:
                return {"success": True, "note": note}
            else:
                return {"success": False, "message": f"Memory note '{name}' not found"}
        
        elif operation == "update":
            name = arguments.get("name")
            content = arguments.get("content")
            tags = arguments.get("tags")
            
            if not name or not content:
                return {"error": "Missing name or content for update operation"}
            
            success = memory.update(name, content, tags)
            return {"success": success, "message": f"Memory note '{name}' updated" if success else f"Failed to update '{name}'"}
        
        elif operation == "delete":
            name = arguments.get("name")
            if not name:
                return {"error": "Missing name for delete operation"}
            
            success = memory.delete(name)
            return {"success": success, "message": f"Memory note '{name}' deleted" if success else f"Failed to delete '{name}'"}
        
        elif operation == "search":
            query = arguments.get("query")
            if not query:
                return {"error": "Missing query for search operation"}
            
            results = memory.search(query)
            return {"success": True, "results": results, "count": len(results)}
        
        elif operation == "list":
            results = memory.list()
            return {"success": True, "results": results, "count": len(results)}
        
        elif operation == "stats":
            stats = memory.stats()
            return {"success": True, "stats": stats}
        
        elif operation == "auto_save":
            name = arguments.get("name")
            content = arguments.get("content")
            context = arguments.get("context")
            tags = arguments.get("tags")
            
            if not name or not content or not context:
                return {"error": "Missing name, content, or context for auto_save operation"}
            
            success = memory.auto_save(name, content, context, tags)
            return {"success": success, "message": f"Memory note '{name}' auto-saved" if success else f"Failed to auto-save '{name}'"}
        
        else:
            return {"error": f"Unknown operation: {operation}"}
            
    except Exception as e:
        return {"error": f"Memory operation failed: {str(e)}"}


def initialize_plugin(aicoder_instance):
    """Initialize the memory plugin."""
    global _aicoder_ref
    _aicoder_ref = aicoder_instance

    # Note: /memory and /m commands are now handled by core memory_command.py
    # This plugin only provides the memory tool for AI to use

    # Register the memory tool
    if hasattr(aicoder_instance, "tool_manager") and hasattr(
        aicoder_instance.tool_manager, "registry"
    ):
        # Add the tool definition to the registry
        aicoder_instance.tool_manager.registry.mcp_tools["memory"] = (
            MEMORY_TOOL_DEFINITION
        )

        # Override the tool execution to use our implementation
        original_execute_tool = aicoder_instance.tool_manager.executor.execute_tool

        def patched_execute_tool(tool_name, arguments, tool_index=0, total_tools=0):
            if tool_name == "memory":
                return memory_tool_handler(arguments)
            else:
                return original_execute_tool(tool_name, arguments, tool_index, total_tools)

        aicoder_instance.tool_manager.executor.execute_tool = patched_execute_tool

        print("[+] Memory plugin initialized - AI can now use memory tool")
        print("    Note: /memory and /m commands for editing messages are now core commands")
        return True
    else:
        print("[X] Failed to load memory plugin: tool_manager not available")
        return False


# Plugin metadata
PLUGIN_NAME = "memory"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Project memory management system with AI integration"