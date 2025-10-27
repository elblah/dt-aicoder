"""
Memory internal tool implementation.

Single tool for all memory operations: create, read, search, delete, list, stats.
Follows AI Coder's pattern of consolidated tools.
"""

from typing import List

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "approval_excludes_arguments": False,
    "approval_key_exclude_arguments": [],
    "hide_results": False,
    "description": "Manage project memory - store and retrieve project-specific knowledge",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "create",
                    "update",
                    "read",
                    "search",
                    "delete",
                    "list",
                    "stats",
                    "auto_save",
                ],
                "description": "Memory operation to perform",
            },
            "name": {
                "type": "string",
                "description": "Name/identifier for the memory note (required for create, update, read, delete, auto_save)",
            },
            "content": {
                "type": "string",
                "description": "Content of the memory note (required for create, update, auto_save)",
            },
            "query": {
                "type": "string",
                "description": "Search query (required for search)",
            },
            "context": {
                "type": "string",
                "description": "Context for auto_save decision (required for auto_save)",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags for categorization (used with create, auto_save)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results for search/list (default: 20)",
                "minimum": 1,
                "maximum": 100,
            },
            "sort_by": {
                "type": "string",
                "enum": ["updated_at", "created_at", "last_accessed", "name"],
                "description": "Sort column for list (default: updated_at)",
            },
        },
        "required": ["operation"],
        "additionalProperties": False,
    },
}


def execute_memory(
    operation: str,
    name: str = None,
    content: str = None,
    query: str = None,
    context: str = None,
    tags: List[str] = None,
    limit: int = 20,
    sort_by: str = "updated_at",
    stats=None,
    project_path: str = None,
) -> str:
    """
    Execute memory operations.

    Args:
        operation: Operation type (create, read, search, delete, list, stats, auto_save)
        name: Note name (for create, read, delete, auto_save)
        content: Note content (for create, auto_save)
        query: Search query (for search)
        context: Context for auto_save decision
        tags: Optional tags
        limit: Result limit for search/list
        sort_by: Sort column for list

    Returns:
        Operation result
    """
    try:
        from aicoder.memory import get_project_memory
        import os

        # Use provided project_path or current working directory
        project_dir = project_path or os.getcwd()
        memory = get_project_memory(project_dir)
        if stats:
            stats.tool_calls += 1

        if operation == "create":
            if not name or not content:
                if stats:
                    stats.tool_errors += 1
                return "Error: 'name' and 'content' are required for create operation"
            return memory.create(name, content, tags)

        elif operation == "update":
            if not name or not content:
                if stats:
                    stats.tool_errors += 1
                return "Error: 'name' and 'content' are required for update operation"
            return memory.create(name, content, tags)  # create already handles updates

        elif operation == "read":
            if not name:
                if stats:
                    stats.tool_errors += 1
                return "Error: 'name' is required for read operation"
            note = memory.read(name)
            if note:
                tags_str = (
                    f"Tags: {', '.join(note['tags'])}" if note["tags"] else "No tags"
                )
                created = (
                    note["created_at"].split(" ")[0]
                    if note["created_at"]
                    else "Unknown"
                )
                accessed = note["access_count"]

                return f"""Memory Note: {note["name"]}
Created: {created} | Accessed: {accessed} times | {tags_str}

{note["content"]}"""
            else:
                return f"Memory note '{name}' not found"

        elif operation == "search":
            if not query:
                if stats:
                    stats.tool_errors += 1
                return "Error: 'query' is required for search operation"
            results = memory.search(query, limit)
            if results:
                output = f"Found {len(results)} memory notes matching '{query}':\n\n"
                for i, note in enumerate(results, 1):
                    tags_str = f"[{', '.join(note['tags'])}]" if note["tags"] else ""
                    preview = (
                        note["content"][:100] + "..."
                        if len(note["content"]) > 100
                        else note["content"]
                    )
                    output += f"{i}. {note['name']} {tags_str}\n   {preview}\n\n"
                return output.strip()
            else:
                return f"No memory notes found matching '{query}'"

        elif operation == "delete":
            if not name:
                if stats:
                    stats.tool_errors += 1
                return "Error: 'name' is required for delete operation"
            if memory.delete(name):
                return f"Deleted memory note: {name}"
            else:
                return f"Memory note '{name}' not found"

        elif operation == "list":
            notes = memory.list(limit=limit, sort_by=sort_by)
            if notes:
                output = f"Memory notes (sorted by {sort_by}):\n\n"
                for i, note in enumerate(notes, 1):
                    tags_str = f"[{', '.join(note['tags'])}]" if note["tags"] else ""
                    output += (
                        f"{i}. {note['name']} {tags_str}\n   {note['content']}\n\n"
                    )
                return output.strip()
            else:
                return "No memory notes found"

        elif operation == "stats":
            stats_data = memory.get_stats()
            output = f"""Memory Statistics:
Total notes: {stats_data["total_notes"]}
Storage used: {stats_data["storage_bytes"]:,} bytes
Unique tags: {stats_data["tag_count"]}"""

            if stats_data["most_accessed"]:
                output += "\n\nMost accessed:"
                for name, count in stats_data["most_accessed"]:
                    output += f"\n  {name}: {count} times"

            if stats_data["recently_updated"]:
                output += "\n\nRecently updated:"
                for name, updated in stats_data["recently_updated"]:
                    date = updated.split(" ")[0]
                    output += f"\n  {name}: {date}"

            if stats_data["unique_tags"]:
                output += f"\n\nTags: {', '.join(stats_data['unique_tags'][:10])}"
                if len(stats_data["unique_tags"]) > 10:
                    output += f" ... and {len(stats_data['unique_tags']) - 10} more"

            return output

        elif operation == "auto_save":
            if not name or not context or not content:
                if stats:
                    stats.tool_errors += 1
                return "Error: 'name', 'context', and 'content' are required for auto_save operation"
            return memory.auto_save_decision(context, content, tags)

        else:
            if stats:
                stats.tool_errors += 1
            return f"Error: Unknown operation '{operation}'. Valid operations: create, update, read, search, delete, list, stats, auto_save"

    except Exception as e:
        if stats:
            stats.tool_errors += 1
        return f"Error in memory operation '{operation}': {e}"
