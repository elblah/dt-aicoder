"""
Todo Plugin for AI Coder

This plugin provides a complete todo management system with:
1. A /todo command for users to view and manage todos
2. A custom update_todo tool implementation for the AI to track progress
3. Memory storage for todo persistence during sessions
"""

# Global storage for todos (in-memory during session)
_last_todo_storage = {"todo_text": None, "explanation": None}

# Custom update_todo tool definition
UPDATE_TODO_TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "hide_results": True,
    "hide_arguments": True,
    "approval_excludes_arguments": True,
    "hidden_parameters": ["todo_text", "explanation"],
    "name": "update_todo",
    "description": "Track and display task progress to the user using text-based input. Use this tool to show what steps you're working on and keep the user informed about your progress. Provide a formatted todo text with clear checkboxes.",
    "parameters": {
        "type": "object",
        "properties": {
            "todo_text": {
                "type": "string",
                "description": "Formatted todo text with clear checkboxes (e.g., '- [x] Completed task\\n- [ ] Pending task')",
            },
            "explanation": {
                "type": "string",
                "description": "Optional explanation or note about the todo",
            },
        },
        "required": ["todo_text"],
    },
}


def execute_update_todo(todo_text: str, explanation: str = None, stats=None) -> str:
    """
    Custom update_todo tool implementation.

    This tool displays a todo list to the user with progress tracking.
    The AI can call this tool to show what steps it's working on.

    Args:
        todo_text: Formatted todo text with clear checkboxes
        explanation: Optional explanation/note (string)
        stats: Stats object (unused but required for internal tools)

    Returns:
        Success message indicating todo was displayed
    """
    # Validate that todo_text is a string
    if not isinstance(todo_text, str):
        raise ValueError("Invalid todo_text format: todo_text must be a string.")

    # Check for minimum content requirements
    if not todo_text.strip():
        raise ValueError("Todo text cannot be empty.")

    # Store the todo in global storage
    global _last_todo_storage
    _last_todo_storage["todo_text"] = todo_text
    _last_todo_storage["explanation"] = explanation

    # Format and display the todo
    _display_todo(todo_text, explanation)

    # Return success message
    return "Todo displayed successfully"


def _display_todo(todo_text: str, explanation: str = None) -> None:
    """
    Display the todo in a user-friendly format.

    Args:
        todo_text: Formatted todo text with clear checkboxes
        explanation: Optional explanation/note
    """
    # Extract todo title (first line starting with # or use a generic title)
    lines = todo_text.strip().split("\n")
    title = None
    for line in lines:
        line = line.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            break
    if not title:
        title = "Todo"

    # Count checkboxes and calculate completion
    total_tasks = 0
    completed_tasks = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
            total_tasks += 1
            completed_tasks += 1
        elif stripped.startswith("- [ ]"):
            total_tasks += 1

    # Calculate percentage
    if total_tasks > 0:
        percentage = int((completed_tasks / total_tasks) * 100)
    else:
        percentage = 0

    # Display formatted todo
    print("\n" + "=" * 60)
    print(f"{title}")
    print("=" * 60)

    # Show progress bar
    progress_bar_length = 30
    filled_length = int((percentage / 100) * progress_bar_length)
    bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
    print(f"Progress: [{bar}] {percentage}% ({completed_tasks}/{total_tasks})")

    # Print todo text
    if not todo_text.strip():
        print("No todo items to display.")
    else:
        # Print each line of the todo with the emojis from the previous JSON version
        for line in todo_text.strip().split("\n"):
            stripped = line.strip()
            if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
                # Completed item
                checkbox = "[✓]"
                content = stripped[5:].strip()  # Remove "- [x] " prefix
                print(f"  {checkbox} {content}")
            elif stripped.startswith("- [ ]"):
                # Pending item
                checkbox = "[ ]"
                content = stripped[5:].strip()  # Remove "- [ ] " prefix
                print(f"  {checkbox} {content}")
            elif stripped.startswith("#"):
                # Header
                level = 0
                for char in stripped:
                    if char == "#":
                        level += 1
                    else:
                        break
                header_text = stripped[level:].strip()
                if level == 1:
                    print(f"\n{header_text}")
                elif level == 2:
                    print(f"\n{header_text}")
                else:
                    print(f"\n{header_text}")
            elif stripped:
                # Regular line
                print(f"  {stripped}")

    print("=" * 60)

    # Show explanation if provided
    if explanation and explanation.strip():
        print(f"\nNote: {explanation}")

    # Show last updated time
    import datetime

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\nLast updated: {now}")


# Global reference to store the aicoder instance
_aicoder_ref = None


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        # Check if todo is enabled in persistent config
        todo_enabled = True  # Default to enabled
        if hasattr(aicoder_instance, "persistent_config"):
            todo_enabled = aicoder_instance.persistent_config.get("todo.enabled", True)

        # Store reference to aicoder instance for access to message history
        global _aicoder_ref
        _aicoder_ref = aicoder_instance

        # Always add /todo command to the command registry
        # The command itself will check if todo is enabled
        aicoder_instance.command_handlers["/todo"] = _handle_todo_command

        # Always register the update_todo tool, but it will be conditionally enabled
        if hasattr(aicoder_instance, "tool_manager") and hasattr(
            aicoder_instance.tool_manager, "registry"
        ):
            # Add the tool definition to the registry
            aicoder_instance.tool_manager.registry.mcp_tools["update_todo"] = (
                UPDATE_TODO_TOOL_DEFINITION
            )

            # Override the tool execution to use our conditional implementation
            original_execute_tool = aicoder_instance.tool_manager.executor.execute_tool

            def patched_execute_tool(tool_name, arguments, tool_index=0, total_tools=0):
                if tool_name == "update_todo":
                    # Use our conditional implementation
                    try:
                        todo_text = arguments.get("todo_text", "")
                        explanation = arguments.get("explanation", None)
                        result = _execute_todo_tool_if_enabled(todo_text, explanation)

                        # Store in aicoder instance as well
                        if hasattr(aicoder_instance, "last_todo"):
                            aicoder_instance.last_todo = todo_text
                            aicoder_instance.last_todo_explanation = explanation

                        # Return the tool configuration as the second element, not True
                        return result, UPDATE_TODO_TOOL_DEFINITION, False
                    except Exception as e:
                        return (
                            f"Error executing update_todo: {e}",
                            UPDATE_TODO_TOOL_DEFINITION,
                            False,
                        )
                else:
                    # Use original implementation for other tools
                    return original_execute_tool(
                        tool_name, arguments, tool_index, total_tools
                    )

            aicoder_instance.tool_manager.executor.execute_tool = patched_execute_tool

        # Add todo storage to the aicoder instance
        aicoder_instance.last_todo = None
        aicoder_instance.last_todo_explanation = None

        if not todo_enabled:
            print("   - Todo functionality disabled via settings")
            print("   - Use '/todo on' to enable or '/todo help' for commands")
            # Don't add system prompt when disabled
            return True

        # Add system prompt if todo is enabled
        _add_todo_system_prompt()

        if todo_enabled:
            print("[✓] Todo plugin loaded successfully")
            print("   - /todo command available")
            print("   - Custom update_todo tool registered")
            print("   - AI instructions added to system prompt")
            print("   - Use /todo to view todos, /todo update to force updates")
        else:
            print("[✓] Todo plugin loaded successfully")
            print("   - /todo command available for management")
            print("   - Custom update_todo tool registered but disabled")
            print("   - Use '/todo on' to enable functionality")

        return True
    except Exception as e:
        print(f"[X] Failed to load todo plugin: {e}")
        return False


def _show_todo_help():
    """Show help for todo command."""
    print("\nTodo Management Help")
    print("====================")
    print("Available commands:")
    print("  /todo              - Show current todo")
    print("  /todo help         - Show this help")
    print("  /todo on           - Enable todo functionality")
    print("  /todo off          - Disable todo functionality")
    print("  /todo update       - Request updated todo from AI")
    print("\nCommand Details:")
    print("  /todo              - Display the currently stored todo list")
    print("                      If no todo exists, tells you how to create one")
    print("  /todo update       - Ask AI to create or update the current todo list")
    print("\nState Management:")
    print(
        "  /todo on           - Enable todo functionality and AI access to update_todo tool"
    )
    print(
        "  /todo off          - Disable todo functionality and remove AI access to tool"
    )
    print("\nExamples:")
    print("  /todo              - View current todo")
    print("  /todo on           - Enable todos")
    print("  /todo off          - Disable todos")
    print("  /todo update       - Get updated todo from AI")
    print("\nNote: When todo is disabled, the AI cannot use the update_todo tool.")
    print("      The /todo command itself remains available for management.")


def _is_todo_tool_enabled():
    """Check if the update_todo tool is enabled in persistent config."""
    global _aicoder_ref

    if not _aicoder_ref or not hasattr(_aicoder_ref, "persistent_config"):
        return True  # Default to enabled

    return _aicoder_ref.persistent_config.get("todo.enabled", True)


def _execute_todo_tool_if_enabled(todo_text, explanation, stats=None):
    """Execute the update_todo tool only if it's enabled."""
    if not _is_todo_tool_enabled():
        return "Error: Todo functionality is currently disabled. Use '/todo on' to enable it."

    return execute_update_todo(todo_text, explanation, stats)


def _add_todo_system_prompt():
    """Add todo functionality information to the system prompt."""
    global _aicoder_ref

    if not _aicoder_ref:
        return

    # Only add system prompt if todo is enabled
    if not _is_todo_tool_enabled():
        return

    # Add comprehensive information about todo functionality to the system prompt
    if (
        hasattr(_aicoder_ref, "message_history")
        and _aicoder_ref.message_history.messages
    ):
        system_prompt = _aicoder_ref.message_history.messages[0]
        if isinstance(system_prompt, dict) and "content" in system_prompt:
            todo_info = """

Todo Management with update_todo Tool

The AI Coder includes an update_todo tool inspired by OpenAI Codex CLI that allows you to track and display task progress to users. This tool helps demonstrate your understanding of tasks and conveys your approach clearly using text-based input.

When to Use the update_todo Tool:
Use the update_todo tool when:
- Working on complex, multi-step tasks
- You want to communicate your approach to the user
- There are logical phases or dependencies in your work
- You want to provide intermediate checkpoints for feedback
- The task has ambiguity that benefits from outlining high-level goals

How to Use the update_todo Tool:
1. Create a todo with meaningful, logically ordered steps
2. Use clear checkbox formatting:
   - [x] or [X] - Completed steps
   - [ ] - Pending steps
3. Organize with headers using # for main title and ## for sections
4. Include an explanation when changing todos significantly

Best Practices for update_todo:
- Break tasks into meaningful steps that are easy to verify
- Mark completed items with [x] as you finish each step
- Update the todo before moving to the next major step
- Use clear, descriptive step names
- Keep todo focused and manageable (avoid overly detailed sub-tasks unless they're important checkpoints)

The update_todo tool is particularly useful for:
- Complex refactoring or feature development
- Multi-file changes that require coordination
- Debugging complex issues with multiple approaches
- Learning new codebases or technologies
- Any task where showing your systematic approach adds value

Example update_todo tool call:

{
  "name": "update_todo",
  "arguments": {
    "todo_text": "# Todo: Build New Website\\n\\n## Phase 1: Project Setup\\n - [x] Initialize git repository\\n - [x] Create project structure (folders for src, assets, etc.)\\n - [x] Install dependencies (e.g., React, Webpack)\\n\\n## Phase 2: Develop Core Features\\n - [x] Create homepage component\\n - [ ] Implement user authentication\\n - [ ] Design the database schema\\n\\n## Phase 3: Deployment\\n - [ ] Write unit tests\\n - [ ] Configure production build\\n - [ ] Deploy to hosting provider",
    "explanation": "Updated todo to reflect completion of project setup phase and mark authentication as next priority."
  }
}

Display and User Interaction:
The update_todo tool will display your todo list to the user in a formatted way with:
- Checkboxes showing completed [x] and pending [ ] items
- Progress indicators and completion percentage
- Clear visual hierarchy for phases and steps
- Optional explanations for context

Users can also use the /todo command to view the current todo list:
- /todo - Shows the current stored todo
- /todo update - Ask AI to create or update the current todo list
- /todo on - Enable todo functionality
- /todo off - Disable todo functionality
- /todo help - Show todo command help
"""
            # Only add if not already present
            if "Todo Management with update_todo Tool" not in system_prompt.get(
                "content", ""
            ):
                system_prompt["content"] += todo_info


def _set_todo_enabled(enabled):
    """Enable or disable todo functionality."""
    global _aicoder_ref

    if not _aicoder_ref or not hasattr(_aicoder_ref, "persistent_config"):
        print("[X] Cannot modify todo settings: persistent config not available")
        return

    # Update the persistent config
    _aicoder_ref.persistent_config["todo.enabled"] = enabled

    if enabled:
        # Add system prompt info if not already added
        _add_todo_system_prompt()

        print("[✓] Todo functionality enabled")
        print("   - /todo command available")
        print("   - AI can use update_todo tool")
    else:
        print("[X] Todo functionality disabled")
        print("   - /todo command unavailable")
        print("   - AI cannot use update_todo tool")


def _handle_todo_command(args):
    """Handle /todo command - show last todo or manage todo settings."""
    global _aicoder_ref, _last_todo_storage

    if not _aicoder_ref:
        print("[X] Todo functionality not available")
        return False, False

    # Handle subcommands
    if args:
        subcommand = args[0].lower()

        if subcommand in ["help", "-h", "--help"]:
            _show_todo_help()
            return False, False
        elif subcommand in ["on", "enable"]:
            _set_todo_enabled(True)
            return False, False
        elif subcommand in ["off", "disable"]:
            _set_todo_enabled(False)
            return False, False
        elif subcommand == "update":
            # Check if todo is enabled before requesting update
            if hasattr(_aicoder_ref, "persistent_config"):
                todo_enabled = _aicoder_ref.persistent_config.get("todo.enabled", True)
                if not todo_enabled:
                    print("Todo functionality is disabled. Use '/todo on' to enable.")
                    return False, False

            # Force a new todo request by asking the AI to call update_todo
            print("\n*** Requesting new todo from AI...")
            _aicoder_ref.message_history.add_user_message(
                "Please provide an updated todo using the update_todo tool to track your current progress."
            )
            return False, True  # Run API call

    # Default behavior: show current todo
    # Check if todo is enabled
    if hasattr(_aicoder_ref, "persistent_config"):
        todo_enabled = _aicoder_ref.persistent_config.get("todo.enabled", True)
        if not todo_enabled:
            print("Todo functionality is disabled. Use '/todo on' to enable.")
            return False, False

    # Check for stored todo in global storage
    todo_text = _last_todo_storage.get("todo_text")
    explanation = _last_todo_storage.get("explanation")

    # Show the last todo if available
    if todo_text:
        print("\n*** Current Todo:")
        _display_todo(todo_text, explanation)
        return False, False
    else:
        # No todo exists, instruct user to create one
        print("\n*** No todo found.")
        print(
            "    Use '/todo update' to ask the AI to create or update the current todo list."
        )
        return False, False


# Plugin metadata
PLUGIN_NAME = "todo"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Complete todo management system with AI integration"
