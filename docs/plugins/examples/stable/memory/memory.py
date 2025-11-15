"""
Memory Plugin for AI Coder

This plugin provides project memory management system with:
1. A /memory command for users to manage project memory
2. A memory tool implementation for the AI to store/retrieve project knowledge
3. SQLite-based storage for persistent project memory
"""

import os
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
                "description": "Optional tags for categorization (used with create, auto_save)"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results for search/list (default: 20)",
                "minimum": 1,
                "maximum": 100
            },
            "sort_by": {
                "type": "string",
                "enum": ["updated_at", "created_at", "last_accessed", "name"],
                "description": "Sort column for list (default: updated_at)"
            }
        },
        "required": ["operation"]
    }
}


class ProjectMemory:
    """Simple project-based memory storage using SQLite."""

    def __init__(self, project_path: str):
        """Initialize project memory."""
        self.project_path = os.path.abspath(project_path)
        self.db_path = os.path.join(self.project_path, ".aicoder", "memory.db")
        self._disabled = False

        # Ensure .aicoder directory exists
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        except Exception:
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
            self._disabled = True

    def create(self, name: str, content: str, tags: List[str] = None) -> str:
        """Create or update a memory note."""
        if self._disabled:
            return "Memory system is disabled (read-only filesystem)"

        tags_str = ",".join(tags) if tags else None

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT name, tags FROM notes WHERE name = ?", (name,))
                existing = cursor.fetchone()
                exists = existing is not None

                if exists:
                    # For updates, preserve existing tags if no new tags provided
                    if tags is None:
                        # Use existing tags
                        tags_str = existing[1]  # existing tags from database
                    action = "Updated"
                else:
                    action = "Created"

                conn.execute(
                    """
                    INSERT OR REPLACE INTO notes (name, content, tags, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (name, content, tags_str),
                )

                conn.commit()

                return f"{action} memory note: {name}"
        except Exception:
            return "Failed to save memory note"

    def read(self, name: str) -> Optional[Dict[str, Any]]:
        """Read a specific memory note."""
        if self._disabled:
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update access count first
                conn.execute(
                    """
                    UPDATE notes
                    SET access_count = access_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE name = ?
                """,
                    (name,),
                )
                conn.commit()  # Commit the access count update
                
                # Then read the note
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
        """Search memory notes by content or name."""
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
        """List all memory notes."""
        if self._disabled:
            return []

        valid_sort_columns = [
            "updated_at",
            "created_at",
            "last_accessed",
            "name",
        ]
        if sort_by not in valid_sort_columns:
            sort_by = "updated_at"

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
        """Delete a memory note."""
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
        """Get memory system statistics."""
        if self._disabled:
            return {"disabled": True, "total_notes": 0}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM notes")
                total_notes = cursor.fetchone()[0]

                # Get actual database size (vacuum to compact)
                try:
                    storage_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                    # Optional: run vacuum to get compacted size (can be slow)
                    # conn.execute("VACUUM")
                except Exception:
                    storage_bytes = 0

                cursor = conn.execute("SELECT tags FROM notes WHERE tags != ''")
                all_tags = set()
                for row in cursor.fetchall():
                    if row[0]:
                        all_tags.update(tag.strip() for tag in row[0].split(',') if tag.strip())

                cursor = conn.execute("""
                    SELECT name, access_count
                    FROM notes
                    WHERE access_count > 0
                    ORDER BY access_count DESC
                    LIMIT 5
                """)
                most_accessed = dict(cursor.fetchall())

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
                    "note": "Database size may include unused space. SQLite doesn't shrink immediately on deletes.",
                    "tag_count": len(all_tags),
                    "unique_tags": list(all_tags),
                    "most_accessed": most_accessed,
                    "recently_updated": recently_updated
                }
        except Exception:
            return {"disabled": True, "total_notes": 0}

    def auto_save_decision(self, issue: str, solution: str, tags: List[str] = None, name: str = None) -> str:
        """Auto-save a decision to memory."""
        import time
        if not name:
            name = f"decision_{int(time.time())}"
        content = f"Issue: {issue}\nSolution: {solution}"
        all_tags = (tags or []) + ["auto-saved", "decision"]
        return self.create(name, content, all_tags)


def execute_memory(operation: str, name: str = None, content: str = None, 
                   query: str = None, context: str = None, tags: List[str] = None,
                   limit: int = 20, sort_by: str = "updated_at", stats=None) -> str:
    """Custom memory tool implementation."""
    global _aicoder_ref

    if not _aicoder_ref:
        return "Error: Memory functionality not available"

    # Get current project path
    project_path = getattr(_aicoder_ref, 'current_project_path', os.getcwd())
    memory = get_project_memory(project_path)

    try:
        if operation == "create":
            if not name or not content:
                return "Error: 'name' and 'content' are required for create operation"
            return memory.create(name, content, tags)

        elif operation == "update":
            if not name or not content:
                return "Error: 'name' and 'content' are required for update operation"
            return memory.create(name, content, tags)  # create handles both create and update

        elif operation == "read":
            if not name:
                return "Error: 'name' is required for read operation"
            result = memory.read(name)
            if result:
                return f"Memory note '{name}':\n{result['content']}\n\nTags: {', '.join(result['tags'])}\nAccessed: {result['access_count']} times"
            else:
                return f"Memory note '{name}' not found"

        elif operation == "search":
            if not query:
                return "Error: 'query' is required for search operation"
            results = memory.search(query, limit)
            if results:
                output = f"Found {len(results)} memory notes matching '{query}':\n\n"
                for result in results:
                    output += f"• {result['name']}\n"
                    output += f"  Tags: {', '.join(result['tags'])}\n"
                    output += f"  Updated: {result['updated_at']}\n\n"
                return output.strip()
            else:
                return f"No memory notes found matching '{query}'"

        elif operation == "list":
            results = memory.list(limit, sort_by)
            if results:
                output = f"Memory notes (sorted by {sort_by}, limit {limit}):\n\n"
                for result in results:
                    output += f"• {result['name']}\n"
                    output += f"  Tags: {', '.join(result['tags'])}\n"
                    output += f"  Updated: {result['updated_at']}\n\n"
                return output.strip()
            else:
                return "No memory notes found"

        elif operation == "delete":
            if not name:
                return "Error: 'name' is required for delete operation"
            if memory.delete(name):
                return f"Deleted memory note: {name}"
            else:
                return f"Memory note '{name}' not found or could not be deleted"

        elif operation == "stats":
            stats_data = memory.stats()
            if stats_data.get("disabled"):
                return "Memory system is disabled"
            
            output = "Memory System Statistics:\n\n"
            output += f"Total notes: {stats_data['total_notes']}\n"
            output += f"Storage size: {stats_data['storage_bytes']} bytes\n"
            output += f"Unique tags: {stats_data['tag_count']}\n"
            
            if stats_data['most_accessed']:
                output += "\nMost accessed notes:\n"
                for name, count in stats_data['most_accessed'].items():
                    output += f"  {name}: {count} times\n"
            
            return output.strip()

        elif operation == "auto_save":
            if not context:
                return "Error: 'context' is required for auto_save operation"
            # Use context as both issue and solution for simple auto-save, pass name if provided
            return memory.auto_save_decision(context, context, tags, name)

        else:
            return f"Error: Unknown operation '{operation}'"

    except Exception as e:
        return f"Error executing memory operation: {e}"


def get_project_memory(project_path: str) -> ProjectMemory:
    """Get or create a project memory instance."""
    abs_path = os.path.abspath(project_path)
    if abs_path not in _memory_instances:
        _memory_instances[abs_path] = ProjectMemory(abs_path)
    return _memory_instances[abs_path]


# Global reference to store the aicoder instance
_aicoder_ref = None


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        # Store reference to aicoder instance
        global _aicoder_ref
        _aicoder_ref = aicoder_instance

        # Add /memory command to the command registry
        aicoder_instance.command_handlers["/memory"] = _handle_memory_command
        aicoder_instance.command_handlers["/m"] = _handle_memory_command  # Alias

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
                    try:
                        # Extract arguments
                        operation = arguments.get("operation")
                        name = arguments.get("name")
                        content = arguments.get("content")
                        query = arguments.get("query")
                        context = arguments.get("context")
                        tags = arguments.get("tags")
                        limit = arguments.get("limit", 20)
                        sort_by = arguments.get("sort_by", "updated_at")
                        
                        result = execute_memory(
                            operation=operation,
                            name=name,
                            content=content,
                            query=query,
                            context=context,
                            tags=tags,
                            limit=limit,
                            sort_by=sort_by
                        )

                        return result, MEMORY_TOOL_DEFINITION, False
                    except Exception as e:
                        return f"Error executing memory: {e}", MEMORY_TOOL_DEFINITION, False
                else:
                    return original_execute_tool(tool_name, arguments, tool_index, total_tools)

            aicoder_instance.tool_manager.executor.execute_tool = patched_execute_tool

        print("[✓] Memory plugin loaded successfully")
        print("   - /memory and /m commands available")
        print("   - memory tool registered for AI use")
        return True
    except Exception as e:
        print(f"[X] Failed to load memory plugin: {e}")
        return False


def _show_memory_help():
    """Show help for memory command."""
    print("\nMemory Management Help")
    print("======================")
    print("Available commands:")
    print("  /memory              - Show memory system status")
    print("  /memory help         - Show this help")
    print("  /memory list         - List all memory notes")
    print("  /memory search <query> - Search memory notes")
    print("  /memory stats        - Show memory statistics")
    print("\nAI Tool Usage:")
    print("  The AI can use the memory tool to:")
    print("  - create: Store new information")
    print("  - read: Retrieve stored information")
    print("  - search: Find relevant information")
    print("  - list: Browse all stored notes")
    print("  - auto_save: Automatically save decisions")
    print("\nExamples:")
    print("  /memory list         - List all stored memory notes")
    print("  /memory search api   - Search for API-related notes")
    print("  /memory stats        - Show usage statistics")
    print("\nNote: Memory is stored per project in .aicoder/memory.db")


def _handle_memory_command(args):
    """Handle /memory command."""
    global _aicoder_ref

    if not _aicoder_ref:
        print("[X] Memory functionality not available")
        return False, False

    # Handle subcommands
    if args:
        subcommand = args[0].lower()

        if subcommand in ["help", "-h", "--help"]:
            _show_memory_help()
            return False, False
        elif subcommand == "list":
            # Get current project path
            project_path = getattr(_aicoder_ref, 'current_project_path', os.getcwd())
            memory = get_project_memory(project_path)
            results = memory.list()
            if results:
                print(f"\nMemory Notes ({len(results)} total):")
                print("=" * 60)
                for result in results:
                    print(f"• {result['name']}")
                    if result['tags']:
                        print(f"  Tags: {', '.join(result['tags'])}")
                    print(f"  Updated: {result['updated_at']}")
                    print()
            else:
                print("\nNo memory notes found.")
            return False, False
        elif subcommand == "search":
            if len(args) < 2:
                print("[X] Usage: /memory search <query>")
                return False, False
            query = " ".join(args[1:])
            project_path = getattr(_aicoder_ref, 'current_project_path', os.getcwd())
            memory = get_project_memory(project_path)
            results = memory.search(query)
            if results:
                print(f"\nMemory Notes matching '{query}' ({len(results)} found):")
                print("=" * 60)
                for result in results:
                    print(f"• {result['name']}")
                    if result['tags']:
                        print(f"  Tags: {', '.join(result['tags'])}")
                    # Show preview of content
                    content_preview = result['content'][:100]
                    if len(result['content']) > 100:
                        content_preview += "..."
                    print(f"  Preview: {content_preview}")
                    print()
            else:
                print(f"\nNo memory notes found matching '{query}'.")
            return False, False
        elif subcommand == "stats":
            project_path = getattr(_aicoder_ref, 'current_project_path', os.getcwd())
            memory = get_project_memory(project_path)
            stats_data = memory.stats()
            
            if stats_data.get("disabled"):
                print("\nMemory system is disabled")
                return False, False
            
            print("\nMemory System Statistics:")
            print("=" * 30)
            print(f"Total notes: {stats_data['total_notes']}")
            print(f"Storage size: {stats_data['storage_bytes']} bytes")
            print(f"Unique tags: {stats_data['tag_count']}")
            
            if stats_data['unique_tags']:
                print(f"Tags: {', '.join(stats_data['unique_tags'][:10])}")
                if len(stats_data['unique_tags']) > 10:
                    print(f"  ... and {len(stats_data['unique_tags']) - 10} more")
            
            if stats_data['most_accessed']:
                print("\nMost accessed notes:")
                for name, count in list(stats_data['most_accessed'].items())[:5]:
                    print(f"  {name}: {count} times")
            
            if stats_data['recently_updated']:
                print("\nRecently updated:")
                for name, updated in stats_data['recently_updated'][:5]:
                    print(f"  {name}: {updated}")
            
            return False, False

    # Default behavior: show memory status
    project_path = getattr(_aicoder_ref, 'current_project_path', os.getcwd())
    memory = get_project_memory(project_path)
    stats_data = memory.stats()
    
    if stats_data.get("disabled"):
        print("\nMemory system is disabled")
        return False, False
    
    print(f"\nMemory System Status:")
    print("=" * 25)
    print(f"Project: {project_path}")
    print(f"Total notes: {stats_data['total_notes']}")
    print(f"Storage: {stats_data['storage_bytes']} bytes")
    print("\nUse '/memory help' for commands")
    print("The AI can use the memory tool to store and retrieve information")
    
    return False, False


# Plugin metadata
PLUGIN_NAME = "memory"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Project memory management system with AI integration"